#!/usr/bin/env python3
"""
yfinance로 전체 ETF 구성종목(top holdings) 월 1회 수집 스크립트

수집 대상: output/etf_data.json의 전체 티커 (~1,651개)
수집 방법: yfinance Ticker.funds_data.top_holdings
           주식형 ETF만 제공됨 (채권·원자재 ETF는 데이터 없음)
저장 위치: data_scraped/holdings.json
           {"as_of": "YYYY-MM-DD", "data": {"SPY": [["NVDA","NVIDIA Corp",7.32], ...], ...}}

실행 예시:
    python scripts/fetch_holdings.py
"""
import json
import os
import sys
import time
from datetime import datetime

import yfinance as yf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ETF_DATA_PATH = os.path.join(ROOT, 'output', 'etf_data.json')
OUT_PATH      = os.path.join(ROOT, 'data_scraped', 'holdings.json')
CHECKPOINT_PATH = OUT_PATH  # 체크포인트 겸용


def load_tickers():
    with open(ETF_DATA_PATH, encoding='utf-8') as f:
        raw = json.load(f)
    tickers = []
    for etfs in raw.get('allData', raw).values():
        if not isinstance(etfs, list):
            continue
        for etf in etfs:
            t = etf.get('ticker', '').upper().strip()
            if t:
                tickers.append(t)
    return tickers


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    # 체크포인트 로드 (재시작 지원)
    existing = {}
    if os.path.exists(CHECKPOINT_PATH):
        try:
            with open(CHECKPOINT_PATH, encoding='utf-8') as f:
                saved = json.load(f)
            existing = saved.get('data', {})
            print(f'[체크포인트] 기존 {len(existing)}개 로드')
        except Exception:
            pass

    tickers = load_tickers()
    total = len(tickers)
    print(f'대상 ETF: {total}개')

    result = dict(existing)
    fetched = 0
    skipped = 0

    for i, ticker in enumerate(tickers, 1):
        if ticker in result:
            skipped += 1
            continue

        try:
            fd = yf.Ticker(ticker).funds_data
            h = fd.top_holdings if fd else None
            if h is not None and not h.empty:
                holdings = [
                    [str(sym), str(row['Name']), round(float(row['Holding Percent']) * 100, 4)]
                    for sym, row in h.iterrows()
                ]
                result[ticker] = holdings
                fetched += 1
            else:
                result[ticker] = []  # 데이터 없음 표시 (재시도 방지)

        except Exception as e:
            print(f'  [{i}/{total}] {ticker} 오류: {e}')
            result[ticker] = []

        # 50개마다 체크포인트 저장
        if i % 50 == 0:
            _save(result)
            has_data = sum(1 for v in result.values() if v)
            print(f'  [{i}/{total}] 진행 중 — holdings 보유: {has_data}개')

        time.sleep(0.3)  # rate limit 방지

    _save(result)
    has_data = sum(1 for v in result.values() if v)
    print(f'\n완료: {total}개 처리 ({fetched}개 신규, {skipped}개 스킵)')
    print(f'holdings 보유 ETF: {has_data}개 / {len(result)}개')
    print(f'저장: {OUT_PATH}')


def _save(data):
    out = {
        'as_of': datetime.utcnow().strftime('%Y-%m-%d'),
        'data': data,
    }
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
