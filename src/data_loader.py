"""
CORRYU ETF Dashboard - 데이터 로딩 모듈
raw/*.parquet에서 원본 데이터를 로드하고, 상관계수·성과지표를 인라인 계산
"""
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import RAW_DIR, MAR_ANNUAL, MAR_DAILY, MIN_ROLLING_DAYS

PRICES_PARQUET = Path(RAW_DIR) / 'prices_close.parquet'
META_PARQUET   = Path(RAW_DIR) / 'meta.parquet'

# 롤링 성과 계산 최대 기간 (약 10년)
ROLLING_MAX_DAYS = 2520


# ── 원본 데이터 로드 ─────────────────────────────────────────────────

def load_price_data() -> pd.DataFrame:
    """일별 수정종가 로드 (wide: DatetimeIndex × ticker)"""
    return pd.read_parquet(PRICES_PARQUET)


def load_scraped_info() -> dict[str, dict[str, Any]]:
    """메타 데이터 로드 → scraped dict 형식 반환

    Returns:
        Dict[ticker → {fullname, market_cap, rank, inception_date}]
    """
    df = pd.read_parquet(META_PARQUET)
    result: dict[str, dict[str, Any]] = {}
    for ticker, row in df.iterrows():
        result[str(ticker)] = {
            'fullname':       str(row.get('fullname', ticker)),
            'market_cap':     float(row.get('market_cap', 0) or 0),
            'rank':           int(row.get('rank', 9999) or 9999),
            'inception_date': str(row.get('inception_date', '1900-01-01') or '1900-01-01'),
        }
    return result


def load_meta_df() -> pd.DataFrame:
    """메타 DataFrame 원형 반환 (expense_ratio, div_yield 포함)"""
    return pd.read_parquet(META_PARQUET)


# ── 인라인 계산 ──────────────────────────────────────────────────────

