"""
CORRYU ETF Dashboard - 레거시 ETF 판별 엔진
자동 규칙 + 수동 오버라이드
"""
import numpy as np
import pandas as pd

from config import (
    SECTOR_DEFS, MANUAL_LEGACY_OVERRIDES, LEGACY_EXEMPTIONS,
    LEGACY_MIN_AUM, LEGACY_MIN_TRADING_DAYS,
    LEGACY_TRACKING_ERROR_THRESHOLD, LEGACY_NEAR_DUPLICATE_CORR,
    LEGACY_NEAR_DUPLICATE_TOP_N,
)


def assess_sector_legacy(sector_id, sector_tickers, classification,
                         df_corr_monthly, df_corr_daily,
                         scraped, perf_stats, df_price):
    """단일 섹터의 레거시 ETF를 판별

    Returns:
        dict: ticker → {is_legacy, reasons, details}
    """
    anchor = SECTOR_DEFS[sector_id]['anchor']
    results = {}

    # 섹터 내 소르티노 분포 계산 (하위 20% 기준)
    sortinos = []
    for t in sector_tickers:
        s = perf_stats.get(t, {}).get('Sortino', None)
        if s is not None and s != 0:
            sortinos.append(s)
    sortino_20th = np.percentile(sortinos, 20) if len(sortinos) >= 5 else -999

    # AUM 기준 상위 N개 추출 (중복 체크용)
    aum_sorted = sorted(
        sector_tickers,
        key=lambda t: scraped.get(t, {}).get('market_cap', 0),
        reverse=True
    )
    top_n_tickers = set(aum_sorted[:LEGACY_NEAR_DUPLICATE_TOP_N])

    for ticker in sector_tickers:
        reasons = []
        details = []

        # 수동 오버라이드만 적용 (자동 규칙 비활성화)
        if ticker in MANUAL_LEGACY_OVERRIDES:
            reasons.append('MANUAL')
            details.append(f'{MANUAL_LEGACY_OVERRIDES[ticker]}')

        is_legacy = len(reasons) >= 1
        results[ticker] = {
            'is_legacy': is_legacy,
            'reasons': reasons,
            'details': details,
        }

    return results


def assess_all_legacy(sector_members, classification,
                      df_corr_monthly, df_corr_daily,
                      scraped, perf_stats, df_price):
    """전체 섹터에 대해 레거시 판별 실행

    Returns:
        dict: ticker → {is_legacy, reasons, details}
    """
    all_legacy = {}
    legacy_summary = {}

    for sector_id, tickers in sorted(sector_members.items()):
        results = assess_sector_legacy(
            sector_id, tickers, classification,
            df_corr_monthly, df_corr_daily,
            scraped, perf_stats, df_price
        )
        all_legacy.update(results)

        legacy_count = sum(1 for v in results.values() if v['is_legacy'])
        legacy_summary[sector_id] = {
            'total': len(tickers),
            'legacy': legacy_count,
            'active': len(tickers) - legacy_count,
        }

    print(f"\n--- 레거시 판별 결과 ---")
    total_legacy = 0
    total_all = 0
    for sid in sorted(SECTOR_DEFS.keys()):
        if sid not in legacy_summary:
            continue
        s = legacy_summary[sid]
        sdef = SECTOR_DEFS[sid]
        pct = s['legacy'] / s['total'] * 100 if s['total'] > 0 else 0
        print(f"  {sid} {sdef['name']:12s}: {s['legacy']:3d}/{s['total']:3d} legacy ({pct:.0f}%)")
        total_legacy += s['legacy']
        total_all += s['total']

    pct_total = total_legacy / total_all * 100 if total_all > 0 else 0
    print(f"  {'─'*45}")
    print(f"  {'합계':18s}: {total_legacy:3d}/{total_all:3d} legacy ({pct_total:.0f}%)")

    return all_legacy
