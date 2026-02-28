"""
CORRYU ETF Dashboard - MECE 섹터 분류 엔진
3-Pass Waterfall: 키워드 → 상관계수 → Fallback
"""
import re
from collections import defaultdict
from typing import Any
import pandas as pd

from config import (
    SECTOR_DEFS, SUPER_SECTOR_DEFS, KEYWORD_RULES, CORR_THRESHOLD,
    PROTECT_EQUITIES, SHORT_TERM_BOND_WORDS, ANCHOR_TO_SECTOR,
    MANUAL_SECTOR_OVERRIDES,
)
from data_loader import get_fullname, get_corr_value


def _match_keywords(text_lower: str, keywords: list[str]) -> bool:
    """키워드 리스트 중 하나라도 텍스트에 포함되면 True"""
    return any(kw in text_lower for kw in keywords)


def _match_ticker_patterns(ticker: str, patterns: list[str]) -> bool:
    """티커가 패턴 리스트에 포함되면 True"""
    return ticker in patterns


def classify_by_keywords(ticker: str, fullname: str) -> str | None:
    """Pass 1: 키워드 기반 분류. 매칭되면 섹터 ID 반환, 아니면 None"""
    fn_lower = fullname.lower()

    # VIX 관련은 무조건 인버스/숏 (S22)
    # 단, "low volatility index" 같은 저변동성 전략 ETF는 제외
    if 'vix' in fn_lower or ('volatility index' in fn_lower and 'low volatility' not in fn_lower):
        return 'S22'

    for sector_id, rules in KEYWORD_RULES.items():
        # ticker 패턴 체크 (우선)
        if _match_ticker_patterns(ticker, rules.get('ticker_patterns', [])):
            return sector_id

        # 키워드 체크
        keywords = rules.get('keywords', [])
        exclude_if = rules.get('exclude_if', [])

        if _match_keywords(fn_lower, keywords):
            # exclude_if가 있으면, 해당 키워드가 포함되어 있을 때 이 규칙 적용 안 함
            if exclude_if and _match_keywords(fn_lower, exclude_if):
                continue
            return sector_id

    return None


def classify_by_correlation(ticker: str, df_corr_monthly: pd.DataFrame, df_corr_daily: pd.DataFrame, scraped: dict[str, Any]) -> tuple[str, float]:
    """Pass 2 & 3: 상관계수 기반 분류

    월간 상관계수 우선, 없으면 일간 fallback.
    가장 높은 상관계수의 앵커 섹터로 배정.
    """
    # 비채권 섹터 앵커 (주식 보호용)
    non_equity_anchors = set()
    equity_sectors = set()
    for sid, sdef in SECTOR_DEFS.items():
        if sdef['asset_class'] == 'EQUITY':
            equity_sectors.add(sid)
        elif sdef['anchor']:
            non_equity_anchors.add(sdef['anchor'])

    # 상관계수 소스 결정 (월간 우선)
    if ticker in df_corr_monthly.columns:
        corr_source = df_corr_monthly
    elif ticker in df_corr_daily.columns:
        corr_source = df_corr_daily
    else:
        return 'S24', 0.0  # 상관계수 데이터 없음 → 테마/특수목적

    best_sector = None
    best_corr = -999.0

    for sector_id, sdef in SECTOR_DEFS.items():
        anchor = sdef['anchor']
        if not anchor:
            continue

        r = get_corr_value(anchor, ticker, df_corr_monthly, df_corr_daily)

        # 주식 보호: PROTECT_EQUITIES에 있는 티커는 비주식 앵커로 끌려가지 않게
        if ticker in PROTECT_EQUITIES and anchor in non_equity_anchors:
            continue

        if r > best_corr:
            best_corr = r
            best_sector = sector_id

    if best_sector and best_corr >= CORR_THRESHOLD:
        return best_sector, best_corr
    else:
        return 'S24', best_corr  # Fallback: 테마/특수목적


