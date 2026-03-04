#!/usr/bin/env python3
"""
compute_sortino.py — CAGR / Vol / Sortino(MAR=4%) 전체 재계산

Supabase etf_prices 테이블의 실 adj_close 데이터를 기반으로
롤링 일간 수익률을 계산하고 성과 지표를 재산출합니다.

Sortino 공식:
    daily_ret  = adj_close.pct_change()
    downside   = daily_ret[daily_ret < MAR_daily]
    dd_annual  = downside.std() * sqrt(252)          # 연율화 하방편차
    sortino    = (CAGR - MAR_annual) / dd_annual

    - MAR(최소 수용 수익률) = 연 4.0% (월가 3-Month T-Bill 근사)
    - 분모 하방편차 < MIN_DD_FLOOR → Sortino = None (극소 분모 방어)
    - 하방일 < MIN_DOWNSIDE_DAYS  → Sortino = None (샘플 부족)

출력:
    data_processed/etf_perf_stats.pkl   — dashboard_builder.py 입력
    etf_database.json                   — ret / vol / sor / is_rolling 갱신

Usage:
    SUPABASE_URL=https://xxx.supabase.co \\
    SUPABASE_SERVICE_KEY=eyJ... \\
    python scripts/compute_sortino.py
"""

import json
import logging
import math
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd
from supabase import create_client

# ── 경로 설정 ──────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from config import (
    DATA_PROCESSED,
    MAR_ANNUAL,
    MAR_DAILY,
    MIN_ROLLING_DAYS,
    OUTPUT_DIR,
)

# ── 로깅 ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-7s %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)

# ── 파라미터 ───────────────────────────────────────────────────────────
BATCH_SIZE       = 100    # Supabase IN 절 티커 수
PAGE_SIZE        = 5_000  # Supabase 페이지당 행 수 (최대 10,000)
MIN_DAYS     = 63    # 최소 거래일 (≈3개월) — 미달 시 지표 None
MIN_DD_FLOOR = 1e-6  # RMS shortfall 플로어 — 사실상 0 분모 방어
TRADING_DAYS     = 252    # 연 거래일

ETF_DATA_JSON    = os.path.join(OUTPUT_DIR, 'etf_data.json')
ETF_DATABASE_JSON = os.path.join(ROOT, 'etf_database.json')
PERF_STATS_PKL   = os.path.join(DATA_PROCESSED, 'etf_perf_stats.pkl')


# ══════════════════════════════════════════════════════════════════════
# 지표 계산
# ══════════════════════════════════════════════════════════════════════

def compute_metrics(prices: pd.Series) -> dict:
    """
    단일 ETF adj_close 시계열 → CAGR / Vol / Sortino / IsRolling

    Args:
        prices: 날짜 인덱스, adj_close 값 (결측치 제거 완료)

    Returns:
        {'CAGR': float, 'Vol': float, 'Sortino': float|None, 'IsRolling': bool}
    """
    prices = prices.sort_index().dropna()
    n = len(prices)

    if n < MIN_DAYS:
        return {'CAGR': 0.0, 'Vol': 0.0, 'Sortino': None, 'IsRolling': False}

    # ── 일간 수익률 ────────────────────────────────────────────────────
    daily_ret = prices.pct_change().dropna()

    # ── CAGR ──────────────────────────────────────────────────────────
    total_return = prices.iloc[-1] / prices.iloc[0]
    years = (n - 1) / TRADING_DAYS
    cagr = total_return ** (1 / years) - 1  # 소수 (예: 0.085 = 8.5%)

    # ── 연율화 변동성 ──────────────────────────────────────────────────
    vol = float(daily_ret.std() * math.sqrt(TRADING_DAYS))  # 소수

    # ── Sortino (MAR = 4%) ────────────────────────────────────────────
    # 원본 Sortino & van der Meer (1991) 공식:
    #   DD = sqrt( mean( min(r_i − MAR_daily, 0)² ) ) × √252
    #
    # 핵심: 분모는 전체 N일 기준 RMS — 하방일이 적을수록 분모가 작아지는
    # std(하방일만) 방식과 달리, 비하방일의 0² 기여가 분모를 희석하여
    # 하방 노출이 낮은 ETF를 올바르게 보상한다.
    shortfalls = np.minimum(daily_ret.values - MAR_DAILY, 0.0)  # 전체 N일
    rms_shortfall = float(np.sqrt(np.mean(shortfalls ** 2)))    # RMS over N
    sortino = None

    if rms_shortfall > MIN_DD_FLOOR:
        dd = rms_shortfall * math.sqrt(TRADING_DAYS)  # 연율화
        # 분자: CAGR − MAR (둘 다 소수 기준)
        sortino = (cagr - MAR_ANNUAL) / dd

    is_rolling = n >= MIN_ROLLING_DAYS

    return {
        'CAGR':      round(cagr * 100, 1),   # 퍼센트 표시 (8.5)
        'Vol':       round(vol  * 100, 1),   # 퍼센트 표시 (16.3)
        'Sortino':   round(sortino, 2) if sortino is not None else None,
        'IsRolling': is_rolling,
    }


# ══════════════════════════════════════════════════════════════════════
# Supabase 데이터 로딩
# ══════════════════════════════════════════════════════════════════════

