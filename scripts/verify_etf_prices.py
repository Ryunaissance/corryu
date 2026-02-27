#!/usr/bin/env python3
"""
ETF 가격 데이터 무결성 검증 스크립트

확인 항목:
  1. 티커 누락   — etf_data.json에 있지만 etf_prices_log에 없는 티커
  2. 데이터 없음 — row_count = 0 (상폐 포함)
  3. 데이터 빈약 — row_count < MIN_ROWS (월봉 기준 12개월 미만)
  4. 최신 날짜   — 핵심 ETF 30개의 max(date)가 최근인지 확인
  5. 요약 통계   — 전체 row 분포

실행:
    SUPABASE_URL=https://xxx.supabase.co \\
    SUPABASE_SERVICE_KEY=eyJ... \\
    python scripts/verify_etf_prices.py
"""

import os
import sys
import json
import math
import logging
from datetime import date, timedelta
from collections import Counter

from supabase import create_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-7s %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)

# ── 설정 ──────────────────────────────────────────────────────────────
MIN_ROWS        = 12     # 이 미만이면 '데이터 빈약' 경고 (일봉 기준이므로 실제론 충분히 낮게 잡음)
MAX_DATE_LAG    = 90     # 최신 날짜가 오늘로부터 이 일수 이상 오래되면 경고
SPOT_CHECK_ETFS = [      # 최신 날짜 확인용 핵심 ETF
    'SPY', 'QQQ', 'IWM', 'VTI', 'BND', 'GLD', 'TLT',
    'XLK', 'XLV', 'XLF', 'XLE', 'XLU', 'VNQ', 'EEM',
    'SQQQ', 'GBTC', 'IBIT', 'HYG', 'LQD', 'SCHP',
    'VEA', 'VWO', 'EFA', 'IEFA', 'AGG', 'SHV', 'BIL',
    'IAU', 'GDX', 'AMLP',
]

SUPABASE_URL         = os.environ.get('SUPABASE_URL', '')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    log.error('환경변수 SUPABASE_URL, SUPABASE_SERVICE_KEY 를 설정하세요.')
    sys.exit(1)


# ── 헬퍼 ──────────────────────────────────────────────────────────────

def load_json_tickers() -> set[str]:
    json_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'etf_data.json')
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    tickers = set()
    for etfs in data.get('allData', {}).values():
        for etf in etfs:
            tickers.add(etf['ticker'])
    return tickers


