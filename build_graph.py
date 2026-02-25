"""
그래프 뷰용 데이터 생성 (build_graph.py)
  - correlation_matrix_monthly.csv → output/graph_data.json
  - r >= STORE_MIN_R 인 쌍만 엣지로 저장
  - 브라우저(graph.html)에서 슬라이더로 동적 필터링

사용법:
  python build_graph.py
  (사전에 python build_monthly_corr.py 가 실행되어 있어야 함)
"""
import json
import os
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'src'))
from config import SECTOR_DEFS, CORR_MONTHLY_CSV

# ── 설정 ──────────────────────────────────────────────
STORE_MIN_R   = 0.85   # JSON 저장 최소 r (슬라이더 하한)
ETF_DATA_JSON = os.path.join(ROOT, 'output', 'etf_data.json')
OUT_JSON      = os.path.join(ROOT, 'output', 'graph_data.json')

# 섹터별 색상 (다크 테마)
SECTOR_COLORS = {
    'S01': '#60a5fa',  # US 대형주   - blue
    'S02': '#a78bfa',  # 테크        - purple
    'S03': '#34d399',  # 헬스케어    - emerald
    'S04': '#fbbf24',  # 금융        - amber
    'S05': '#f87171',  # 경기소비재  - red
    'S06': '#fb923c',  # 필수소비재  - orange
    'S07': '#94a3b8',  # 산업재      - slate
    'S08': '#fde047',  # 유틸리티    - yellow
    'S09': '#38bdf8',  # 커뮤니케이션- sky
    'S10': '#a3e635',  # 소재        - lime
    'S11': '#4ade80',  # 국제선진국  - green
    'S12': '#2dd4bf',  # 신흥국      - teal
    'S13': '#f472b6',  # 중소형주    - pink
    'S14': '#818cf8',  # 투자등급채권- indigo
    'S15': '#67e8f9',  # 단기채      - cyan
    'S16': '#fdba74',  # 하이일드    - orange2
    'S17': '#86efac',  # TIPS        - green2
    'S18': '#fcd34d',  # 금/귀금속   - gold
    'S19': '#6b7280',  # 에너지      - gray
    'S20': '#c084fc',  # 부동산      - violet
    'S21': '#f59e0b',  # 가상자산    - amber2
    'S22': '#ef4444',  # 인버스      - red2
    'S24': '#475569',  # 테마        - slate2
}


def main():
    # 1. 상관행렬 로드
    if not os.path.exists(CORR_MONTHLY_CSV):
        print(f"❌ 파일 없음: {CORR_MONTHLY_CSV}")
        print("   먼저 python build_monthly_corr.py 를 실행하세요.")
        sys.exit(1)

    print("📊 상관행렬 로드 중...")
    corr = pd.read_csv(CORR_MONTHLY_CSV, index_col=0)
    tickers = list(corr.columns)
    n = len(tickers)
    print(f"   {n}×{n} 행렬  ({n*(n-1)//2:,}쌍)")

    # 2. ETF 메타데이터
    print("   ETF 메타데이터 로드 중...")
    with open(ETF_DATA_JSON, encoding='utf-8') as f:
        db = json.load(f)
    meta = {}
    for sid, etfs in db['allData'].items():
        for e in etfs:
            meta[e['ticker']] = {
                'n': e['name'],
                's': sid,
                'a': round(e.get('aum', 0) / 1e9, 2),
            }

    # 3. 노드 목록 (상관행렬에 있는 티커 기준)
    nodes = []
    for tk in tickers:
        m = meta.get(tk, {})
        nodes.append({
            'id': tk,
            'n':  m.get('n', tk),
            's':  m.get('s', 'S24'),
            'a':  m.get('a', 0.0),
        })

    # 4. 엣지 계산 (numpy 벡터화, 상삼각만)
    print(f"   엣지 계산 중 (r ≥ {STORE_MIN_R})...")
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
    print(f"   엣지 수: {len(links):,}개")

    # 5. 섹터 메타 (이름 + 색상)
    sectors = {
        sid: {
            'name':    sdef['name'],
            'name_en': sdef['name_en'],
            'color':   SECTOR_COLORS.get(sid, '#888888'),
            'ac':      sdef['asset_class'],
        }
        for sid, sdef in SECTOR_DEFS.items()
    }

    # 6. 저장
    out = {
        'nodes': nodes,
        'links': links,
        'sectors': sectors,
        'meta': {
            'n_nodes':        len(nodes),
            'n_links_stored': len(links),
            'store_min_r':    STORE_MIN_R,
        },
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))

    size_mb = os.path.getsize(OUT_JSON) / 1024 ** 2
    print(f"✅ 저장 완료: {OUT_JSON}")
    print(f"   노드 {len(nodes):,}개 | 엣지 {len(links):,}개 | {size_mb:.1f} MB")
    print()
    print("💡 이후 git add output/graph_data.json && git commit 후 배포하세요.")


if __name__ == '__main__':
    main()