def fetch_prices_batch(client, tickers: list[str]) -> dict[str, pd.Series]:
    """
    Supabase etf_prices 에서 특정 티커 목록의 adj_close 전체 히스토리 조회.
    Supabase REST API 최대 행 수 제한을 페이지네이션으로 우회.
    """
    result: dict[str, list] = {t: [] for t in tickers}
    ticker_filter = ','.join(f'"{t}"' for t in tickers)  # "VOO","SPY",...

    offset = 0
    while True:
        resp = (
            client.table('etf_prices')
            .select('ticker,date,adj_close')
            .in_('ticker', tickers)
            .order('date')
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        rows = resp.data
        if not rows:
            break
        for row in rows:
            tk = row['ticker']
            if tk in result:
                result[tk].append((row['date'], row['adj_close']))
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    series_map: dict[str, pd.Series] = {}
    for tk, records in result.items():
        if not records:
            continue
        dates, prices = zip(*records)
        s = pd.Series(
            data=list(prices),
            index=pd.to_datetime(list(dates)),
            name=tk,
            dtype=float,
        ).dropna()
        if len(s) >= MIN_DAYS:
            series_map[tk] = s

    return series_map


# ══════════════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════════════

def load_all_tickers() -> list[str]:
    """etf_data.json 에서 전체 티커 목록 추출 (없으면 etf_database.json)."""
    if os.path.exists(ETF_DATA_JSON):
        with open(ETF_DATA_JSON, encoding='utf-8') as f:
            data = json.load(f)
        tickers = set()
        for etfs in data.get('allData', {}).values():
            for etf in etfs:
                tickers.add(etf['ticker'])
        return sorted(tickers)

    if os.path.exists(ETF_DATABASE_JSON):
        with open(ETF_DATABASE_JSON, encoding='utf-8') as f:
            db = json.load(f)
        return sorted({e['ticker'] for e in db})

    raise FileNotFoundError('etf_data.json / etf_database.json 를 찾을 수 없습니다.')


def main():
    t0 = time.time()

    # ── 환경변수 ────────────────────────────────────────────────────
    url = os.environ.get('SUPABASE_URL', '')
    key = os.environ.get('SUPABASE_SERVICE_KEY', '')
    if not url or not key:
        log.error('환경변수 SUPABASE_URL, SUPABASE_SERVICE_KEY 를 설정하세요.')
        sys.exit(1)

    client = create_client(url, key)
    log.info(f'MAR = {MAR_ANNUAL*100:.1f}%/yr  |  MIN_ROLLING_DAYS = {MIN_ROLLING_DAYS}')

    # ── 티커 목록 ────────────────────────────────────────────────────
    all_tickers = load_all_tickers()
    log.info(f'총 {len(all_tickers)}개 티커 대상')

    # ── 배치별 가격 조회 + 지표 계산 ──────────────────────────────────
    perf_stats: dict[str, dict] = {}
    n_batches = math.ceil(len(all_tickers) / BATCH_SIZE)

    for i in range(n_batches):
        batch = all_tickers[i * BATCH_SIZE:(i + 1) * BATCH_SIZE]
        try:
            price_map = fetch_prices_batch(client, batch)
        except Exception as e:
            log.warning(f'배치 {i+1}/{n_batches} Supabase 오류: {e}')
            price_map = {}

        for tk in batch:
            if tk in price_map:
                perf_stats[tk] = compute_metrics(price_map[tk])
            else:
                # 가격 데이터 없는 경우 빈 레코드
                perf_stats[tk] = {
                    'CAGR': 0.0, 'Vol': 0.0,
                    'Sortino': None, 'IsRolling': False,
                }

        if (i + 1) % 10 == 0 or i == n_batches - 1:
            log.info(f'진행: {i+1}/{n_batches} 배치  |  계산 완료: {len(perf_stats)}개')

    # ── Sortino 통계 출력 ─────────────────────────────────────────────
    sortinos = [v['Sortino'] for v in perf_stats.values() if v['Sortino'] is not None]
    rolling_count = sum(1 for v in perf_stats.values() if v['IsRolling'])
    log.info(
        f'Sortino 유효: {len(sortinos)}/{len(perf_stats)} | '
        f'IsRolling: {rolling_count} | '
        f'중앙값: {float(np.median(sortinos)):.2f} | '
        f'최대: {max(sortinos):.2f} | '
        f'최소: {min(sortinos):.2f}'
    )

    # ── etf_perf_stats.pkl 저장 ──────────────────────────────────────
    os.makedirs(DATA_PROCESSED, exist_ok=True)
    with open(PERF_STATS_PKL, 'wb') as f:
        pickle.dump(perf_stats, f)
    log.info(f'저장: {PERF_STATS_PKL}')

    # ── etf_database.json 갱신 ───────────────────────────────────────
    if os.path.exists(ETF_DATABASE_JSON):
        with open(ETF_DATABASE_JSON, encoding='utf-8') as f:
            db = json.load(f)

        updated = 0
        for etf in db:
            tk = etf['ticker']
            p = perf_stats.get(tk, {})
            if p.get('Sortino') is not None:
                etf['ret']        = p['CAGR']
                etf['vol']        = p['Vol']
                etf['sor']        = p['Sortino']
                etf['is_rolling'] = p['IsRolling']
                updated += 1

        with open(ETF_DATABASE_JSON, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, separators=(',', ':'))
        log.info(f'etf_database.json 갱신: {updated}/{len(db)}개 ETF')

    elapsed = time.time() - t0
    log.info(f'완료! ({elapsed:.0f}초)  → python src/dashboard_builder.py 로 재빌드 필요')


if __name__ == '__main__':
    main()