def classify_all(all_tickers: set[str], scraped: dict[str, Any], df_corr_monthly: pd.DataFrame, df_corr_daily: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """전체 ETF를 섹터로 분류

    Args:
        all_tickers: 전체 ETF 티커 셋
        scraped: 스크래핑 정보 dict
        df_corr_monthly: 월간 상관계수 매트릭스
        df_corr_daily: 일간 상관계수 매트릭스

    Returns:
        dict: ticker → {'sector': 섹터ID, 'method': 분류방법, 'r_anchor': 상관계수}
    """
    classification: dict[str, dict[str, Any]] = {}
    method_counts: defaultdict[str, int] = defaultdict(int)

    for ticker in sorted(all_tickers):
        fullname = get_fullname(ticker, scraped)

        # Pass 0: 앵커 ETF는 자기 섹터에 무조건 배정
        # (수동 오버라이드보다 앵커 배정이 우선)
        sector: str | None = None
        if ticker in ANCHOR_TO_SECTOR:
            sector = ANCHOR_TO_SECTOR[ticker]
            classification[ticker] = {
                'sector': sector,
                'method': 'anchor',
                'r_anchor': 1.0,
            }
            method_counts['anchor'] += 1
            continue

        # Pass 0.5: 수동 섹터 오버라이드 (키워드/상관계수보다 우선)
        if ticker in MANUAL_SECTOR_OVERRIDES:
            sector = MANUAL_SECTOR_OVERRIDES[ticker]
            classification[ticker] = {
                'sector': sector,
                'method': 'manual_override',
                'r_anchor': 0.0,  # 나중에 fill_anchor_correlations에서 채움
            }
            method_counts['manual_override'] += 1
            continue

        # Pass 1: 키워드 룰
        sector = classify_by_keywords(ticker, fullname)
        if sector:
            classification[ticker] = {
                'sector': sector,
                'method': 'keyword',
                'r_anchor': 0.0,  # 키워드로 분류된 것은 나중에 상관계수 채움
            }
            method_counts['keyword'] += 1
            continue

        # Pass 2 & 3: 상관계수 기반
        sector, r_val = classify_by_correlation(
            ticker, df_corr_monthly, df_corr_daily, scraped
        )
        method = 'correlation' if r_val >= CORR_THRESHOLD else 'fallback'
        classification[ticker] = {
            'sector': sector,
            'method': method,
            'r_anchor': round(r_val, 4),
        }
        method_counts[method] += 1

    print(f"\n--- 분류 방법별 통계 ---")
    for method, count in sorted(method_counts.items()):
        print(f"  {method}: {count}개")

    return classification


def get_sector_members(classification: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    """분류 결과에서 섹터별 멤버 셋 추출

    Returns:
        dict: sector_id → set of tickers
    """
    members = defaultdict(set)
    for ticker, info in classification.items():
        members[info['sector']].add(ticker)
    return dict(members)


def fill_anchor_correlations(classification: dict[str, dict[str, Any]], sector_members: dict[str, set[str]], df_corr_monthly: pd.DataFrame, df_corr_daily: pd.DataFrame) -> None:
    """키워드로 분류된 ETF의 r_anchor를 실제 상관계수로 채움"""
    for sector_id, tickers in sector_members.items():
        anchor = SECTOR_DEFS[sector_id]['anchor']
        if not anchor:
            continue

        for ticker in tickers:
            if classification[ticker]['r_anchor'] == 0.0 or classification[ticker]['method'] == 'keyword':
                r = get_corr_value(anchor, ticker, df_corr_monthly, df_corr_daily)
                classification[ticker]['r_anchor'] = round(r, 4)


def fill_super_anchor_correlations(classification: dict[str, dict[str, Any]], df_corr_monthly: pd.DataFrame, df_corr_daily: pd.DataFrame) -> None:
    """슈퍼섹터 소속 ETF의 r_anchor를 슈퍼섹터 앵커(QQQ)로 전면 재계산.

    분류 방법(키워드/상관계수)에 관계없이 모든 해당 섹터 ETF에 적용.
    """
    # 섹터ID → 슈퍼섹터 앵커 매핑
    sector_to_ss_anchor = {}
    for ss_def in SUPER_SECTOR_DEFS.values():
        for sid in ss_def['sub_sectors']:
            sector_to_ss_anchor[sid] = ss_def['anchor']

    updated = 0
    for ticker, info in classification.items():
        sid = info['sector']
        if sid in sector_to_ss_anchor:
            anchor = sector_to_ss_anchor[sid]
            r = get_corr_value(anchor, ticker, df_corr_monthly, df_corr_daily)
            classification[ticker]['r_anchor'] = round(r, 4)
            updated += 1

    print(f"  슈퍼섹터 앵커 재계산 완료: {updated}개 ETF (앵커: QQQ)")
