#!/usr/bin/env python3
"""
ETF 가격 데이터 일별 증분 업데이트 스크립트

용도:
    GitHub Actions cron으로 평일마다 자동 실행.
    최근 7거래일 데이터를 전체 티커 대상으로 다운받아 Supabase에 upsert.
    PRIMARY KEY (ticker, date) 덕분에 이미 있는 행은 자동 업데이트.
    7일 범위로 다운받아 workflow 실패로 며칠 건너뛰어도 갭 없이 복구.

실행 방법:
    SUPABASE_URL=https://xxx.supabase.co \\
    SUPABASE_SERVICE_KEY=eyJ... \\
    python scripts/update_etf_prices_daily.py
"""

import os
import sys
import json
import time
import math
import logging

import pandas as pd
import yfinance as yf
from supabase import create_client

# ── 로깅 설정 ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-7s %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)

# ── 환경변수 ──────────────────────────────────────────────────────────
SUPABASE_URL         = os.environ.get('SUPABASE_URL', '')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    log.error('환경변수 SUPABASE_URL, SUPABASE_SERVICE_KEY 를 설정하세요.')
    sys.exit(1)

# ── 튜닝 파라미터 ─────────────────────────────────────────────────────
BATCH_YF  = 50    # yfinance 1회 요청 티커 수
BATCH_DB  = 500   # Supabase 1회 upsert 행 수
SLEEP_YF  = 0.5   # yfinance 배치 간 대기(초)
FETCH_PERIOD = '7d'  # 매번 최근 7일치 fetch → 갭 발생 시 자동 복구


# ══════════════════════════════════════════════════════════════════════
# 유틸리티 (load_etf_prices_initial.py 와 동일)
# ══════════════════════════════════════════════════════════════════════

def _safe_float(v):
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _safe_int(v):
    try:
        f = float(v)
        return 0 if (math.isnan(f) or math.isinf(f)) else int(f)
    except (TypeError, ValueError):
        return 0


def _col(df: pd.DataFrame, *names: str):
    for name in names:
        normalized = name.lower().replace(' ', '_')
        for col in df.columns:
            if col.lower().replace(' ', '_') == normalized:
                return col
    return None


def df_to_rows(ticker: str, df: pd.DataFrame) -> list[dict]:
    close_col  = _col(df, 'Close')
    adj_col    = _col(df, 'Adj Close', 'Adj_Close', 'AdjClose')
    open_col   = _col(df, 'Open')
    high_col   = _col(df, 'High')
    low_col    = _col(df, 'Low')
    volume_col = _col(df, 'Volume')

    if close_col is None:
        return []

    rows = []
    for idx, row in df.iterrows():
        close = _safe_float(row.get(close_col))
        if close is None:
            continue

        adj = _safe_float(row.get(adj_col)) if adj_col else None

        if hasattr(idx, 'date'):
            d = idx.date().isoformat()
        else:
            d = str(idx)[:10]

        rows.append({
            'ticker':    ticker,
            'date':      d,
            'open':      _safe_float(row.get(open_col))   if open_col   else None,
            'high':      _safe_float(row.get(high_col))   if high_col   else None,
            'low':       _safe_float(row.get(low_col))    if low_col    else None,
            'close':     close,
            'volume':    _safe_int(row.get(volume_col))   if volume_col else 0,
            'adj_close': adj if adj is not None else close,
        })
    return rows


# ══════════════════════════════════════════════════════════════════════
# yfinance 다운로드
# ══════════════════════════════════════════════════════════════════════

def download_batch(tickers: list[str], period: str = FETCH_PERIOD) -> dict[str, pd.DataFrame]:
    if not tickers:
        return {}

    raw = yf.download(
        tickers,
        period=period,
        auto_adjust=False,
        progress=False,
        threads=True,
    )

    if raw is None or raw.empty:
        return {}

    result = {}

    if len(tickers) == 1:
        if _col(raw, 'Close') is not None:
            df = raw.dropna(subset=[_col(raw, 'Close')])
            if not df.empty:
                result[tickers[0]] = df
        return result

    for ticker in tickers:
        try:
            df = raw.xs(ticker, axis=1, level=1)
            close_col = _col(df, 'Close')
            if close_col:
                df = df.dropna(subset=[close_col])
                if not df.empty:
                    result[ticker] = df
        except (KeyError, Exception):
            continue

    return result


# ══════════════════════════════════════════════════════════════════════
# Supabase 연동
# ══════════════════════════════════════════════════════════════════════

def upsert_prices(client, rows: list[dict]):
    for i in range(0, len(rows), BATCH_DB):
        chunk = rows[i:i + BATCH_DB]
        client.table('etf_prices').upsert(
            chunk, on_conflict='ticker,date'
        ).execute()


# ══════════════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════════════

def load_all_tickers() -> list[str]:
    json_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'etf_data.json')
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    tickers = set()
    for etfs in data.get('allData', {}).values():
        for etf in etfs:
            tickers.add(etf['ticker'])
    return sorted(tickers)


def main():
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    all_tickers = load_all_tickers()
    log.info(f'업데이트 대상: {len(all_tickers)}개 티커  |  기간: 최근 {FETCH_PERIOD}')

    total_batches = math.ceil(len(all_tickers) / BATCH_YF)
    total_rows = 0

    for batch_idx in range(total_batches):
        batch = all_tickers[batch_idx * BATCH_YF:(batch_idx + 1) * BATCH_YF]

        try:
            ticker_dfs = download_batch(batch)
        except Exception as e:
            log.warning(f'배치 {batch_idx + 1} 다운로드 실패: {e}')
            ticker_dfs = {}

        all_rows = []
        for ticker, df in ticker_dfs.items():
            all_rows.extend(df_to_rows(ticker, df))

        if all_rows:
            try:
                upsert_prices(client, all_rows)
                total_rows += len(all_rows)
            except Exception as e:
                log.error(f'배치 {batch_idx + 1} Supabase 오류: {e}')

        # 10배치마다 진행률 출력
        if (batch_idx + 1) % 10 == 0 or batch_idx == total_batches - 1:
            log.info(f'진행: {batch_idx + 1}/{total_batches}  |  누적 {total_rows:,}행')

        if batch_idx < total_batches - 1:
            time.sleep(SLEEP_YF)

    log.info(f'일별 업데이트 완료 — 총 {total_rows:,}행 upsert')


if __name__ == '__main__':
    main()
