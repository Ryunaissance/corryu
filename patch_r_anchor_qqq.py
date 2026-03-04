"""patch_r_anchor_qqq.py — 주식 시장 슈퍼섹터 r_anchor(QQQ) + smh_corr(SMH) 패치

Yahoo Finance 월간 데이터로 QQQ/SMH 상관계수를 계산해
output/etf_data.json 의 r_anchor, smh_corr 컬럼을 업데이트합니다.
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
from config import SUPER_SECTOR_DEFS, SECTOR_DEFS, MANUAL_SECTOR_OVERRIDES

# ── 설정 ──────────────────────────────────────────────
RANGE        = 'max'      # 상장일부터 전체 이력 사용
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

    # 2. 슈퍼섹터 소속 섹터 및 ETF 티커 수집 (QQQ 기준)
    ss_sub_sectors = set()
    for ss_def in SUPER_SECTOR_DEFS.values():
        ss_sub_sectors.update(ss_def['sub_sectors'])

    ss_tickers = []
    for sid in sorted(ss_sub_sectors):
        for etf in db['allData'].get(sid, []):
            ss_tickers.append(etf['ticker'])

    # 2b. MANUAL_SECTOR_OVERRIDES 소속 ETF 티커 + 해당 섹터 앵커 수집
    #     (섹터별 앵커 기준으로 별도 계산)
    override_anchors = {}   # anchor_ticker → [etf_tickers]
    for tk, sid in MANUAL_SECTOR_OVERRIDES.items():
        anchor = SECTOR_DEFS.get(sid, {}).get('anchor')
        if anchor:
            override_anchors.setdefault(anchor, []).append(tk)

    override_tickers = [tk for tks in override_anchors.values() for tk in tks]
    override_anchor_list = list(override_anchors.keys())

    all_fetch = list(set(['QQQ', 'SMH'] + ss_tickers + override_tickers + override_anchor_list))
    print(f'   슈퍼섹터 ETF: {len(ss_tickers)}개 + QQQ/SMH + 수동오버라이드 {len(override_tickers)}개 → 총 {len(all_fetch)}개 다운로드 예정')

    # 3. 월간 데이터 다운로드 (상장일부터 전체 이력)
    print(f'\n📡 Yahoo Finance 월간 데이터 다운로드 (range=max, {MAX_WORKERS}스레드)...')
    price_data = download_all(all_fetch)
    print(f'   완료: {len(price_data)}/{len(all_fetch)}개 성공')

    if 'QQQ' not in price_data:
        print('❌ QQQ 데이터 다운로드 실패. 네트워크 연결을 확인하세요.')
        sys.exit(1)

    # 4. 월간 수익률 → QQQ/SMH 상관계수 계산 (슈퍼섹터)
    print('\n📊 QQQ/SMH 상관계수 계산 중...')
    df = pd.DataFrame(price_data)
    # ETF마다 Yahoo Finance 월간 bar의 시작 날짜가 다를 수 있음(IPO일 등).
    # 날짜가 다르면 DataFrame을 outer-join할 때 중간에 NaN 행이 생겨
    # pct_change()가 QQQ 수익률을 잘못 NaN으로 만드는 버그가 발생.
    # resample('ME').last()로 월말 기준 통일 → 모든 ETF 동일 날짜 격자 사용.
    df = df.resample('ME').last()
    df_ret = df.pct_change(fill_method=None)
    corr   = df_ret.corrwith(df_ret['QQQ'], min_periods=MIN_MONTHS)
    corr['QQQ'] = 1.0   # QQQ는 자기 자신이 기준 → 항상 1.0
    valid  = corr.dropna()
    print(f'   QQQ 기준 유효 티커: {len(valid)}개')

    # SMH 상관계수 (EQUITY_MARKET 더블 앵커)
    if 'SMH' in df_ret.columns:
        corr_smh = df_ret.corrwith(df_ret['SMH'], min_periods=MIN_MONTHS)
        corr_smh['SMH'] = 1.0   # SMH는 자기 자신 → 항상 1.0
        valid_smh = corr_smh.dropna()
        print(f'   SMH 기준 유효 티커: {len(valid_smh)}개')
    else:
        corr_smh = pd.Series(dtype=float)
        print('   ⚠️  SMH 데이터 없음 → smh_corr 스킵')

    # 4b. 수동 오버라이드 ETF → 섹터 앵커 기준 상관계수 계산
    override_corr = {}   # ticker → r_anchor (vs 섹터 앵커)
    for anchor, tickers in override_anchors.items():
        if anchor not in price_data:
            print(f'   ⚠️  앵커 {anchor} 데이터 없음 → 스킵')
            continue
        anchor_ret = df_ret.get(anchor)
        if anchor_ret is None:
            continue
        for tk in tickers:
            if tk in df_ret.columns:
                r = float(df_ret[tk].corr(anchor_ret, min_periods=MIN_MONTHS))
                if not np.isnan(r):
                    override_corr[tk] = round(r, 4)
                    print(f'   {tk} vs {anchor}: r={r:.4f}')

    # 5. etf_data.json r_anchor + smh_corr 패치
    print('\n✏️  r_anchor / smh_corr 패치 중...')
    updated_r = 0
    updated_s = 0
    skipped   = 0
    for sid in sorted(ss_sub_sectors):
        for etf in db['allData'].get(sid, []):
            tk = etf['ticker']
            if tk in corr and not pd.isna(corr[tk]):
                etf['r_anchor'] = round(float(corr[tk]), 4)
                updated_r += 1
            else:
                skipped += 1
            if tk in corr_smh and not pd.isna(corr_smh[tk]):
                etf['smh_corr'] = round(float(corr_smh[tk]), 4)
                updated_s += 1

    # 5b. 수동 오버라이드 ETF r_anchor 패치 (섹터 앵커 기준)
    for tk, r_val in override_corr.items():
        sid = MANUAL_SECTOR_OVERRIDES.get(tk)
        if not sid:
            continue
        for etf in db['allData'].get(sid, []):
            if etf['ticker'] == tk:
                etf['r_anchor'] = r_val
                updated_r += 1
                break

    print(f'   r_anchor 업데이트: {updated_r}개 | smh_corr 업데이트: {updated_s}개 | 스킵: {skipped}개')

    # 6. 저장
    with open(ETF_DATA_JSON, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, separators=(',', ':'))
    print(f'   저장: {ETF_DATA_JSON}')

    elapsed = time.time() - t0
    print(f'\n✅ 완료! ({elapsed:.0f}초)')
    print('\n다음 단계:')
    print('  git add output/etf_data.json')
    print("  git commit -m 'feat: r_anchor QQQ + smh_corr 업데이트'")
    print('  git push')


if __name__ == '__main__':
    main()
