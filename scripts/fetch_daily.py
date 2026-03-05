#!/usr/bin/env python3
"""
ETF 가격 데이터 일별 증분 업데이트

용도:
    매일 미국 장 종료 후 (UTC 22:00) GitHub Actions에서 자동 실행.
    최근 7거래일 수정종가를 raw/prices_close.parquet에 추가(upsert).
    AUM 등 메타 데이터도 갱신.
    workflow 실패로 며칠 건너뛰어도 7일 범위로 갭 없이 복구.

실행 방법:
    python scripts/fetch_daily.py

선행 조건:
    raw/prices_close.parquet, raw/meta.parquet 존재 (fetch_initial.py 선행 실행)
"""

import logging
import math
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

# ── 경로 ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
RAW_DIR        = ROOT / 'raw'
PRICES_PARQUET = RAW_DIR / 'prices_close.parquet'
META_PARQUET   = RAW_DIR / 'meta.parquet'

# ── 파라미터 ─────────────────────────────────────────────────────────
BATCH_YF     = 50
SLEEP_YF     = 0.5
FETCH_PERIOD = '7d'   # 7일 범위 → 며칠 건너뛰어도 자동 복구

# ── 로깅 ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-7s %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# 가격 업데이트
# ════════════════════════════════════════════════════════════════════

def update_prices(tickers: list[str]) -> int:
    """최근 7일 수정종가 다운로드 → parquet에 upsert

    Returns:
        업데이트된 새 행 수
    """
    df_existing = pd.read_parquet(PRICES_PARQUET)
    last_date   = df_existing.index.max()
    log.info(f'기존 마지막 날짜: {last_date.date()}  |  티커: {len(tickers)}개')

    new_frames: dict[str, pd.Series] = {}
    total_batches = math.ceil(len(tickers) / BATCH_YF)

    for i in range(total_batches):
        batch = tickers[i * BATCH_YF:(i + 1) * BATCH_YF]

        try:
            raw = yf.download(
                batch,
                period=FETCH_PERIOD,
                auto_adjust=True,
                progress=False,
                threads=True,
            )
        except Exception as e:
            log.warning(f'배치 {i+1} 다운로드 실패: {e}')
            time.sleep(SLEEP_YF * 4)
            continue

        if raw is None or raw.empty:
            continue

        if len(batch) == 1:
            close = raw.get('Close')
            if close is not None and not close.empty:
                new_frames[batch[0]] = close.squeeze()
        else:
            try:
                close_df = raw['Close']
            except Exception:
                continue
            for ticker in batch:
                if ticker in close_df.columns:
                    s = close_df[ticker].dropna()
                    if not s.empty:
                        new_frames[ticker] = s

        if (i + 1) % 10 == 0 or i == total_batches - 1:
            log.info(f'  배치: {i+1}/{total_batches}')

        if i < total_batches - 1:
            time.sleep(SLEEP_YF)

    if not new_frames:
        log.warning('새 가격 데이터 없음')
        return 0

    df_new = pd.DataFrame(new_frames)
    df_new.index = pd.to_datetime(df_new.index)
    df_new.index.name = 'date'

    # last_date 이후 행만 추가 (이미 있는 날짜는 갱신)
    df_new = df_new[df_new.index > last_date]

    if df_new.empty:
        log.info('새로운 거래일 없음 (이미 최신)')
        return 0

    # 기존 + 신규 병합 후 저장
    df_merged = pd.concat([df_existing, df_new], axis=0).sort_index()
    # 중복 인덱스 제거 (keep='last'로 최신값 우선)
    df_merged = df_merged[~df_merged.index.duplicated(keep='last')]
    df_merged.to_parquet(PRICES_PARQUET, compression='snappy')

    new_rows = len(df_new) * df_new.shape[1]
    log.info(f'가격 업데이트: +{len(df_new)}거래일  ({new_rows:,}개 셀)')
    log.info(f'  총 기간: {df_merged.index.min().date()} ~ {df_merged.index.max().date()}')
    return new_rows


# ════════════════════════════════════════════════════════════════════
# 메타 업데이트 (AUM 중심)
# ════════════════════════════════════════════════════════════════════

def _safe(v, default=None):
    try:
        f = float(v)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


def update_meta(tickers: list[str]) -> None:
    """AUM, 수수료, 배당수익률 갱신 (종목명·상장일은 변하지 않으므로 기존값 유지)"""
    df_meta = pd.read_parquet(META_PARQUET)
    updated = 0

    for idx, ticker in enumerate(tickers):
        try:
            info = yf.Ticker(ticker).info
        except Exception:
            continue

        aum = _safe(info.get('totalAssets'), 0)
        exp = _safe(info.get('annualReportExpenseRatio')) or _safe(info.get('totalExpenseRatio'))
        div = _safe(info.get('dividendYield')) or _safe(info.get('trailingAnnualDividendYield'))

        if ticker in df_meta.index:
            df_meta.loc[ticker, 'market_cap'] = aum
            if exp is not None:
                df_meta.loc[ticker, 'expense_ratio'] = exp
            if div is not None:
                df_meta.loc[ticker, 'div_yield'] = div
        else:
            # 신규 티커 (etf_database.json에 추가된 경우)
            name = info.get('longName') or info.get('shortName') or ticker
            inception = '1900-01-01'
            ts = info.get('fundInceptionDate')
            if ts:
                try:
                    inception = pd.Timestamp(ts, unit='s').strftime('%Y-%m-%d')
                except Exception:
                    pass
            df_meta.loc[ticker] = {
                'fullname': name, 'market_cap': aum,
                'expense_ratio': exp, 'div_yield': div,
                'inception_date': inception,
            }
            log.info(f'  신규 티커 추가: {ticker}')

        updated += 1
        if (idx + 1) % 200 == 0:
            log.info(f'  메타 업데이트: {idx+1}/{len(tickers)}')
        time.sleep(0.05)

    # AUM 기반 순위 재계산
    df_meta['rank'] = (
        df_meta['market_cap']
        .rank(ascending=False, method='min')
        .fillna(9999)
        .astype(int)
    )
    df_meta.to_parquet(META_PARQUET, compression='snappy')
    log.info(f'메타 업데이트 완료: {updated}개 티커')


# ════════════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════════════

def main():
    if not PRICES_PARQUET.exists() or not META_PARQUET.exists():
        log.error(
            'raw/ 파일이 없습니다. 먼저 fetch_initial.py를 실행하세요.\n'
            '  python scripts/fetch_initial.py'
        )
        sys.exit(1)

    df_existing = pd.read_parquet(PRICES_PARQUET)
    tickers = sorted(df_existing.columns.tolist())
    log.info(f'업데이트 대상: {len(tickers)}개 ETF')

    log.info('\n=== [1/2] 가격 업데이트 ===')
    update_prices(tickers)

    log.info('\n=== [2/2] 메타 업데이트 (AUM·수수료·배당) ===')
    update_meta(tickers)

    log.info('\n=== 일별 업데이트 완료 ===')
    log.info('다음 단계: python scripts/compute_all.py')


if __name__ == '__main__':
    main()
