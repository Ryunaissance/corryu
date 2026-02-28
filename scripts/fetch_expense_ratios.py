#!/usr/bin/env python3
"""
yfinance로 전체 ETF 수수료(expense ratio) 수집 스크립트

수집 대상: output/etf_data.json의 전체 티커 (~1,651개)
수집 방법: yfinance Ticker.info['annualReportExpenseRatio']
           없으면  Ticker.info['totalExpenseRatio'] fallback
저장 위치: data_scraped/expense_ratios.pkl  (Dict[str, float])
           data_scraped/expense_ratios_raw.json  (디버그용)

중단/재시작 지원:
    중간 체크포인트를 expense_ratios_raw.json에 실시간 저장.
    재실행 시 이미 조회된 티커는 건너뛰고 이어서 처리.

실행 예시:
    python scripts/fetch_expense_ratios.py
    python scripts/fetch_expense_ratios.py --reset   # 체크포인트 무시 후 처음부터
"""

import argparse
import json
import logging
import os
import pickle
import sys
import time

import yfinance as yf

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-7s %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
DATA_SCRAPED = os.path.join(BASE_DIR, 'data_scraped')

CHECKPOINT_JSON = os.path.join(DATA_SCRAPED, 'expense_ratios_raw.json')
OUTPUT_PKL      = os.path.join(DATA_SCRAPED, 'expense_ratios.pkl')

SLEEP_PER_TICKER = 0.25   # Yahoo rate limit 방지 (초)
CHECKPOINT_EVERY = 50     # N개 처리마다 체크포인트 저장


def load_all_tickers() -> list[str]:
    """etf_data.json에서 전체 티커 목록 추출"""
    path = os.path.join(OUTPUT_DIR, 'etf_data.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    tickers = []
    for etfs in (data.get('allData') or data).values():
        if isinstance(etfs, list):
            tickers.extend(e['ticker'] for e in etfs)
    return sorted(set(tickers))


def load_checkpoint() -> dict[str, float | None]:
    """기존 체크포인트 로드 (없으면 빈 dict)"""
    if os.path.exists(CHECKPOINT_JSON):
        with open(CHECKPOINT_JSON, encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_checkpoint(results: dict):
    os.makedirs(DATA_SCRAPED, exist_ok=True)
    with open(CHECKPOINT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def fetch_one(ticker: str) -> float | None:
    """단일 티커 수수료 조회. 실패 시 None 반환."""
    try:
        info = yf.Ticker(ticker).info
        for key in ('annualReportExpenseRatio', 'totalExpenseRatio'):
            v = info.get(key)
            if v is not None and isinstance(v, (int, float)) and 0 < v < 1:
                return float(v)
        return None
    except Exception as e:
        log.debug('%s fetch error: %s', ticker, e)
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true',
                        help='체크포인트 무시하고 처음부터 재수집')
    args = parser.parse_args()

    tickers = load_all_tickers()
    log.info('전체 티커: %d개', len(tickers))

    results: dict[str, float | None] = {} if args.reset else load_checkpoint()
    if results:
        log.info('체크포인트 로드: %d개 이미 완료', len(results))

    todo = [t for t in tickers if t not in results]
    log.info('남은 조회: %d개  (예상 소요 약 %.0f분)',
             len(todo), len(todo) * SLEEP_PER_TICKER / 60)

    found = sum(1 for v in results.values() if v is not None)

    for i, ticker in enumerate(todo, 1):
        val = fetch_one(ticker)
        results[ticker] = val
        if val is not None:
            found += 1
            log.info('[%d/%d] %-10s %.4f%%', i, len(todo), ticker, val * 100)
        else:
            log.debug('[%d/%d] %-10s None', i, len(todo), ticker)

        if i % CHECKPOINT_EVERY == 0:
            save_checkpoint(results)
            total_done = len(results)
            log.info('--- 체크포인트 저장 %d/%d  (수수료 확보: %d개) ---',
                     total_done, len(tickers), found)

        time.sleep(SLEEP_PER_TICKER)

    # 최종 저장
    save_checkpoint(results)

    # pkl 저장 (None 제외한 실제 값만)
    clean: dict[str, float] = {t: v for t, v in results.items() if v is not None}
    os.makedirs(DATA_SCRAPED, exist_ok=True)
    with open(OUTPUT_PKL, 'wb') as f:
        pickle.dump(clean, f)

    total = len(tickers)
    log.info('완료: %d/%d개 수수료 확보 (%.1f%%)', len(clean), total,
             len(clean) / total * 100)
    log.info('저장: %s', OUTPUT_PKL)

    # 간단한 커버리지 리포트
    missing = [t for t in tickers if results.get(t) is None]
    if missing:
        log.info('수수료 없는 티커 %d개: %s ...', len(missing), missing[:20])


if __name__ == '__main__':
    main()
