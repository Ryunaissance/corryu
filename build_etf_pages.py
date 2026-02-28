"""build_etf_pages.py — ETF별 개별 JSON 파일 배치 생성

output/etf_data.json 에서 각 티커의 데이터를 추출해
output/etf/{TICKER}.json 파일을 생성합니다.

etf-detail.html 이 625KB 전체 JSON 대신 500B짜리 개별 파일을 먼저 로드하게 됩니다.

Usage:
    python3 build_etf_pages.py
"""
import json
import os
import sys
from datetime import datetime


ROOT = os.path.dirname(os.path.abspath(__file__))
ETF_DATA_PATH = os.path.join(ROOT, 'output', 'etf_data.json')
ETF_DIR = os.path.join(ROOT, 'output', 'etf')


def build_etf_pages():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ETF 개별 JSON 생성 시작")

    with open(ETF_DATA_PATH, encoding='utf-8') as f:
        raw = json.load(f)

    all_data = raw.get('allData', raw)
    os.makedirs(ETF_DIR, exist_ok=True)

    count = 0
    for sid, etfs in all_data.items():
        if not isinstance(etfs, list):
            continue
        for etf in etfs:
            ticker = etf.get('ticker', '').upper().strip()
            if not ticker:
                continue
            out = {'ticker': ticker, 'sid': sid, 'etf': etf}
            path = os.path.join(ETF_DIR, f'{ticker}.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
            count += 1

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 완료: {count}개 ETF JSON 생성 → output/etf/")
    return count


if __name__ == '__main__':
    n = build_etf_pages()
    sys.exit(0 if n > 0 else 1)
