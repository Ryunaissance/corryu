"""
CORRYU ETF Dashboard - 지표 계산 모듈
Z-score, 200DMA 이격도, 52주 MDD, 태그 생성
"""
import pandas as pd
import numpy as np

from config import TAG_RULES


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


def generate_tags(fullname):
    """ETF 이름에서 태그 생성"""
    fn_upper = fullname.upper()
    tags = []
    for tag_name, keywords in TAG_RULES.items():
        if any(kw in fn_upper for kw in keywords):
            tags.append(tag_name)
    return tags


def compute_etf_metrics(ticker, df_price, perf_stats, scraped, classification,
                        df_corr_monthly, df_corr_daily, legacy_info):
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
        inc_date = str(scraped.get(ticker, {}).get('inception_date', '1900-01-01'))[:10]
    except Exception:
        inc_date = '1900-01-01'

    # 짧은 연혁 판별
    is_short_history = True
    try:
        if '1900' not in inc_date and inc_date > '2021-05-20':
            is_short_history = True
        elif '1900' not in inc_date:
            is_short_history = False
    except Exception:
        pass

    # 가격 기반 지표
    z_score = 0.0
    ma_div = 0.0
    h52_mdd = 0.0

    if ticker in df_price.columns:
        ts = df_price[ticker].dropna()
        if len(ts) >= 200:
            z_score = compute_z_score(ts)
            ma_div = compute_200dma_divergence(ts)
            h52_mdd = compute_52w_mdd(ts)

    # r_SPY (글로벌 참조 상관계수)
    r_spy = 0.0
    if 'SPY' in df_corr_monthly.columns and ticker in df_corr_monthly.columns:
        r_spy = df_corr_monthly['SPY'].get(ticker, 0.0)
    elif 'SPY' in df_corr_daily.columns and ticker in df_corr_daily.columns:
        r_spy = df_corr_daily['SPY'].get(ticker, 0.0)
    if pd.isna(r_spy):
        r_spy = 0.0

    return {
        't': ticker,
        'n': fullname,
        'rk': rank,
        'mc': market_cap,
        'r': round(float(cl.get('r_anchor', 0)), 3),
        'r_spy': round(float(r_spy), 3),
        'z': round(float(z_score), 2),
        'ma': round(float(ma_div), 1),
        'h52': round(float(h52_mdd), 1),
        'cagr': round(float(p.get('CAGR', 0)), 1),
        'v': round(float(p.get('Vol', 0)), 1),
        's': round(float(p.get('Sortino', 0)), 2),
        'sh': is_short_history,
        'inc': inc_date,
        'tags': generate_tags(fullname),
        'isl': leg.get('is_legacy', False),
        'lr': leg.get('reasons', []),
        'ld': leg.get('details', []),
    }


def compute_sector_stats(sector_etf_data):
    """섹터의 요약 통계 계산"""
    if not sector_etf_data:
        return {'count': 0, 'active': 0, 'legacy': 0,
                'avg_cagr': 0, 'avg_vol': 0, 'avg_sortino': 0}

    active_data = [e for e in sector_etf_data if not e['isl'] and not e['sh']]
    cagrs = [e['cagr'] for e in active_data if e['cagr'] != 0]
    vols = [e['v'] for e in active_data if e['v'] != 0]
    sortinos = [e['s'] for e in active_data if e['s'] != 0]

    return {
        'count': len(sector_etf_data),
        'active': len([e for e in sector_etf_data if not e['isl']]),
        'legacy': len([e for e in sector_etf_data if e['isl']]),
        'avg_cagr': round(np.mean(cagrs), 1) if cagrs else 0,
        'avg_vol': round(np.mean(vols), 1) if vols else 0,
        'avg_sortino': round(np.mean(sortinos), 2) if sortinos else 0,
    }
