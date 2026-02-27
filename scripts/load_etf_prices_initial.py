#!/usr/bin/env python3
"""
ETF 가격 데이터 초기 적재 스크립트 (최초 1회 실행)

용도:
    output/etf_data.json의 전체 ETF 티커에 대해
    yfinance로 max 히스토리를 다운받아 Supabase etf_prices 테이블에 적재.

특징:
    - etf_prices_log 테이블로 진행 상태 추적 → 중단 후 재실행해도 이어서 처리
    - 50 티커 단위로 yfinance 배치 다운로드
    - 500 행 단위로 Supabase upsert
    - 실패한 티커는 개별 재시도

실행 방법:
    SUPABASE_URL=https://xxx.supabase.co \\
    SUPABASE_SERVICE_KEY=eyJ... \\
    python scripts/load_etf_prices_initial.py
"""

import os
import sys
import json
import time
import math
import logging
from datetime import datetime

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
SUPABASE_URL        = os.environ.get('SUPABASE_URL', '')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    log.error('환경변수 SUPABASE_URL, SUPABASE_SERVICE_KEY 를 설정하세요.')
    sys.exit(1)

# ── 튜닝 파라미터 ─────────────────────────────────────────────────────
BATCH_YF  = 50    # yfinance 1회 요청 티커 수
BATCH_DB  = 500   # Supabase 1회 upsert 행 수
SLEEP_YF  = 1.0   # yfinance 배치 간 대기(초) — Yahoo 과부하 방지


# ══════════════════════════════════════════════════════════════════════
# 유틸리티
# ══════════════════════════════════════════════════════════════════════

def _safe_float(v):
    """None / NaN / Inf → None, 그 외 float"""
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _safe_int(v):
    """None / NaN → 0, 그 외 int"""
    try:
        f = float(v)
        return 0 if (math.isnan(f) or math.isinf(f)) else int(f)
    except (TypeError, ValueError):
        return 0


def _col(df: pd.DataFrame, *names: str):
    """대소문자/공백 무관하게 컬럼명 찾기"""
    for name in names:
        normalized = name.lower().replace(' ', '_')
        for col in df.columns:
            if col.lower().replace(' ', '_') == normalized:
                return col
    return None


def df_to_rows(ticker: str, df: pd.DataFrame) -> list[dict]:
    """DataFrame → Supabase upsert용 딕셔너리 리스트"""
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

        # 날짜 추출 (timezone-aware도 대응)
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

def download_batch(tickers: list[str]) -> dict[str, pd.DataFrame]:
    """
    여러 티커를 yfinance로 일괄 다운로드.
    반환: {ticker: DataFrame(OHLCV + Adj Close)}
    """
    if not tickers:
        return {}

    raw = yf.download(
        tickers,
        period='max',
        auto_adjust=False,
        progress=False,
        threads=True,
    )

    if raw is None or raw.empty:
        return {}

    result = {}

    # 단일 티커는 MultiIndex 없이 평탄한 컬럼 반환
    if len(tickers) == 1:
        if _col(raw, 'Close') is not None:
            df = raw.dropna(subset=[_col(raw, 'Close')])
            if not df.empty:
                result[tickers[0]] = df
        return result

    # 다중 티커: MultiIndex (price_type, ticker) — xs로 per-ticker 추출
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

def get_loaded_tickers(client) -> set[str]:
    """etf_prices_log에서 이미 완료된 티커 목록 반환"""
    res = client.table('etf_prices_log').select('ticker').execute()
    return {row['ticker'] for row in (res.data or [])}


def upsert_prices(client, rows: list[dict]):
    """500행 단위 Supabase upsert"""
    for i in range(0, len(rows), BATCH_DB):
        chunk = rows[i:i + BATCH_DB]
        client.table('etf_prices').upsert(
            chunk, on_conflict='ticker,date'
        ).execute()


def mark_loaded(client, ticker: str, row_count: int):
    """etf_prices_log에 완료 기록"""
    client.table('etf_prices_log').upsert({
        'ticker':    ticker,
        'loaded_at': datetime.utcnow().isoformat(),
        'row_count': row_count,
    }, on_conflict='ticker').execute()


# ══════════════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════════════

def load_all_tickers() -> list[str]:
    """etf_data.json에서 전체 ETF 티커 추출"""
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
    log.info(f'전체 티커: {len(all_tickers)}개')

    # 이미 완료된 티커 스킵 (재실행 안전)
    loaded = get_loaded_tickers(client)
    pending = [t for t in all_tickers if t not in loaded]
    log.info(f'완료: {len(loaded)}개  |  대기: {len(pending)}개')

    if not pending:
        log.info('모든 티커 이미 적재 완료.')
        return

    total_batches = math.ceil(len(pending) / BATCH_YF)
    total_rows = 0
    failed_tickers = []

    for batch_idx in range(total_batches):
        batch = pending[batch_idx * BATCH_YF:(batch_idx + 1) * BATCH_YF]
        log.info(f'배치 {batch_idx + 1}/{total_batches}  [{batch[0]} … {batch[-1]}]')

        # yfinance 배치 다운로드
        try:
            ticker_dfs = download_batch(batch)
        except Exception as e:
            log.warning(f'  배치 다운로드 실패: {e}  → 개별 재시도')
            ticker_dfs = {}
            for t in batch:
                try:
                    ticker_dfs.update(download_batch([t]))
                except Exception as e2:
                    log.warning(f'    {t} 실패: {e2}')
                    failed_tickers.append(t)

        # Supabase 적재
        for ticker, df in ticker_dfs.items():
            rows = df_to_rows(ticker, df)
            if not rows:
                log.warning(f'  {ticker}: 유효 행 없음')
                continue
            try:
                upsert_prices(client, rows)
                mark_loaded(client, ticker, len(rows))
                total_rows += len(rows)
            except Exception as e:
                log.error(f'  {ticker} Supabase 오류: {e}')
                failed_tickers.append(ticker)

        # 다운로드 불가 티커 (데이터 없음) → 로그만 남기고 완료 처리
        for t in batch:
            if t not in ticker_dfs and t not in failed_tickers:
                log.warning(f'  {t}: yfinance 데이터 없음 (상폐 등)')
                mark_loaded(client, t, 0)

        if batch_idx < total_batches - 1:
            time.sleep(SLEEP_YF)

    log.info(f'적재 완료 — 총 {total_rows:,}행')
    if failed_tickers:
        log.warning(f'실패 티커 ({len(failed_tickers)}개): {failed_tickers}')
        log.warning('재실행하면 실패 티커만 재처리됩니다.')


if __name__ == '__main__':
    main()
