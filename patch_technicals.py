"""patch_technicals.py — RSI(14) 및 52주 레인지 위치(%) 일괄 계산·패치

Yahoo Finance 일간 데이터(1y)로 RSI(14)와 52주 레인지 위치를
계산해 output/etf_data.json 의 rsi·range_52w 컬럼만 업데이트합니다.
전체 build 파이프라인 없이 단독 실행 가능.

Usage:
    python patch_technicals.py
"""
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'src'))
from metrics import compute_rsi, compute_52w_range_pct

# ── 설정 ──────────────────────────────────────────────
MAX_WORKERS   = 16
RETRY_MAX     = 3
ETF_DATA_JSON = os.path.join(ROOT, 'output', 'etf_data.json')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}

_lock = threading.Lock()


def safe_print(msg):
    with _lock:
        print(msg, flush=True)


def fetch_daily(session, ticker):
    """Yahoo Finance에서 1년 일간 수정종가 Series 반환. 실패 시 None."""
    url = (
        f'https://query2.finance.yahoo.com/v8/finance/chart/{ticker}'
        f'?range=1y&interval=1d&includeAdjustedClose=true'
    )
    for attempt in range(RETRY_MAX):
        try:
            r = session.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            if r.status_code != 200:
                return None
            data = r.json()
            result = data.get('chart', {}).get('result')
            if not result:
                return None
            ts         = result[0]['timestamp']
            indicators = result[0].get('indicators', {})
            adj        = indicators.get('adjclose', [{}])
            prices     = (adj[0].get('adjclose') if adj else None) or \
                         indicators.get('quote', [{}])[0].get('close', [])
            if not prices:
                return None
            idx = pd.to_datetime(ts, unit='s', utc=True).tz_convert(None)
            s = pd.Series(prices, index=idx, name=ticker, dtype=float).dropna()
            return s if len(s) >= 15 else None
        except Exception:
            time.sleep(1)
    return None


def download_all(tickers):
    results = {}
    done    = 0
    total   = len(tickers)
    session = requests.Session()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_daily, session, tk): tk for tk in tickers}
        for fut in as_completed(futures):
            tk   = futures[fut]
            done += 1
            s    = fut.result()
            if s is not None:
                results[tk] = s
            if done % 200 == 0 or done == total:
                safe_print(f'  {done}/{total}  (성공: {len(results)}개)')

    return results


def main():
    t0 = time.time()

    print('📋 etf_data.json 로드...')
    with open(ETF_DATA_JSON, encoding='utf-8') as f:
        db = json.load(f)

    # 전체 티커 수집
    all_tickers = []
    for etfs in db['allData'].values():
        for etf in etfs:
            all_tickers.append(etf['ticker'])

    print(f'   총 {len(all_tickers)}개 티커')

    print(f'\n📡 Yahoo Finance 일간 데이터 다운로드 ({MAX_WORKERS}스레드)...')
    price_data = download_all(all_tickers)
    print(f'   완료: {len(price_data)}/{len(all_tickers)}개 성공')

    print('\n📊 RSI(14) · 52주 레인지 계산 중...')
    updated = 0
    skipped = 0

    for etfs in db['allData'].values():
        for etf in etfs:
            tk = etf['ticker']
            if tk in price_data:
                s = price_data[tk]
                etf['rsi']       = compute_rsi(s)
                etf['range_52w'] = compute_52w_range_pct(s)
                updated += 1
            else:
                etf.setdefault('rsi', None)
                etf.setdefault('range_52w', None)
                skipped += 1

    print(f'   업데이트: {updated}개 | 스킵: {skipped}개')

    with open(ETF_DATA_JSON, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, separators=(',', ':'))
    print(f'   저장: {ETF_DATA_JSON}')

    print('\n🌐 index.html 재생성...')
    import subprocess
    subprocess.run([sys.executable, os.path.join(ROOT, 'render_html.py')], check=True)

    elapsed = time.time() - t0
    print(f'\n✅ 완료! ({elapsed:.0f}초)')


if __name__ == '__main__':
    main()
