#!/usr/bin/env python3
"""
ETF 원본 데이터 초기 다운로드 (최초 1회 실행)

용도:
    raw/prices_close.parquet — 1651개 ETF 수정종가 (adj_close), 최대 기간
    raw/meta.parquet          — AUM, 수수료, 배당수익률, 상장일, 종목명

실행 방법:
    python scripts/fetch_initial.py

주의:
    - 약 1~2시간 소요 (1651개 ETF × 10년 데이터)
    - 이미 raw/ 파일이 존재하면 덮어씀
    - 이후 매일은 fetch_daily.py 사용
"""

import json
import logging
import math
import os
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

# ── 경로 설정 ────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / 'raw'
ETF_DB  = ROOT / 'etf_database.json'

PRICES_PARQUET = RAW_DIR / 'prices_close.parquet'
META_PARQUET   = RAW_DIR / 'meta.parquet'

# ── 튜닝 파라미터 ────────────────────────────────────────────────────
BATCH_YF   = 50      # yfinance 1회 요청 티커 수
SLEEP_YF   = 1.0     # 배치 간 대기 (초)
FETCH_PERIOD = 'max' # 전체 기간 (또는 '10y')

# ── 로깅 ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-7s %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# ETF 목록 로드
# ════════════════════════════════════════════════════════════════════

def load_tickers() -> list[str]:
    """etf_database.json에서 티커 목록 로드"""
    with open(ETF_DB, encoding='utf-8') as f:
        db = json.load(f)

    # allData 하위의 모든 ETF 티커 수집
    tickers: set[str] = set()
    if isinstance(db, dict):
        for section in db.values():
            if isinstance(section, list):
                for item in section:
                    t = item.get('ticker') if isinstance(item, dict) else None
                    if t:
                        tickers.add(str(t))
            elif isinstance(section, dict):
                for sub in section.values():
                    if isinstance(sub, list):
                        for item in sub:
                            t = item.get('ticker') if isinstance(item, dict) else None
                            if t:
                                tickers.add(str(t))

    # 대안: 상위 레벨에 ticker 키가 있는 경우
    if not tickers and isinstance(db, list):
        for item in db:
            t = item.get('ticker') if isinstance(item, dict) else None
            if t:
                tickers.add(str(t))

    result = sorted(tickers)
    log.info(f'ETF 목록 로드: {len(result)}개')
    return result


# ════════════════════════════════════════════════════════════════════
# 가격 다운로드
# ════════════════════════════════════════════════════════════════════

def download_prices(tickers: list[str]) -> pd.DataFrame:
    """전체 ETF 수정종가 다운로드 → wide DataFrame (DatetimeIndex × ticker)"""
    all_frames: dict[str, pd.Series] = {}
    total_batches = math.ceil(len(tickers) / BATCH_YF)

    for i in range(total_batches):
        batch = tickers[i * BATCH_YF:(i + 1) * BATCH_YF]

        try:
            raw = yf.download(
                batch,
                period=FETCH_PERIOD,
                auto_adjust=True,   # 수정종가 (배당·분할 반영)
                progress=False,
                threads=True,
            )
        except Exception as e:
            log.warning(f'배치 {i+1}/{total_batches} 다운로드 실패: {e}')
            time.sleep(SLEEP_YF * 4)
            continue

        if raw is None or raw.empty:
            continue

        # yfinance >= 0.2: MultiIndex(field, ticker) 또는 단일 ticker일 때 단순 DataFrame
        if len(batch) == 1:
            close = raw.get('Close')
            if close is not None and not close.empty:
                all_frames[batch[0]] = close.squeeze()
        else:
            try:
                close_df = raw['Close'] if 'Close' in raw.columns.get_level_values(0) else None
            except Exception:
                close_df = None

            if close_df is None:
                continue

            for ticker in batch:
                if ticker in close_df.columns:
                    s = close_df[ticker].dropna()
                    if not s.empty:
                        all_frames[ticker] = s

        if (i + 1) % 10 == 0 or i == total_batches - 1:
            log.info(f'가격 배치: {i+1}/{total_batches}  |  수집 {len(all_frames)}개')

        if i < total_batches - 1:
            time.sleep(SLEEP_YF)

    if not all_frames:
        raise RuntimeError('가격 데이터를 하나도 수집하지 못했습니다.')

    df = pd.DataFrame(all_frames)
    df.index = pd.to_datetime(df.index)
    df.index.name = 'date'
    df = df.sort_index()
    log.info(f'가격 DataFrame: {df.shape[1]} ETF × {df.shape[0]} 거래일')
    return df


