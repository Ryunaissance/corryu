#!/usr/bin/env python3
"""
CORRYU ETF 전체 지표 재계산 파이프라인

원본(raw/*.parquet) → 분류 → 레거시 → 지표 → etf_data.json → HTML

실행 방법:
    python scripts/compute_all.py

config.py 규칙을 바꾸었을 때도 이 스크립트 하나로 반영 완료.
Supabase 불필요, 약 5~15분 소요.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

# src/ 모듈 경로 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from config import SECTOR_DEFS, SUPER_SECTOR_DEFS, MY_PORTFOLIO, OUTPUT_DIR
from data_loader import (
    load_price_data, load_scraped_info, load_meta_df,
    compute_perf_stats, compute_corr_monthly, compute_corr_daily,
    load_expense_ratios, load_dividend_yields, get_all_tickers,
)
from classify import (
    classify_all, get_sector_members,
    fill_anchor_correlations, fill_super_anchor_correlations,
)
from verify import verify_mece, spot_check
from legacy import assess_all_legacy
from metrics import compute_etf_metrics, compute_sector_stats


# ════════════════════════════════════════════════════════════════════
# 빌드 헬퍼
# ════════════════════════════════════════════════════════════════════

def build_sector_meta(sector_members, all_etf_data):
    meta = {}
    for sid, sdef in SECTOR_DEFS.items():
        etfs = all_etf_data.get(sid, [])
        stats = compute_sector_stats(etfs)
        meta[sid] = {
            'name':         sdef['name'],
            'name_en':      sdef['name_en'],
            'asset_class':  sdef['asset_class'],
            'anchor':       sdef['anchor'] or '—',
            'icon':         sdef['icon'],
            'super_sector': sdef.get('super_sector'),
            **stats,
        }
    return meta


def build_all_etf_data(
    sector_members, classification, legacy_results,
    df_price, perf_stats, scraped,
    df_corr_monthly, df_corr_daily,
    expense_ratios, dividend_yields,
):
    all_data = {}
    for sid in sorted(SECTOR_DEFS.keys()):
        tickers = sector_members.get(sid, set())
        etf_list = []
        for ticker in tickers:
            info = compute_etf_metrics(
                ticker, df_price, perf_stats, scraped, classification,
                df_corr_monthly, df_corr_daily, legacy_results,
                expense_ratios=expense_ratios,
                dividend_yields=dividend_yields,
            )
            info['mine'] = 1 if ticker in MY_PORTFOLIO else 0
            etf_list.append(info)
        etf_list.sort(key=lambda x: (-x['mine'], x['rank']))
        all_data[sid] = etf_list
    return all_data


# ════════════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════════════

def main():
    print('=' * 55)
    print('CORRYU ETF 전체 재계산')
    print('=' * 55)

    # ── 1. 원본 데이터 로드 ──────────────────────────────────────
    print('\n[1/7] 원본 데이터 로드...')
    df_price = load_price_data()
    scraped  = load_scraped_info()
    print(f'  가격: {df_price.shape[1]} ETF × {df_price.shape[0]} 거래일')
    print(f'  메타: {len(scraped)} ETF')

    # ── 2. 성과 지표 (CAGR · Vol · Sortino) ─────────────────────
    print('\n[2/7] 성과 지표 계산 (CAGR · Vol · Sortino)...')
    perf_stats = compute_perf_stats(df_price)
    valid = sum(1 for v in perf_stats.values() if v['CAGR'] != 0)
    print(f'  계산 완료: {valid}/{len(perf_stats)} ETF (데이터 충분)')

    # ── 3. 상관계수 ──────────────────────────────────────────────
    print('\n[3/7] 상관계수 계산...')
    print('  월간 상관계수...')
    df_corr_monthly = compute_corr_monthly(df_price)
    print(f'    → {df_corr_monthly.shape[0]} × {df_corr_monthly.shape[1]}')
    print('  일간 상관계수...')
    df_corr_daily = compute_corr_daily(df_price)
    print(f'    → {df_corr_daily.shape[0]} × {df_corr_daily.shape[1]}')

    # ── 4. 분류 ─────────────────────────────────────────────────
    print('\n[4/7] ETF 분류...')
    all_tickers = get_all_tickers(df_corr_daily)
    print(f'  전체 ETF 유니버스: {len(all_tickers)}개')

    classification = classify_all(all_tickers, scraped, df_corr_monthly, df_corr_daily)
    sector_members = get_sector_members(classification)
    fill_anchor_correlations(classification, sector_members, df_corr_monthly, df_corr_daily)
    fill_super_anchor_correlations(classification, df_corr_monthly, df_corr_daily)

    verify_mece(classification, all_tickers)
    spot_check(classification, scraped)

    # ── 5. 레거시 판별 ───────────────────────────────────────────
    print('\n[5/7] 레거시 판별...')
    legacy_results = assess_all_legacy(
        sector_members, classification,
        df_corr_monthly, df_corr_daily,
        scraped, perf_stats, df_price,
    )

    # ── 6. ETF 데이터 JSON 생성 ──────────────────────────────────
    print('\n[6/7] etf_data.json 생성...')
    expense_ratios  = load_expense_ratios()
    dividend_yields = load_dividend_yields()
    print(f'  수수료: {len(expense_ratios)}개  |  배당: {len(dividend_yields)}개')

    all_etf_data = build_all_etf_data(
        sector_members, classification, legacy_results,
        df_price, perf_stats, scraped,
        df_corr_monthly, df_corr_daily,
        expense_ratios, dividend_yields,
    )
    sector_meta = build_sector_meta(sector_members, all_etf_data)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    as_of = df_price.index[-1].strftime('%Y-%m-%d')

    etf_data_path = os.path.join(OUTPUT_DIR, 'etf_data.json')
    with open(etf_data_path, 'w', encoding='utf-8') as f:
        json.dump({
            'as_of':      as_of,
            'sectorMeta': sector_meta,
            'allData':    all_etf_data,
            'superSectorDefs': {
                k: {
                    'name': v['name'], 'name_en': v['name_en'],
                    'anchor': v['anchor'], 'icon': v['icon'],
                    'color': v['color'], 'sub_sectors': v['sub_sectors'],
                }
                for k, v in SUPER_SECTOR_DEFS.items()
            },
        }, f, ensure_ascii=False, separators=(',', ':'))
    print(f'  저장: {etf_data_path}')

    cls_path = os.path.join(OUTPUT_DIR, 'classification.json')
    cls_export = {}
    for ticker, info in classification.items():
        sid  = info['sector']
        sdef = SECTOR_DEFS[sid]
        cls_export[ticker] = {
            'sector_id':     sid,
            'sector_name':   sdef['name'],
            'asset_class':   sdef['asset_class'],
            'method':        info['method'],
            'r_anchor':      info['r_anchor'],
            'is_legacy':     legacy_results.get(ticker, {}).get('is_legacy', False),
            'legacy_reasons': legacy_results.get(ticker, {}).get('reasons', []),
        }
    with open(cls_path, 'w', encoding='utf-8') as f:
        json.dump(cls_export, f, ensure_ascii=False, indent=2)
    print(f'  저장: {cls_path}')

    # ── 6b. 개별 ETF JSON 생성 ───────────────────────────────────
    print('\n=== build_etf_pages: 개별 ETF JSON 생성 ===')
    sys.path.insert(0, str(ROOT))
    from build_etf_pages import main as build_etf_pages_main
    build_etf_pages_main()
    print('✅ 개별 ETF JSON 생성 완료')

    # ── 6c. 백테스트 실수익률 데이터 생성 ────────────────────────
    print('\n=== build_backtest_data: 연도별 실수익률 생성 ===')
    from build_backtest_data import main as build_backtest_data_main
    build_backtest_data_main()
    print('✅ backtest_data.json 생성 완료')

    # ── 6d. 상관계수 월간 수익률 데이터 생성 ────────────────────────
    print('\n=== build_corr_data: 월간 수익률 JSON 생성 ===')
    from build_corr_data import main as build_corr_data_main
    build_corr_data_main()
    print('✅ corr_returns.json 생성 완료')

    # ── 7. HTML 생성 ─────────────────────────────────────────────
    print('\n[7/7] HTML 생성...')
    render_script = str(ROOT / 'render_html.py')
    subprocess.run([sys.executable, render_script], check=True)

    # ── 완료 요약 ─────────────────────────────────────────────────
    total  = sum(m['count']  for m in sector_meta.values())
    active = sum(m['active'] for m in sector_meta.values())
    legacy = sum(m['legacy'] for m in sector_meta.values())
    print(f'\n{"=" * 55}')
    print(f'재계산 완료')
    print(f'  전체: {total:,}  Active: {active:,}  Legacy: {legacy:,}')
    print(f'{"=" * 55}')


if __name__ == '__main__':
    main()
