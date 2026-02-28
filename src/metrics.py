"""
CORRYU ETF Dashboard - 지표 계산 모듈
Z-score, 200DMA 이격도, 52주 MDD
"""
import pandas as pd
import numpy as np

from config import SHORT_HISTORY_CUTOFF
from data_loader import get_corr_value


def compute_z_score(prices):
    """200일 이동평균 기반 Z-Score 계산"""
    if len(prices) < 200:
        return 0.0
    ma200 = prices.rolling(200).mean().iloc[-1]
    std200 = prices.rolling(200).std().iloc[-1]
    if pd.isna(std200) or std200 == 0:
        return 0.0
    return (prices.iloc[-1] - ma200) / std200


def compute_200dma_divergence(prices):
    """200일 이동평균 이격도 (%)"""
    if len(prices) < 200:
        return 0.0
    ma200 = prices.rolling(200).mean().iloc[-1]
    if pd.isna(ma200) or ma200 == 0:
        return 0.0
    return (prices.iloc[-1] / ma200 - 1) * 100


def compute_52w_mdd(prices):
    """52주 최고가 대비 현재가 괴리율 (%)"""
    if len(prices) < 10:
        return 0.0
    recent = prices.tail(252)
    high_52 = recent.max()
    if pd.isna(high_52) or high_52 == 0:
        return 0.0
    return (prices.iloc[-1] / high_52 - 1) * 100


def compute_rsi(prices, period=14):
    """RSI (Wilder 방식, 기본 14일)

    Returns:
        float: RSI 값 (0~100), 데이터 부족 시 None
    """
    if len(prices) < period + 1:
        return None
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 1) if not pd.isna(val) else None


def compute_52w_range_pct(prices):
    """52주 레인지 내 위치 (%)

    0% = 52주 최저, 100% = 52주 최고

    Returns:
        float: 0~100, 데이터 부족 시 None
    """
    if len(prices) < 10:
        return None
    recent = prices.tail(252)
    high = recent.max()
    low = recent.min()
    current = prices.iloc[-1]
    if pd.isna(high) or pd.isna(low) or high == low:
        return None
    return round(float((current - low) / (high - low) * 100), 1)


def compute_etf_metrics(ticker, df_price, perf_stats, scraped, classification,
                        df_corr_monthly, df_corr_daily, legacy_info,
                        expense_ratios=None):
    """단일 ETF의 모든 대시보드 지표를 계산

    Returns:
        dict: 대시보드 JSON 데이터 항목
    """
    fullname = scraped.get(ticker, {}).get('fullname', ticker)
    rank = scraped.get(ticker, {}).get('rank', 9999)
    market_cap = scraped.get(ticker, {}).get('market_cap', 0)
    p = perf_stats.get(ticker, {})
    cl = classification.get(ticker, {})
    leg = legacy_info.get(ticker, {})

    # 상장일
    try:
        inception = str(scraped.get(ticker, {}).get('inception_date', '1900-01-01'))[:10]
    except Exception:
        inception = '1900-01-01'

    # 짧은 연혁 판별
    short_history = True
    try:
        if '1900' not in inception and inception > SHORT_HISTORY_CUTOFF:
            short_history = True
        elif '1900' not in inception:
            short_history = False
    except Exception:
        pass

    # 가격 기반 지표
    z_score = 0.0
    ma200_pct = 0.0
    mdd_52w = 0.0
    rsi = None
    range_52w = None

    if ticker in df_price.columns:
        ts = df_price[ticker].dropna()
        if len(ts) >= 200:
            z_score = compute_z_score(ts)
            ma200_pct = compute_200dma_divergence(ts)
            mdd_52w = compute_52w_mdd(ts)
        if len(ts) >= 15:
            rsi = compute_rsi(ts)
            range_52w = compute_52w_range_pct(ts)

    # r_spy (글로벌 참조 상관계수)
    r_spy = get_corr_value('SPY', ticker, df_corr_monthly, df_corr_daily)

    # 수수료 (expense_ratios dict에서 조회, 없으면 None)
    exp_ratio = None
    if expense_ratios:
        v = expense_ratios.get(ticker)
        if v is not None:
            exp_ratio = round(float(v), 6)

    return {
        'ticker': ticker,
        'name': fullname,
        'rank': rank,
        'aum': market_cap,
        'r_anchor': round(float(cl.get('r_anchor', 0)), 3),
        'r_spy': round(float(r_spy), 3),
        'z_score': round(float(z_score), 2),
        'ma200_pct': round(float(ma200_pct), 1),
        'mdd_52w': round(float(mdd_52w), 1),
        'rsi': rsi,
        'range_52w': range_52w,
        'cagr': round(float(p.get('CAGR', 0)), 1),
        'vol': round(float(p.get('Vol', 0)), 1),
        'sortino': round(float(p.get('Sortino', 0)), 2),
        'short_history': short_history,
        'inception': inception,
        'exp_ratio': exp_ratio,
        'is_legacy': leg.get('is_legacy', False),
        'legacy_reasons': leg.get('reasons', []),
        'legacy_detail': leg.get('details', []),
    }


def compute_sector_stats(sector_etf_data):
    """섹터의 요약 통계 계산"""
    if not sector_etf_data:
        return {'count': 0, 'active': 0, 'legacy': 0,
                'avg_cagr': 0, 'avg_vol': 0, 'avg_sortino': 0}

    active_data = [e for e in sector_etf_data if not e['is_legacy'] and not e['short_history']]
    cagrs = [e['cagr'] for e in active_data if e['cagr'] != 0]
    vols = [e['vol'] for e in active_data if e['vol'] != 0]
    sortinos = [e['sortino'] for e in active_data if e['sortino'] != 0]

    return {
        'count': len(sector_etf_data),
        'active': len([e for e in sector_etf_data if not e['is_legacy']]),
        'legacy': len([e for e in sector_etf_data if e['is_legacy']]),
        'avg_cagr': round(np.mean(cagrs), 1) if cagrs else 0,
        'avg_vol': round(np.mean(vols), 1) if vols else 0,
        'avg_sortino': round(np.mean(sortinos), 2) if sortinos else 0,
    }
