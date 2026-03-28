"""build_corr_data.py — 전체 이력 월간 수익률 데이터 생성

raw/prices_close.parquet → output/corr_returns.json

포맷: {
  "dates": ["1993-01-31", ...],          // 전체 월 인덱스
  "returns": {
    "SPY": [start_idx, [r0, r1, ...]],   // start_idx부터 연속 슬라이스 (leading null 제거)
    ...
  }
}

Vercel gzip 자동 압축 덕분에 실전 전송 크기 ~550KB.

Usage:
    python3 build_corr_data.py
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
PRICES_PARQUET = ROOT / 'raw' / 'prices_close.parquet'
OUT_PATH = ROOT / 'output' / 'corr_returns.json'

MIN_MONTHS = 12  # 최소 12개월 이상 데이터 있는 티커만


def build_corr_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] corr_returns.json 생성 시작")

    df = pd.read_parquet(PRICES_PARQUET)

    # 월말 종가 → 월간 수익률 (전체 이력)
    monthly = df.resample('ME').last()
    monthly_ret = monthly.pct_change(fill_method=None)

    # 유효 티커 (최소 12개월)
    valid = monthly_ret.columns[monthly_ret.notna().sum() >= MIN_MONTHS]
    ret = monthly_ret[valid]

    dates = ret.index.strftime('%Y-%m-%d').tolist()

    # compact 포맷: [start_idx, [r0, r1, ...]] — leading/trailing null 제거
    tickers_data = {}
    for col in ret.columns:
        s = ret[col]
        non_null = s.notna()
        if not non_null.any():
            continue
        first = non_null.idxmax()
        last = non_null[::-1].idxmax()
        slice_ = s.loc[first:last]
        start_idx = int(ret.index.get_loc(first))
        vals = [round(v, 5) if pd.notna(v) else None for v in slice_]
        tickers_data[col] = [start_idx, vals]

    out = {
        'as_of': df.index[-1].strftime('%Y-%m-%d'),
        'dates': dates,
        'returns': tickers_data,
    }

    os.makedirs(OUT_PATH.parent, exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, separators=(',', ':'))

    size_kb = OUT_PATH.stat().st_size / 1024
    date_range = f"{dates[0]} ~ {dates[-1]}"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 완료: {len(tickers_data)}개 티커 × {len(dates)}개월 ({date_range}) → {size_kb:.0f} KB")
    return len(tickers_data)


def main():
    n = build_corr_data()
    return n


if __name__ == '__main__':
    n = main()
    sys.exit(0 if n > 0 else 1)
