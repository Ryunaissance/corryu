"""
yfinance 기반 그래프 데이터 생성 (build_graph_yfinance.py)
  - pkl/CSV 없이도 yfinance에서 직접 월간 가격 다운로드
  - 상관행렬 계산 후 output/graph_data.json 저장

사용법:
  pip install yfinance pandas numpy
  python build_graph_yfinance.py

소요시간: 약 5~15분 (네트워크 환경에 따라 다름)
"""
import json
import os
import sys
import time
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'src'))
from config import SECTOR_DEFS

# ── 설정 ──────────────────────────────────────────────
PERIOD        = '10y'   # 최근 10년 데이터
INTERVAL      = '1mo'   # 월 단위
MIN_MONTHS    = 24      # 상관계수 최소 유효 기간
STORE_MIN_R   = 0.85    # JSON 저장 최소 r
BATCH_SIZE    = 200     # yfinance 한 번에 요청할 티커 수
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


def load_meta():
    with open(ETF_DATA_JSON, encoding='utf-8') as f:
        db = json.load(f)
    meta = {}
    all_tickers = []
    for sid, etfs in db['allData'].items():
        for e in etfs:
            tk = e['ticker']
            meta[tk] = {
                'n': e['name'],
                's': sid,
                'a': round(e.get('aum', 0) / 1e9, 2),
            }
            all_tickers.append(tk)
    return meta, all_tickers


def fetch_monthly_prices(tickers):
    """yfinance 배치 다운로드 → 월말 종가 DataFrame 반환"""
    import yfinance as yf

    all_close = {}
    total_batches = (len(tickers) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"   배치 {batch_num}/{total_batches}  ({len(batch)}개 티커)...", end=' ', flush=True)

        try:
            raw = yf.download(
                tickers=batch,
                period=PERIOD,
                interval=INTERVAL,
                auto_adjust=True,
                progress=False,
                threads=True,
            )

            # Close 컬럼 추출 (멀티인덱스 or 단일)
            if isinstance(raw.columns, pd.MultiIndex):
                close = raw['Close'] if 'Close' in raw.columns.get_level_values(0) else raw.iloc[:, :len(batch)]
            else:
                close = raw[['Close']] if 'Close' in raw.columns else raw

            if isinstance(close, pd.Series):
                close = close.to_frame(name=batch[0])

            for tk in close.columns:
                col = close[tk].dropna()
                if len(col) >= MIN_MONTHS:
                    all_close[tk] = col

            print(f"✓ ({sum(1 for tk in batch if tk in all_close)}개 성공)")

        except Exception as e:
            print(f"⚠️ 오류: {e}")

        # 과도한 요청 방지
        if batch_num < total_batches:
            time.sleep(0.5)

    if not all_close:
        raise RuntimeError("다운로드된 데이터가 없습니다.")

    # 공통 인덱스로 합치기
    df = pd.DataFrame(all_close)
    print(f"\n   성공한 티커: {df.shape[1]}개 / 요청 {len(tickers)}개")
    return df


def compute_corr(df_monthly):
    """월간 수익률 → 상관행렬"""
    df_ret = df_monthly.pct_change(fill_method=None)
    valid = df_ret.columns[df_ret.count() >= MIN_MONTHS]
    df_ret = df_ret[valid]
    print(f"   유효 티커(≥{MIN_MONTHS}개월): {len(valid)}개")
    print("   상관행렬 계산 중...")
    return df_ret.corr(method='pearson', min_periods=MIN_MONTHS)


def build_graph(corr, meta):
    tickers = list(corr.columns)
    n = len(tickers)

    nodes = []
    for tk in tickers:
        m = meta.get(tk, {})
        nodes.append({
            'id': tk,
            'n':  m.get('n', tk),
            's':  m.get('s', 'S24'),
            'a':  m.get('a', 0.0),
        })

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

    sectors = {
        sid: {
            'name':    sdef['name'],
            'name_en': sdef['name_en'],
            'color':   SECTOR_COLORS.get(sid, '#888888'),
            'ac':      sdef['asset_class'],
        }
        for sid, sdef in SECTOR_DEFS.items()
    }

    return {
        'nodes': nodes,
        'links': links,
        'sectors': sectors,
        'meta': {
            'n_nodes':        len(nodes),
            'n_links_stored': len(links),
            'store_min_r':    STORE_MIN_R,
        },
    }


def main():
    print("📋 ETF 메타데이터 로드 중...")
    meta, tickers = load_meta()
    print(f"   총 {len(tickers)}개 티커")

    print("\n📡 yfinance 월간 가격 다운로드 중...")
    df_monthly = fetch_monthly_prices(tickers)

    print("\n📊 상관행렬 계산 중...")
    corr = compute_corr(df_monthly)

    print("\n🔗 그래프 데이터 생성 중...")
    out = build_graph(corr, meta)

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))

    size_mb = os.path.getsize(OUT_JSON) / 1024 ** 2
    print(f"\n✅ 저장 완료: {OUT_JSON}")
    print(f"   노드 {out['meta']['n_nodes']:,}개 | 엣지 {out['meta']['n_links_stored']:,}개 | {size_mb:.1f} MB")
    print()
    print("💡 다음 단계:")
    print("   git add output/graph_data.json")
    print("   git commit -m 'feat: graph_data.json 추가'")
    print("   git push")


if __name__ == '__main__':
    main()
