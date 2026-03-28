#!/usr/bin/env python3
"""
백테스트용 연도별 실제 수익률 데이터 생성
raw/prices_close.parquet → output/backtest_data.json

출력 형식:
  { "SPY": {"2005": 0.0490, "2006": 0.1561, ...}, ... }

- 연말 마지막 거래일 종가 기준 연도별 수익률
- 상장 첫 해(수익률 계산 불가한 연도)는 제외
- 마지막 연도: 데이터에 존재하는 가장 최근 완전한 연도 (당해 연도 미포함)
"""
import json
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent


def build_backtest_data():
    df = pd.read_parquet(ROOT / 'raw' / 'prices_close.parquet')
    df.index = pd.to_datetime(df.index)

    # 현재 연도는 미완성 → 직전 연도까지만 포함
    current_year = pd.Timestamp.now().year
    df = df[df.index.year < current_year]

    # 연말 마지막 거래일 종가
    yearly = df.resample('YE').last()

    # 연도별 수익률 (전년도 말 → 당해 연도 말)
    annual_ret = yearly.pct_change()

    result = {}
    for ticker in annual_ret.columns:
        series = annual_ret[ticker].dropna()
        if series.empty:
            continue
        returns = {
            str(dt.year): round(float(ret), 6)
            for dt, ret in series.items()
            if pd.notna(ret)
        }
        if returns:
            result[ticker] = returns

    out_path = ROOT / 'output' / 'backtest_data.json'
    with open(out_path, 'w') as f:
        json.dump(result, f, separators=(',', ':'))

    size_kb = out_path.stat().st_size // 1024
    print(f'✅ backtest_data.json: {len(result)}개 티커, {size_kb}KB → {out_path}')
    return len(result)


def main():
    return build_backtest_data()


if __name__ == '__main__':
    main()
