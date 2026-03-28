"""build_corr_data.py — 월간 수익률 데이터 생성

raw/prices_close.parquet → output/corr_returns.json

correlation.html이 브라우저에서 직접 Pearson 상관계수를 계산할 수 있도록
최근 5년치 월간 수익률을 컴팩트 JSON으로 출력합니다.

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

LOOKBACK_MONTHS = 60   # 5년
MIN_MONTHS = 36        # 유효 티커 최소 데이터 기간


def build_corr_data():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] corr_returns.json 생성 시작")

    df = pd.read_parquet(PRICES_PARQUET)

    # 월말 종가 → 월간 수익률
    monthly = df.resample('ME').last()
    monthly_ret = monthly.pct_change(fill_method=None)

    # 최근 N개월만
    ret = monthly_ret.tail(LOOKBACK_MONTHS)

    # 유효 데이터 충분한 티커만
    valid = ret.columns[ret.notna().sum() >= MIN_MONTHS]
    ret = ret[valid]

    dates = ret.index.strftime('%Y-%m-%d').tolist()

    # {ticker: [r1, r2, ...]} — null 포함, round(5)
    tickers_data = {}
    for col in ret.columns:
        vals = [round(v, 5) if pd.notna(v) else None for v in ret[col]]
        tickers_data[col] = vals

    out = {
        'as_of': df.index[-1].strftime('%Y-%m-%d'),
        'dates': dates,
        'returns': tickers_data,
    }

    os.makedirs(OUT_PATH.parent, exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, separators=(',', ':'))

    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 완료: {len(valid)}개 티커 × {len(dates)}개월 → {size_kb:.0f} KB")
    return len(valid)


def main():
    n = build_corr_data()
    return n


if __name__ == '__main__':
    n = main()
    sys.exit(0 if n > 0 else 1)
