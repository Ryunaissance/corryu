"""
CORRYU ETF Dashboard - MECE 검증 모듈
"""
from typing import Any
from config import SECTOR_DEFS


def verify_mece(classification: dict[str, dict[str, Any]], all_tickers: set[str]) -> bool:
    """MECE(Mutually Exclusive, Collectively Exhaustive) 검증

    Args:
        classification: ticker → {'sector': ..., 'method': ..., 'r_anchor': ...}
        all_tickers: 전체 ETF 티커 셋

    Returns:
        bool: 검증 통과 여부
    """
    classified_tickers = set(classification.keys())
    passed = True

    # 1. Exhaustive: 모든 ETF가 분류되었는가?
    missing = all_tickers - classified_tickers
    extra = classified_tickers - all_tickers
    if missing:
        print(f"[FAIL] 미분류 ETF {len(missing)}개: {sorted(missing)[:20]}...")
        passed = False
    if extra:
        print(f"[WARN] 상관계수 매트릭스에 없는 분류 {len(extra)}개: {sorted(extra)[:20]}...")

    # 2. Exclusive: 중복 분류가 없는가? (dict이므로 구조적으로 보장됨)
    print(f"[OK] 중복 분류 없음 (dict 구조)")

    # 3. 섹터별 크기 분포
    from collections import Counter
    sector_counts = Counter(info['sector'] for info in classification.values())

    print(f"\n--- 섹터별 ETF 분포 ({len(classification)}개 전체) ---")
    total = 0
    for sid in sorted(SECTOR_DEFS.keys()):
        sdef = SECTOR_DEFS[sid]
        count = sector_counts.get(sid, 0)
        total += count
        anchor_str = sdef['anchor'] or '—'
        warning = ""
        if count > 200:
            warning = " ⚠️ 과대"
        elif count < 3:
            warning = " ⚠️ 과소"
        print(f"  {sid} {sdef['name']:12s} ({anchor_str:5s}): {count:4d}개{warning}")

    print(f"  {'─'*45}")
    print(f"  {'합계':18s}: {total:4d}개")

    if total != len(all_tickers):
        print(f"[FAIL] 합계({total}) != 전체({len(all_tickers)})")
        passed = False
    else:
        print(f"[OK] 합계 일치 ({total} = {len(all_tickers)})")

    # 4. 방법별 통계
    from collections import Counter
    method_counts = Counter(info['method'] for info in classification.values())
    print(f"\n--- 분류 방법 통계 ---")
    for method, count in sorted(method_counts.items()):
        print(f"  {method}: {count}개 ({count/len(classification)*100:.1f}%)")

    return passed


def spot_check(classification: dict[str, dict[str, Any]], scraped: dict[str, Any]) -> bool:
    """주요 ETF가 올바른 섹터에 배정되었는지 확인"""
    expected = {
        'VOO': 'S01', 'SPY': 'S01', 'VTI': 'S01',
        'QQQ': 'S02', 'XLK': 'S02', 'SMH': 'S02',
        'XLV': 'S03', 'IBB': 'S03',
        'XLF': 'S04', 'KRE': 'S04',
        'XLY': 'S05',
        'XLP': 'S06',
        'XLI': 'S07',
        'XLU': 'S08',
        'XLC': 'S09',
        'XLB': 'S10',
        'VEA': 'S11', 'IEFA': 'S11', 'EFA': 'S11',
        'VWO': 'S12', 'EEM': 'S12',
        'IWM': 'S13', 'IJR': 'S13',
        'BND': 'S14', 'AGG': 'S14',
        'SHV': 'S15', 'BIL': 'S15', 'SGOV': 'S15',
        'HYG': 'S16', 'JNK': 'S16',
        'SCHP': 'S17', 'TIP': 'S17',
        'GLD': 'S18', 'IAU': 'S18', 'GDX': 'S18',
        'XLE': 'S19', 'AMLP': 'S19',
        'VNQ': 'S20', 'IYR': 'S20',
        'GBTC': 'S21', 'IBIT': 'S21',
        'SQQQ': 'S22', 'SH': 'S22',
    }

    print(f"\n--- 스팟체크 ({len(expected)}개 핵심 ETF) ---")
    failures = 0
    for ticker, expected_sector in expected.items():
        if ticker not in classification:
            print(f"  [SKIP] {ticker} - 상관계수 매트릭스에 없음")
            continue
        actual = classification[ticker]['sector']
        method = classification[ticker]['method']
        if actual != expected_sector:
            fullname = scraped.get(ticker, {}).get('fullname', ticker)
            print(f"  [FAIL] {ticker} ({fullname}): expected {expected_sector}, got {actual} (via {method})")
            failures += 1

    if failures == 0:
        print(f"  [OK] 전체 통과")
    else:
        print(f"  [FAIL] {failures}개 불일치")

    return failures == 0