# ════════════════════════════════════════════════════════════════════
# 메타 데이터 수집
# ════════════════════════════════════════════════════════════════════

def _safe(v, default=None):
    try:
        f = float(v)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


def fetch_meta(tickers: list[str]) -> pd.DataFrame:
    """yfinance .info로 메타 수집 (AUM, 수수료, 배당, 상장일, 종목명)"""
    records = []
    total = len(tickers)

    for idx, ticker in enumerate(tickers):
        try:
            info = yf.Ticker(ticker).info
        except Exception as e:
            log.debug(f'  {ticker}: info 실패 — {e}')
            info = {}

        # AUM
        aum = _safe(info.get('totalAssets'), 0)

        # 수수료 (소수 형식, 예: 0.0003)
        exp = _safe(info.get('annualReportExpenseRatio')) or _safe(info.get('totalExpenseRatio'))

        # 배당수익률 (소수 형식, 예: 0.0275)
        div = _safe(info.get('dividendYield')) or _safe(info.get('trailingAnnualDividendYield'))

        # 상장일 (Unix timestamp → YYYY-MM-DD)
        inception = '1900-01-01'
        ts = info.get('fundInceptionDate')
        if ts:
            try:
                inception = pd.Timestamp(ts, unit='s').strftime('%Y-%m-%d')
            except Exception:
                pass

        # 종목명
        name = info.get('longName') or info.get('shortName') or ticker

        records.append({
            'ticker':        ticker,
            'fullname':      str(name),
            'market_cap':    aum,
            'expense_ratio': exp,
            'div_yield':     div,
            'inception_date': inception,
        })

        if (idx + 1) % 100 == 0 or idx == total - 1:
            log.info(f'메타 수집: {idx+1}/{total}')

        time.sleep(0.1)  # rate limit 방지

    df = pd.DataFrame(records).set_index('ticker')

    # AUM 기반 순위 계산 (1 = 최대)
    df['rank'] = df['market_cap'].rank(ascending=False, method='min').fillna(9999).astype(int)

    return df


# ════════════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════════════

def main():
    RAW_DIR.mkdir(exist_ok=True)
    log.info(f'저장 경로: {RAW_DIR}')

    tickers = load_tickers()
    if not tickers:
        log.error('ETF 목록이 비어 있습니다. etf_database.json을 확인하세요.')
        sys.exit(1)

    # 1. 가격 다운로드
    log.info(f'\n=== [1/2] 수정종가 다운로드 (period={FETCH_PERIOD}) ===')
    df_prices = download_prices(tickers)
    df_prices.to_parquet(PRICES_PARQUET, compression='snappy')
    log.info(f'저장: {PRICES_PARQUET}  ({PRICES_PARQUET.stat().st_size / 1e6:.1f} MB)')

    # 2. 메타 데이터 수집
    log.info(f'\n=== [2/2] 메타 데이터 수집 ===')
    df_meta = fetch_meta(tickers)
    df_meta.to_parquet(META_PARQUET, compression='snappy')
    log.info(f'저장: {META_PARQUET}  ({META_PARQUET.stat().st_size / 1e6:.1f} MB)')

    log.info('\n=== 초기 다운로드 완료 ===')
    log.info(f'  가격: {df_prices.shape[1]} ETF × {df_prices.shape[0]} 거래일')
    log.info(f'  메타: {len(df_meta)} ETF')
    log.info(f'\n다음 단계: python scripts/compute_all.py')


if __name__ == '__main__':
    main()
