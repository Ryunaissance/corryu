"""
CORRYU ETF Dashboard - 데이터 로딩 모듈
pkl/csv 파일에서 데이터를 로드하고 검증
"""
import os
import pickle
from typing import Any
import pandas as pd
from config import DATA_PROCESSED, DATA_SCRAPED, CORR_MONTHLY_CSV, CORR_DAILY_CSV


def load_price_data() -> pd.DataFrame:
    """일별 종가 데이터 로드 (DataFrame[datetime × ticker])"""
    path = f'{DATA_PROCESSED}/etf_close_data_cleaned.pkl'
    with open(path, 'rb') as f:
        return pickle.load(f)


def load_perf_stats() -> dict[str, dict[str, Any]]:
    """성과 통계 로드 (Dict[ticker → {CAGR, Vol, Sortino, IsRolling}])"""
    path = f'{DATA_PROCESSED}/etf_perf_stats.pkl'
    with open(path, 'rb') as f:
        return pickle.load(f)


def load_scraped_info() -> dict[str, dict[str, Any]]:
    """스크래핑 정보 로드 (Dict[ticker → {rank, fullname, market_cap, inception_date}])"""
    path = f'{DATA_SCRAPED}/scraped_info.pkl'
    with open(path, 'rb') as f:
        return pickle.load(f)


def load_corr_monthly() -> pd.DataFrame:
    """월간 수익률 상관계수 매트릭스 로드 (1,354 tickers)"""
    return pd.read_csv(CORR_MONTHLY_CSV, index_col=0)


def load_corr_daily() -> pd.DataFrame:
    """일간 수익률 상관계수 매트릭스 로드 (1,654 tickers)"""
    return pd.read_csv(CORR_DAILY_CSV, index_col=0)


def get_all_tickers(df_corr_daily: pd.DataFrame) -> set[str]:
    """상관계수 매트릭스에서 인덱스 티커(^GSPC 등) 제외한 전체 ETF 티커셋 반환"""
    return {t for t in df_corr_daily.columns if not t.startswith('^')}


def load_expense_ratios() -> dict[str, float]:
    """수수료 데이터 로드 (Dict[ticker → float], 없는 경우 빈 dict 반환)

    yfinance에서 수집한 annualReportExpenseRatio / totalExpenseRatio 값.
    소수점 형식 (예: 0.0003 = 0.03%).
    """
    path = f'{DATA_SCRAPED}/expense_ratios.pkl'
    if not os.path.exists(path):
        return {}
    with open(path, 'rb') as f:
        return pickle.load(f)


def load_all() -> tuple[pd.DataFrame, dict[str, dict[str, Any]], dict[str, dict[str, Any]], pd.DataFrame, pd.DataFrame]:
    """모든 데이터를 한 번에 로드하여 반환

    Returns:
        tuple: (df_price, perf_stats, scraped, df_corr_monthly, df_corr_daily)
    """
    print("데이터 로딩 중...")
    df_price = load_price_data()
    perf_stats = load_perf_stats()
    scraped = load_scraped_info()
    df_corr_monthly = load_corr_monthly()
    df_corr_daily = load_corr_daily()

    all_tickers = get_all_tickers(df_corr_daily)
    monthly_tickers = {t for t in df_corr_monthly.columns if not t.startswith('^')}

    print(f"  일별 종가: {df_price.shape[1]} tickers × {df_price.shape[0]} days")
    print(f"  성과 통계: {len(perf_stats)} tickers")
    print(f"  스크래핑 정보: {len(scraped)} tickers")
    print(f"  월간 상관계수: {len(monthly_tickers)} tickers")
    print(f"  일간 상관계수: {len(all_tickers)} tickers")
    print(f"  월간에만 없는 ETF: {len(all_tickers - monthly_tickers)}개 (데이터 36개월 미만)")

    return df_price, perf_stats, scraped, df_corr_monthly, df_corr_daily


def get_fullname(ticker: str, scraped: dict[str, dict[str, Any]]) -> str:
    """ETF 풀네임 반환"""
    return scraped.get(ticker, {}).get('fullname', ticker)


def get_market_cap(ticker: str, scraped: dict[str, dict[str, Any]]) -> float:
    """시가총액 반환"""
    return scraped.get(ticker, {}).get('market_cap', 0)


def get_rank(ticker: str, scraped: dict[str, dict[str, Any]]) -> int:
    """시가총액 순위 반환"""
    return scraped.get(ticker, {}).get('rank', 9999)


def get_corr_value(ref_ticker: str, ticker: str, df_corr_monthly: pd.DataFrame, df_corr_daily: pd.DataFrame) -> float:
    """두 티커 간 상관계수 반환 (월간 우선, 없으면 일간 fallback)

    Args:
        ref_ticker: 기준 티커 (예: 앵커 ETF, 'SPY')
        ticker: 대상 티커
        df_corr_monthly: 월간 상관계수 매트릭스
        df_corr_daily: 일간 상관계수 매트릭스

    Returns:
        float: 상관계수 (데이터 없으면 0.0)
    """
    if ref_ticker in df_corr_monthly.columns and ticker in df_corr_monthly.columns:
        r = df_corr_monthly[ref_ticker].get(ticker, 0.0)
    elif ref_ticker in df_corr_daily.columns and ticker in df_corr_daily.columns:
        r = df_corr_daily[ref_ticker].get(ticker, 0.0)
    else:
        return 0.0
    return 0.0 if pd.isna(r) else float(r)
