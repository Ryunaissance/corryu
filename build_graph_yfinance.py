"""
yfinance 없이 Yahoo Finance API 직접 호출로 그래프 데이터 생성
  - requests + ThreadPoolExecutor 병렬 다운로드
  - 월간 수익률 상관행렬 계산 → output/graph_data.json 저장

사용법:
  python build_graph_yfinance.py
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
from config import SECTOR_DEFS

# ── 설정 ──────────────────────────────────────────────
RANGE         = 'max'        # 상장일부터 최신 데이터까지 전체 이력 사용
MIN_MONTHS    = 24           # 상관계수 최소 유효 기간
STORE_MIN_R   = 0.85         # JSON 저장 최소 r
MAX_WORKERS   = 12           # 병렬 다운로드 스레드 수
RETRY_MAX     = 3            # 실패 시 재시도 횟수
ETF_DATA_JSON = os.path.join(ROOT, 'output', 'etf_data.json')
OUT_JSON      = os.path.join(ROOT, 'output', 'graph_data.json')

SECTOR_COLORS = {
    'S01': '#60a5fa', 'S02': '#a78bfa', 'S03': '#34d399',
    'S04': '#fbbf24', 'S05': '#f87171', 'S06': '#fb923c',
    'S07': '#94a3b8', 'S08': '#fde047', 'S09': '#38bdf8',
    'S10': '#a3e635', 'S11': '#4ade80', 'S12': '#2dd4bf',
    'S13': '#f472b6', 'S14': '#818cf8', 'S15': '#67e8f9',
    'S16': '#fdba74', 'S17': '#86efac', 'S18': '#fcd34d',
    'S19': '#6b7280', 'S20': '#c084fc', 'S21': '#f59e0b',
    'S22': '#ef4444', 'S24': '#475569',
}

# 요청 헤더 (봇 차단 우회)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}

_print_lock = threading.Lock()


def safe_print(msg):
    with _print_lock:
        print(msg, flush=True)


def fetch_ticker(session, ticker):
    """Yahoo Finance chart API로 월간 종가 Series 반환. 실패 시 None."""
    url = (
        f'https://query2.finance.yahoo.com/v8/finance/chart/{ticker}'
        f'?range={RANGE}&interval=1mo&includeAdjustedClose=true'
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
            ts    = result[0]['timestamp']
            meta  = result[0].get('meta', {})
            # adjclose 우선, 없으면 close
            indicators = result[0].get('indicators', {})
            adj = indicators.get('adjclose', [{}])
            if adj and adj[0].get('adjclose'):
                prices = adj[0]['adjclose']
            else:
                prices = indicators.get('quote', [{}])[0].get('close', [])
            if not prices:
                return None
            idx = pd.to_datetime(ts, unit='s', utc=True).tz_convert(None)
            s = pd.Series(prices, index=idx, name=ticker, dtype=float)
            s = s.dropna()
            return s if len(s) >= MIN_MONTHS else None
        except Exception:
            time.sleep(1)
    return None


def download_all(tickers):
    """병렬 다운로드. {ticker: Series} 딕셔너리 반환."""
    results = {}
    done = 0
    total = len(tickers)

    session = requests.Session()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_ticker, session, tk): tk for tk in tickers}
        for fut in as_completed(futures):
            tk = futures[fut]
            done += 1
            s = fut.result()
            if s is not None:
                results[tk] = s
            if done % 100 == 0 or done == total:
                safe_print(f'   {done}/{total}  (성공: {len(results)}개)')

    return results


def build_graph_data(corr, meta):
    tickers = list(corr.columns)
    n = len(tickers)

    nodes = []
    for tk in tickers:
        m = meta.get(tk, {})
        nodes.append({'id': tk, 'n': m.get('n', tk), 's': m.get('s', 'S24'), 'a': m.get('a', 0.0)})

    print(f'   엣지 계산 중 (r ≥ {STORE_MIN_R})...')
    arr = corr.values.astype(np.float32)
    np.fill_diagonal(arr, np.nan)
    ri, ci = np.triu_indices(n, k=1)
    rv = arr[ri, ci]
    mask = (rv >= STORE_MIN_R) & ~np.isnan(rv)
    ri, ci, rv = ri[mask], ci[mask], rv[mask]
    links = [
        {'s': tickers[int(i)], 't': tickers[int(j)], 'r': round(float(r), 3)}
        for i, j, r in zip(ri, ci, rv)
    ]
    print(f'   엣지 수: {len(links):,}개')

    sectors = {
        sid: {
            'name': sdef['name'], 'name_en': sdef['name_en'],
            'color': SECTOR_COLORS.get(sid, '#888888'), 'ac': sdef['asset_class'],
        }
        for sid, sdef in SECTOR_DEFS.items()
    }
    return {
        'nodes': nodes, 'links': links, 'sectors': sectors,
        'meta': {'n_nodes': len(nodes), 'n_links_stored': len(links), 'store_min_r': STORE_MIN_R},
    }


def main():
    t0 = time.time()

    print('📋 ETF 메타데이터 로드...')
    with open(ETF_DATA_JSON, encoding='utf-8') as f:
        db = json.load(f)
    meta = {}
    tickers = []
    for sid, etfs in db['allData'].items():
        for e in etfs:
            tk = e['ticker']
            meta[tk] = {'n': e['name'], 's': sid, 'a': round(e.get('aum', 0) / 1e9, 2)}
            tickers.append(tk)
    print(f'   {len(tickers)}개 티커')

    print(f'\n📡 Yahoo Finance 월간 데이터 다운로드 (병렬 {MAX_WORKERS}스레드)...')
    price_data = download_all(tickers)
    print(f'   완료: {len(price_data)}/{len(tickers)}개 성공')

    if len(price_data) < 50:
        print('❌ 성공한 티커가 너무 적습니다. 네트워크 연결을 확인하세요.')
        sys.exit(1)

    print('\n📊 상관행렬 계산 중...')
    df = pd.DataFrame(price_data)
    # ETF마다 Yahoo Finance 월간 bar 시작 날짜가 다를 수 있어(IPO일 등)
    # outer-join 시 중간에 NaN 행이 생기면 pct_change가 수익률을 잘못 NaN으로 만든다.
    # resample('ME').last()로 월말 기준 통일 → 모든 ETF 동일 날짜 격자 사용.
    df = df.resample('ME').last()
    df_ret = df.pct_change(fill_method=None)
    valid = df_ret.columns[df_ret.count() >= MIN_MONTHS]
    df_ret = df_ret[valid]
    print(f'   유효 티커(≥{MIN_MONTHS}개월): {len(valid)}개')
    corr = df_ret.corr(method='pearson', min_periods=MIN_MONTHS)

    print('\n🔗 그래프 데이터 생성 중...')
    out = build_graph_data(corr, meta)

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))

    size_mb = os.path.getsize(OUT_JSON) / 1024 ** 2
    elapsed = time.time() - t0
    print(f'\n✅ 저장 완료: {OUT_JSON}')
    print(f'   노드 {out["meta"]["n_nodes"]:,}개 | 엣지 {out["meta"]["n_links_stored"]:,}개 | {size_mb:.1f} MB')
    print(f'   소요 시간: {elapsed:.0f}초')
    print()
    print('💡 다음 단계:')
    print('   git add output/graph_data.json')
    print("   git commit -m 'feat: graph_data.json 추가'")
    print('   git push')


if __name__ == '__main__':
    main()
