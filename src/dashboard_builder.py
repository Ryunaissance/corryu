"""
CORRYU ETF Dashboard - HTML 대시보드 생성 (단일 진입점)
데이터 로딩 → 분류 → 레거시 → 지표 → JSON 저장 → HTML 생성

HTML 템플릿은 루트의 render_html.py 가 단독 관리합니다.
HTML 수정 시 render_html.py 만 편집하세요.
"""
import json
import os
import subprocess
import sys
from typing import Any
import pandas as pd

from config import SECTOR_DEFS, SUPER_SECTOR_DEFS, ASSET_CLASSES, MY_PORTFOLIO, OUTPUT_DIR
from data_loader import load_all, load_expense_ratios, get_all_tickers, get_fullname, get_market_cap, get_rank
from classify import classify_all, get_sector_members, fill_anchor_correlations, fill_super_anchor_correlations
from verify import verify_mece, spot_check
from legacy import assess_all_legacy
from metrics import compute_etf_metrics, compute_sector_stats


def build_sector_meta(sector_members: dict[str, set[str]], all_etf_data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """섹터별 메타 정보 JSON 생성"""
    meta = {}
    for sid, sdef in SECTOR_DEFS.items():
        etfs = all_etf_data.get(sid, [])
        stats = compute_sector_stats(etfs)
        meta[sid] = {
            'name': sdef['name'],
            'name_en': sdef['name_en'],
            'asset_class': sdef['asset_class'],
            'anchor': sdef['anchor'] or '—',
            'icon': sdef['icon'],
            'super_sector': sdef.get('super_sector'),
            **stats,
        }
    return meta


def build_all_etf_data(sector_members: dict[str, set[str]], classification: dict[str, Any], legacy_results: dict[str, Any],
                       df_price: pd.DataFrame, perf_stats: dict[str, Any], scraped: dict[str, Any],
                       df_corr_monthly: pd.DataFrame, df_corr_daily: pd.DataFrame, expense_ratios: dict[str, float] | None = None) -> dict[str, list[dict[str, Any]]]:
    """전체 섹터별 ETF 데이터 JSON 생성"""
    all_data = {}

    for sid in sorted(SECTOR_DEFS.keys()):
        tickers = sector_members.get(sid, set())
        etf_list = []

        for ticker in tickers:
            etf_info = compute_etf_metrics(
                ticker, df_price, perf_stats, scraped, classification,
                df_corr_monthly, df_corr_daily, legacy_results,
                expense_ratios=expense_ratios
            )
            etf_info['mine'] = 1 if ticker in MY_PORTFOLIO else 0
            etf_list.append(etf_info)

        # 정렬: 내 보유종목 최우선, 그다음 시가총액 순
        etf_list.sort(key=lambda x: (-x['mine'], x['rank']))
        all_data[sid] = etf_list

    return all_data


def main() -> None:
    """메인 실행: 데이터 로딩 → 분류 → 레거시 → 지표 → HTML"""
    # 1. 데이터 로딩
    df_price, perf_stats, scraped, df_corr_monthly, df_corr_daily = load_all()
    all_tickers = get_all_tickers(df_corr_daily)
    print(f"\n전체 ETF 유니버스: {len(all_tickers)}개")

    # 2. MECE 분류
    print("\n=== 섹터 분류 실행 ===")
    classification = classify_all(all_tickers, scraped, df_corr_monthly, df_corr_daily)
    sector_members = get_sector_members(classification)
    fill_anchor_correlations(classification, sector_members, df_corr_monthly, df_corr_daily)
    # 슈퍼섹터(주식 시장) 소속 ETF의 r_anchor를 QQQ 기준으로 재계산
    fill_super_anchor_correlations(classification, df_corr_monthly, df_corr_daily)

    # 3. MECE 검증
    print("\n=== MECE 검증 ===")
    verify_mece(classification, all_tickers)
    spot_check(classification, scraped)

    # 4. 레거시 판별
    print("\n=== 레거시 판별 ===")
    legacy_results = assess_all_legacy(
        sector_members, classification,
        df_corr_monthly, df_corr_daily,
        scraped, perf_stats, df_price
    )

    # 5. 전체 ETF 데이터 생성
    print("\n대시보드 데이터 생성 중...")
    expense_ratios = load_expense_ratios()
    print(f"  수수료 데이터: {len(expense_ratios)}개 티커")
    all_etf_data = build_all_etf_data(
        sector_members, classification, legacy_results,
        df_price, perf_stats, scraped,
        df_corr_monthly, df_corr_daily,
        expense_ratios=expense_ratios
    )

    # 6. 섹터 메타 생성
    sector_meta = build_sector_meta(sector_members, all_etf_data)

    # 7. etf_data.json 저장 (HTML과 분리된 데이터 파일)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    etf_data_path = os.path.join(OUTPUT_DIR, 'etf_data.json')
    with open(etf_data_path, 'w', encoding='utf-8') as f:
        json.dump({
            'sectorMeta': sector_meta,
            'allData': all_etf_data,
            'superSectorDefs': {
                k: {'name': v['name'], 'name_en': v['name_en'],
                    'anchor': v['anchor'], 'icon': v['icon'],
                    'color': v['color'], 'sub_sectors': v['sub_sectors']}
                for k, v in SUPER_SECTOR_DEFS.items()
            },
        }, f, ensure_ascii=False, separators=(',', ':'))
    print(f"ETF 데이터 JSON 저장: {etf_data_path}")

    # 8. HTML 생성 — render_html.py 호출 (pandas 불필요, 단독 실행 가능)
    print("HTML 대시보드 생성 중...")
    render_script = os.path.join(os.path.dirname(OUTPUT_DIR), 'render_html.py')
    subprocess.run([sys.executable, render_script], check=True)

    print(f"\n{'='*50}")
    print(f"대시보드 생성 완료")
    print(f"  전체 ETF: {sum(m['count'] for m in sector_meta.values()):,}개")
    print(f"  Active: {sum(m['active'] for m in sector_meta.values()):,}개")
    print(f"  Legacy: {sum(m['legacy'] for m in sector_meta.values()):,}개")
    print(f"{'='*50}")

    # 9. classification.json 저장
    cls_path = os.path.join(OUTPUT_DIR, 'classification.json')
    cls_export = {}
    for ticker, info in classification.items():
        sid = info['sector']
        sdef = SECTOR_DEFS[sid]
        cls_export[ticker] = {
            'sector_id': sid,
            'sector_name': sdef['name'],
            'asset_class': sdef['asset_class'],
            'method': info['method'],
            'r_anchor': info['r_anchor'],
            'is_legacy': legacy_results.get(ticker, {}).get('is_legacy', False),
            'legacy_reasons': legacy_results.get(ticker, {}).get('reasons', []),
        }
    with open(cls_path, 'w', encoding='utf-8') as f:
        json.dump(cls_export, f, ensure_ascii=False, indent=2)
    print(f"분류 JSON 저장: {cls_path}")


if __name__ == '__main__':
    main()