def compute_perf_stats(df_price: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """10년 롤링 CAGR, 연간 변동성, 소르티노 계산

    Returns:
        Dict[ticker → {CAGR(%), Vol(%), Sortino, IsRolling}]
    """
    stats: dict[str, dict[str, Any]] = {}
    daily_ret = df_price.pct_change()

    for ticker in df_price.columns:
        ts  = df_price[ticker].dropna()
        ret = daily_ret[ticker].reindex(ts.index).dropna()
        n   = len(ts)

        if n < MIN_ROLLING_DAYS:
            stats[ticker] = {'CAGR': 0.0, 'Vol': 0.0, 'Sortino': 0.0, 'IsRolling': False}
            continue

        roll = min(n, ROLLING_MAX_DAYS)
        ts_r  = ts.tail(roll)
        ret_r = ret.tail(roll)
        years = roll / 252

        cagr = (float(ts_r.iloc[-1]) / float(ts_r.iloc[0])) ** (1 / years) - 1
        vol  = float(ret_r.std()) * (252 ** 0.5)

        downside = ret_r[ret_r < MAR_DAILY]
        down_std = float(downside.std()) * (252 ** 0.5) if len(downside) > 1 else 0.0
        sortino  = (cagr - MAR_ANNUAL) / down_std if down_std > 0 else 0.0

        stats[ticker] = {
            'CAGR':      round(cagr * 100, 2),
            'Vol':       round(vol  * 100, 2),
            'Sortino':   round(sortino, 3),
            'IsRolling': roll < n,
        }

    return stats


def compute_corr_monthly(df_price: pd.DataFrame) -> pd.DataFrame:
    """월말 수익률 기반 상관계수 행렬 계산 (분류에 사용)"""
    monthly = df_price.resample('ME').last().pct_change().dropna(how='all')
    # 36개월 미만 데이터는 제외 (NaN 열 → 상관계수 0)
    valid = monthly.columns[monthly.notna().sum() >= 36]
    return monthly[valid].corr()


def compute_corr_daily(df_price: pd.DataFrame) -> pd.DataFrame:
    """일간 수익률 기반 상관계수 행렬 계산 (월간 fallback용)"""
    daily_ret = df_price.pct_change().dropna(how='all')
    return daily_ret.corr()


# ── 통합 로드 ────────────────────────────────────────────────────────

def load_all() -> tuple[
    pd.DataFrame,
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    pd.DataFrame,
    pd.DataFrame,
]:
    """모든 데이터를 한 번에 로드·계산하여 반환

    Returns:
        (df_price, perf_stats, scraped, df_corr_monthly, df_corr_daily)
    """
    print("데이터 로딩 중...")
    df_price = load_price_data()
    scraped  = load_scraped_info()

    print(f"  일별 종가: {df_price.shape[1]} tickers × {df_price.shape[0]} days")
    print(f"  메타:     {len(scraped)} tickers")

    print("  성과지표 계산 중 (CAGR·Vol·Sortino)...")
    perf_stats = compute_perf_stats(df_price)

    print("  상관계수 계산 중 (월간)...")
    df_corr_monthly = compute_corr_monthly(df_price)
    print(f"    → {df_corr_monthly.shape[0]} × {df_corr_monthly.shape[1]}")

    print("  상관계수 계산 중 (일간)...")
    df_corr_daily = compute_corr_daily(df_price)
    print(f"    → {df_corr_daily.shape[0]} × {df_corr_daily.shape[1]}")

    monthly_tickers = set(df_corr_monthly.columns)
    daily_tickers   = set(df_corr_daily.columns)
    print(f"  월간에만 없는 ETF: {len(daily_tickers - monthly_tickers)}개 (36개월 미만)")

    return df_price, perf_stats, scraped, df_corr_monthly, df_corr_daily


def get_all_tickers(df_corr_daily: pd.DataFrame) -> set[str]:
    """^GSPC 등 지수 제외한 ETF 티커셋 반환"""
    return {t for t in df_corr_daily.columns if not t.startswith('^')}


# ── 보조 함수 (기존 인터페이스 유지) ─────────────────────────────────

def load_expense_ratios() -> dict[str, float]:
    """수수료 데이터 반환 (meta.parquet의 expense_ratio 열)"""
    df = load_meta_df()
    if 'expense_ratio' not in df.columns:
        return {}
    return {str(t): float(v) for t, v in df['expense_ratio'].dropna().items()}


def load_dividend_yields() -> dict[str, float]:
    """배당수익률 데이터 반환 (meta.parquet의 div_yield 열, 소수 형식)"""
    df = load_meta_df()
    if 'div_yield' not in df.columns:
        return {}
    return {str(t): float(v) for t, v in df['div_yield'].dropna().items()}


def get_fullname(ticker: str, scraped: dict[str, dict[str, Any]]) -> str:
    return scraped.get(ticker, {}).get('fullname', ticker)


def get_market_cap(ticker: str, scraped: dict[str, dict[str, Any]]) -> float:
    return scraped.get(ticker, {}).get('market_cap', 0)


def get_rank(ticker: str, scraped: dict[str, dict[str, Any]]) -> int:
    return scraped.get(ticker, {}).get('rank', 9999)


def get_corr_value(
    ref_ticker: str,
    ticker: str,
    df_corr_monthly: pd.DataFrame,
    df_corr_daily: pd.DataFrame,
) -> float:
    """두 티커 간 상관계수 반환 (월간 우선, 없으면 일간 fallback)"""
    if ref_ticker in df_corr_monthly.columns and ticker in df_corr_monthly.columns:
        r = df_corr_monthly[ref_ticker].get(ticker, 0.0)
    elif ref_ticker in df_corr_daily.columns and ticker in df_corr_daily.columns:
        r = df_corr_daily[ref_ticker].get(ticker, 0.0)
    else:
        return 0.0
    return 0.0 if pd.isna(r) else float(r)
