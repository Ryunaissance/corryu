"""patch_r_anchor_qqq.py — 주식 시장 슈퍼섹터 r_anchor를 QQQ 기준으로 패치

Yahoo Finance 월간 데이터로 QQQ 상관계수를 계산해
output/etf_data.json 의 r_anchor 컬럼만 업데이트합니다.
전체 build 파이프라인 없이 단독 실행 가능.

Usage:
    python patch_r_anchor_qqq.py
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
from config import SUPER_SECTOR_DEFS

# ── 설정 ──────────────────────────────────────────────
YEARS        = 5          # 최근 N년 월간 데이터
MIN_MONTHS   = 24         # 상관계수 최소 유효 기간 (개월)
MAX_WORKERS  = 16         # 병렬 다운로드 스레드 수
RETRY_MAX    = 3
ETF_DATA_JSON = os.path.join(ROOT, 'output', 'etf_data.json')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}

_lock = threading.Lock()


def safe_print(msg):
    with _lock:
        print(msg, flush=True)


def fetch_ticker(session, ticker):
    """Yahoo Finance chart API로 월간 수정종가 Series 반환. 실패 시 None."""
    url = (
        f'https://query2.finance.yahoo.com/v8/finance/chart/{ticker}'
        f'?range={YEARS}y&interval=1mo&includeAdjustedClose=true'
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
            if adj and adj[0].get('adjclose'):
                prices = adj[0]['adjclose']
            else:
                prices = indicators.get('quote', [{}])[0].get('close', [])
            if not prices:
                return None
            idx = pd.to_datetime(ts, unit='s', utc=True).tz_convert(None)
            s = pd.Series(prices, index=idx, name=ticker, dtype=float).dropna()
            return s if len(s) >= MIN_MONTHS else None
        except Exception:
            time.sleep(1)
    return None


def download_all(tickers):
    """병렬 다운로드. {ticker: Series} 딕셔너리 반환."""
    results = {}
    done    = 0
    total   = len(tickers)
    session = requests.Session()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_ticker, session, tk): tk for tk in tickers}
        for fut in as_completed(futures):
            tk   = futures[fut]
            done += 1
            s    = fut.result()
            if s is not None:
                results[tk] = s
            if done % 100 == 0 or done == total:
                safe_print(f'  {done}/{total}  (성공: {len(results)}개)')

    return results


def main():
    t0 = time.time()

    # 1. etf_data.json 로드
    print('📋 etf_data.json 로드...')
    with open(ETF_DATA_JSON, encoding='utf-8') as f:
        db = json.load(f)

    # 2. 슈퍼섹터 소속 섹터 및 ETF 티커 수집
    sub_sectors = set()
    for ss_def in SUPER_SECTOR_DEFS.values():
        sub_sectors.update(ss_def['sub_sectors'])

    ss_tickers = []
    for sid in sorted(sub_sectors):
        etfs = db['allData'].get(sid, [])
        for etf in etfs:
            ss_tickers.append(etf['ticker'])

    all_fetch = list(set(['QQQ'] + ss_tickers))
    print(f'   슈퍼섹터 ETF: {len(ss_tickers)}개 + QQQ → 총 {len(all_fetch)}개 다운로드 예정')

    # 3. 월간 데이터 다운로드
    print(f'\n📡 Yahoo Finance 월간 데이터 다운로드 ({MAX_WORKERS}스레드)...')
    price_data = download_all(all_fetch)
    print(f'   완료: {len(price_data)}/{len(all_fetch)}개 성공')

    if 'QQQ' not in price_data:
        print('❌ QQQ 데이터 다운로드 실패. 네트워크 연결을 확인하세요.')
        sys.exit(1)

    # 4. 월간 수익률 → QQQ와의 상관계수 계산
    print('\n📊 QQQ 상관계수 계산 중...')
    df     = pd.DataFrame(price_data)
    df_ret = df.pct_change(fill_method=None)
    corr   = df_ret.corrwith(df_ret['QQQ'], min_periods=MIN_MONTHS)
    valid  = corr.dropna()
    print(f'   유효 티커: {len(valid)}개')

    # 5. etf_data.json r_anchor 패치
    print('\n✏️  r_anchor 패치 중...')
    updated = 0
    skipped = 0
    for sid in sorted(sub_sectors):
        for etf in db['allData'].get(sid, []):
            tk = etf['ticker']
            if tk in corr and not pd.isna(corr[tk]):
                etf['r_anchor'] = round(float(corr[tk]), 4)
                updated += 1
            else:
                skipped += 1

    print(f'   업데이트: {updated}개 | 스킵(데이터 없음): {skipped}개')

    # 6. 저장
    with open(ETF_DATA_JSON, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, separators=(',', ':'))
    print(f'   저장: {ETF_DATA_JSON}')

    # 7. index.html 재생성
    print('\n🌐 index.html 재생성...')
    import subprocess
    render_script = os.path.join(ROOT, 'render_html.py')
    subprocess.run([sys.executable, render_script], check=True)

    elapsed = time.time() - t0
    print(f'\n✅ 완료! ({elapsed:.0f}초)')
    print('\n다음 단계:')
    print('  git add output/etf_data.json output/index.html')
    print("  git commit -m 'feat: r_anchor QQQ 기준으로 업데이트'")
    print('  git push')


if __name__ == '__main__':
    main()