def fetch_log_all(client) -> list[dict]:
    """etf_prices_log 전체 행 반환"""
    rows = []
    page_size = 1000
    offset = 0
    while True:
        res = (
            client.table('etf_prices_log')
            .select('ticker,loaded_at,row_count')
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows


def fetch_max_date(client, ticker: str) -> str | None:
    """특정 티커의 가장 최신 날짜 반환"""
    res = (
        client.table('etf_prices')
        .select('date')
        .eq('ticker', ticker)
        .order('date', desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0]['date'] if rows else None


def fetch_row_count_db(client, ticker: str) -> int:
    """DB에서 직접 COUNT(*) — log.row_count 교차 검증용"""
    res = (
        client.table('etf_prices')
        .select('ticker', count='exact')
        .eq('ticker', ticker)
        .limit(1)
        .execute()
    )
    return res.count or 0


# ── 메인 ──────────────────────────────────────────────────────────────

def main():
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    today  = date.today()
    issues = []

    # ── 1. 기준 티커 목록 ──────────────────────────────────────────────
    json_tickers = load_json_tickers()
    log.info(f'etf_data.json 티커: {len(json_tickers)}개')

    # ── 2. etf_prices_log 전체 fetch ──────────────────────────────────
    log_rows = fetch_log_all(client)
    log.info(f'etf_prices_log 행: {len(log_rows)}개')

    log_by_ticker = {r['ticker']: r for r in log_rows}
    log_tickers   = set(log_by_ticker.keys())

    # ── 3. 누락 티커 ──────────────────────────────────────────────────
    missing = json_tickers - log_tickers
    if missing:
        log.warning(f'[누락] etf_prices_log에 없는 티커 {len(missing)}개:')
        for t in sorted(missing):
            log.warning(f'       {t}')
        issues.append(f'누락 티커 {len(missing)}개')
    else:
        log.info('[OK] 누락 티커 없음')

    # ── 4. row_count 분석 ──────────────────────────────────────────────
    zero_rows   = []
    sparse_rows = []

    for r in log_rows:
        if r['ticker'] not in json_tickers:
            continue  # 이미 json에서 삭제된 ETF는 스킵
        cnt = r['row_count']
        if cnt == 0:
            zero_rows.append(r['ticker'])
        elif cnt < MIN_ROWS:
            sparse_rows.append((r['ticker'], cnt))

    if zero_rows:
        log.warning(f'[row=0] 데이터 없는 티커 {len(zero_rows)}개 (상폐 포함):')
        for t in sorted(zero_rows):
            log.warning(f'        {t}')
        issues.append(f'row_count=0 티커 {len(zero_rows)}개')
    else:
        log.info('[OK] row_count=0 티커 없음')

    if sparse_rows:
        log.warning(f'[빈약] row_count < {MIN_ROWS} 인 티커 {len(sparse_rows)}개:')
        for t, cnt in sorted(sparse_rows):
            log.warning(f'       {t}: {cnt}행')
        issues.append(f'row_count 빈약 티커 {len(sparse_rows)}개')
    else:
        log.info(f'[OK] row_count < {MIN_ROWS} 티커 없음')

    # ── 5. 요약 통계 ──────────────────────────────────────────────────
    counts = [r['row_count'] for r in log_rows if r['ticker'] in json_tickers]
    if counts:
        total_rows = sum(counts)
        avg_rows   = total_rows / len(counts)
        max_rows   = max(counts)
        min_rows   = min(c for c in counts if c > 0) if any(c > 0 for c in counts) else 0
        buckets    = Counter(
            '0' if c == 0 else
            '1–99' if c < 100 else
            '100–999' if c < 1000 else
            '1000–4999' if c < 5000 else
            '5000+'
            for c in counts
        )
        log.info('--- row_count 분포 ---')
        for label in ['0', '1–99', '100–999', '1000–4999', '5000+']:
            log.info(f'  {label:12s}: {buckets[label]:4d}개')
        log.info(f'  합계(행): {total_rows:,}  평균: {avg_rows:.0f}  최대: {max_rows:,}  최소(>0): {min_rows:,}')

    # ── 6. 최신 날짜 스팟체크 ─────────────────────────────────────────
    log.info(f'--- 핵심 ETF {len(SPOT_CHECK_ETFS)}개 최신 날짜 확인 ---')
    stale = []
    not_found = []

    for ticker in SPOT_CHECK_ETFS:
        if ticker not in log_tickers:
            not_found.append(ticker)
            log.warning(f'  {ticker:6s}: log에 없음')
            continue

        max_date = fetch_max_date(client, ticker)
        if max_date is None:
            not_found.append(ticker)
            log.warning(f'  {ticker:6s}: DB에 행 없음')
            continue

        dt     = date.fromisoformat(max_date)
        lag    = (today - dt).days
        status = 'OK' if lag <= MAX_DATE_LAG else '⚠ STALE'
        log.info(f'  {ticker:6s}: 최신={max_date}  ({lag}일 전)  {status}')

        if lag > MAX_DATE_LAG:
            stale.append((ticker, max_date, lag))

    if stale:
        log.warning(f'[오래된 데이터] {MAX_DATE_LAG}일 초과 티커 {len(stale)}개:')
        for t, d, lag in stale:
            log.warning(f'  {t}: {d} ({lag}일 전)')
        issues.append(f'오래된 데이터 티커 {len(stale)}개')
    else:
        log.info('[OK] 최신 날짜 모두 정상')

    if not_found:
        issues.append(f'핵심 ETF DB 미조회 {len(not_found)}개: {not_found}')

    # ── 7. 최종 결과 ──────────────────────────────────────────────────
    print('\n' + '=' * 60)
    if issues:
        print(f'[검증 결과] 이슈 {len(issues)}개 발견:')
        for i, msg in enumerate(issues, 1):
            print(f'  {i}. {msg}')
        print('\n→ 위 티커들은 load_etf_prices_initial.py 재실행으로 보완 가능합니다.')
    else:
        print('[검증 결과] 이상 없음 — 모든 ETF 가격 데이터 정상')
    print('=' * 60)


if __name__ == '__main__':
    main()
