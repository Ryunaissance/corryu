"""
CORRYU 스모크 테스트 — 외부 데이터(Supabase) 없이 실행 가능
커버 범위: config 무결성, 키워드 분류, 지표 수식, 레거시 불변식

실행:
    python tests/test_smoke.py
    python -m pytest tests/test_smoke.py -v
"""
import sys
import os
import unittest

import numpy as np
import pandas as pd

# src/ 모듈 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# render_html.py 경로 추가 (루트)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import (
    SECTOR_DEFS, ANCHOR_TO_SECTOR, ASSET_CLASSES,
    SUPER_SECTOR_DEFS, MANUAL_SECTOR_OVERRIDES,
    MANUAL_LEGACY_OVERRIDES, LEGACY_EXEMPTIONS,
    KEYWORD_RULES,
)
from classify import classify_by_keywords
from metrics import (
    compute_z_score, compute_rsi,
    compute_52w_mdd, compute_52w_range_pct,
)


# ─────────────────────────────────────────────────────────
# 1. config.py 무결성
# ─────────────────────────────────────────────────────────

class TestConfigIntegrity(unittest.TestCase):

    def test_sector_ids_format(self):
        """모든 섹터 ID가 'S##' 형식인지 확인"""
        for sid in SECTOR_DEFS:
            self.assertRegex(sid, r'^S\d{2}$', f"잘못된 섹터 ID: {sid}")

    def test_anchor_to_sector_reverse_mapping(self):
        """ANCHOR_TO_SECTOR가 SECTOR_DEFS와 일치하는지 확인"""
        for anchor, sid in ANCHOR_TO_SECTOR.items():
            self.assertIn(sid, SECTOR_DEFS, f"{anchor} 앵커의 섹터 {sid}가 SECTOR_DEFS에 없음")
            self.assertEqual(
                SECTOR_DEFS[sid]['anchor'], anchor,
                f"역방향 매핑 불일치: {anchor} → {sid}"
            )

    def test_anchor_uniqueness(self):
        """앵커 ETF가 중복 없이 고유한지 확인"""
        anchors = [s['anchor'] for s in SECTOR_DEFS.values() if s['anchor']]
        self.assertEqual(len(anchors), len(set(anchors)), "중복 앵커 발견")

    def test_asset_classes_valid(self):
        """모든 섹터의 asset_class가 ASSET_CLASSES에 정의된 값인지 확인"""
        valid = set(ASSET_CLASSES.keys())
        for sid, sdef in SECTOR_DEFS.items():
            self.assertIn(sdef['asset_class'], valid, f"{sid} asset_class 오류")

    def test_manual_sector_overrides_valid_sectors(self):
        """MANUAL_SECTOR_OVERRIDES의 값이 모두 유효한 섹터 ID인지 확인"""
        for ticker, sid in MANUAL_SECTOR_OVERRIDES.items():
            self.assertIn(sid, SECTOR_DEFS, f"MANUAL_SECTOR_OVERRIDES[{ticker}]={sid} 유효하지 않음")

    def test_super_sector_sub_sectors_exist(self):
        """슈퍼섹터의 sub_sectors가 모두 SECTOR_DEFS에 있는지 확인"""
        for ss_name, ss_def in SUPER_SECTOR_DEFS.items():
            for sid in ss_def['sub_sectors']:
                self.assertIn(sid, SECTOR_DEFS, f"슈퍼섹터 {ss_name}의 sub_sector {sid}가 없음")

    def test_anchor_etfs_not_in_manual_legacy(self):
        """앵커 ETF가 MANUAL_LEGACY_OVERRIDES에 포함되지 않아야 함"""
        all_anchors = {s['anchor'] for s in SECTOR_DEFS.values() if s['anchor']}
        overlap = all_anchors & set(MANUAL_LEGACY_OVERRIDES.keys())
        self.assertEqual(overlap, set(), f"앵커 ETF가 레거시 오버라이드에 포함됨: {overlap}")

    def test_anchor_etfs_in_legacy_exemptions(self):
        """앵커 ETF가 레거시 면제 목록에 있어야 함"""
        all_anchors = {s['anchor'] for s in SECTOR_DEFS.values() if s['anchor']}
        missing = all_anchors - LEGACY_EXEMPTIONS
        self.assertEqual(missing, set(), f"앵커 ETF가 LEGACY_EXEMPTIONS에 없음: {missing}")

    def test_keyword_rules_sectors_exist(self):
        """KEYWORD_RULES의 섹터 키가 모두 SECTOR_DEFS에 있는지 확인"""
        for sid in KEYWORD_RULES:
            self.assertIn(sid, SECTOR_DEFS, f"KEYWORD_RULES의 섹터 {sid}가 SECTOR_DEFS에 없음")


# ─────────────────────────────────────────────────────────
# 2. classify_by_keywords — 데이터 없이 테스트 가능
# ─────────────────────────────────────────────────────────

class TestKeywordClassification(unittest.TestCase):

    def _classify(self, ticker, name):
        return classify_by_keywords(ticker, name)

    # 인버스/숏 (S22)
    def test_inverse_by_ticker(self):
        self.assertEqual(self._classify('SQQQ', 'ProShares UltraPro Short QQQ'), 'S22')

    def test_inverse_by_keyword(self):
        self.assertEqual(self._classify('XINV', 'Direxion Daily S&P 500 Bear 3X ETF'), 'S22')

    def test_vix_etf_is_inverse(self):
        self.assertEqual(self._classify('VXX', 'iPath Series B S&P 500 VIX Short-Term Futures ETN'), 'S22')

    def test_short_term_bond_not_inverse(self):
        """단기채 키워드가 있으면 S22에서 제외되어야 함"""
        result = self._classify('XSHT', 'ProShares Short Term Treasury ETF')
        self.assertNotEqual(result, 'S22', "단기채 ETF가 인버스로 잘못 분류됨")

    # 가상자산 (S21)
    def test_bitcoin_by_ticker(self):
        self.assertEqual(self._classify('IBIT', 'iShares Bitcoin Trust'), 'S21')

    def test_crypto_by_keyword(self):
        self.assertEqual(self._classify('XBTC', 'Some Bitcoin Fund ETF'), 'S21')

    # 금/귀금속 (S18)
    def test_gold_by_ticker(self):
        self.assertEqual(self._classify('GLD', 'SPDR Gold Shares'), 'S18')

    def test_gold_by_keyword(self):
        self.assertEqual(self._classify('XGLD', 'Aberdeen Physical Gold Shares ETF'), 'S18')

    def test_goldman_not_gold(self):
        """Goldman Sachs ETF가 금으로 잘못 분류되면 안 됨"""
        result = self._classify('XGSB', 'Goldman Sachs Access Investment Grade Bond ETF')
        self.assertNotEqual(result, 'S18', "Goldman Sachs ETF가 금으로 분류됨")

    # REITs (S20)
    def test_reit_by_keyword(self):
        self.assertEqual(self._classify('XREI', 'Vanguard Real Estate ETF'), 'S20')

    # 단기채 (S15)
    def test_short_term_bond_by_ticker(self):
        self.assertEqual(self._classify('SHV', 'iShares Short Treasury Bond ETF'), 'S15')

    def test_short_term_bond_by_keyword(self):
        self.assertEqual(self._classify('XMNY', 'Invesco Treasury Money Market ETF'), 'S15')

    # TIPS (S17)
    def test_tips_by_ticker(self):
        self.assertEqual(self._classify('TIP', 'iShares TIPS Bond ETF'), 'S17')

    # 하이일드 (S16)
    def test_high_yield_by_ticker(self):
        self.assertEqual(self._classify('HYG', 'iShares iBoxx High Yield Corporate Bond ETF'), 'S16')

    def test_high_yield_by_keyword(self):
        self.assertEqual(self._classify('XHJY', 'PGIM US High-Yield ETF'), 'S16')

    # 분류 불가 → None (상관계수 pass로 넘어가야 함)
    def test_unknown_etf_returns_none(self):
        result = self._classify('XUNKNOWN', 'Some Generic Multi-Asset Fund ETF')
        self.assertIsNone(result, "알 수 없는 ETF가 None이 아닌 섹터로 분류됨")


# ─────────────────────────────────────────────────────────
# 3. metrics.py — 순수 수식 테스트
# ─────────────────────────────────────────────────────────

class TestMetrics(unittest.TestCase):

    def _make_series(self, values):
        return pd.Series(values, dtype=float)

    # compute_z_score
    def test_z_score_short_series_returns_zero(self):
        """데이터 < 200개면 0.0 반환"""
        ts = self._make_series(range(100))
        self.assertEqual(compute_z_score(ts), 0.0)

    def test_z_score_above_ma_is_positive(self):
        """현재가가 200일 평균 위 → Z-score 양수"""
        # 200개 기준값 + 급등한 최근값
        base = [100.0] * 200
        base[-1] = 150.0
        ts = self._make_series(base)
        self.assertGreater(compute_z_score(ts), 0.0)

    def test_z_score_below_ma_is_negative(self):
        """현재가가 200일 평균 아래 → Z-score 음수"""
        base = [100.0] * 200
        base[-1] = 50.0
        ts = self._make_series(base)
        self.assertLess(compute_z_score(ts), 0.0)

    # compute_rsi
    def test_rsi_short_series_returns_none(self):
        """데이터 < 15개면 None 반환"""
        ts = self._make_series(range(10))
        self.assertIsNone(compute_rsi(ts))

    def test_rsi_all_up_near_100(self):
        """대부분 상승(+1), 간헐적 소폭 하락(-0.1) → RSI 높음 (>70)"""
        # 완벽 직선이면 avg_loss=0 → NaN이므로 작은 변동 포함
        values = [100.0]
        for i in range(49):
            values.append(values[-1] - 0.1 if i % 5 == 4 else values[-1] + 1.0)
        ts = self._make_series(values)
        rsi = compute_rsi(ts)
        self.assertIsNotNone(rsi)
        self.assertGreater(rsi, 70.0)

    def test_rsi_all_down_near_0(self):
        """계속 하락하는 시리즈 → RSI 낮음 (<30)"""
        ts = self._make_series([float(50 - i) for i in range(50)])
        rsi = compute_rsi(ts)
        self.assertIsNotNone(rsi)
        self.assertLess(rsi, 30.0)

    def test_rsi_range_0_to_100(self):
        """RSI는 항상 0~100 범위"""
        np.random.seed(42)
        ts = self._make_series(np.random.randn(100).cumsum() + 100)
        rsi = compute_rsi(ts)
        if rsi is not None:
            self.assertGreaterEqual(rsi, 0.0)
            self.assertLessEqual(rsi, 100.0)

    # compute_52w_mdd
    def test_mdd_at_52w_high_is_zero(self):
        """현재가 = 52주 최고가 → MDD = 0.0"""
        ts = self._make_series([90.0, 95.0, 100.0])
        self.assertEqual(compute_52w_mdd(ts), 0.0)

    def test_mdd_below_52w_high_is_negative(self):
        """현재가 < 52주 최고가 → MDD 음수"""
        ts = self._make_series([100.0] * 10 + [80.0])
        mdd = compute_52w_mdd(ts)
        self.assertLess(mdd, 0.0)

    def test_mdd_short_series_returns_zero(self):
        """데이터 < 10개면 0.0 반환"""
        ts = self._make_series([100.0] * 5)
        self.assertEqual(compute_52w_mdd(ts), 0.0)

    # compute_52w_range_pct
    def test_range_pct_at_high_is_100(self):
        """현재가 = 52주 최고 → 100.0 (len >= 10 필요)"""
        ts = self._make_series([50.0] * 8 + [60.0, 100.0])
        self.assertEqual(compute_52w_range_pct(ts), 100.0)

    def test_range_pct_at_low_is_0(self):
        """현재가 = 52주 최저 → 0.0 (len >= 10 필요)"""
        ts = self._make_series([100.0] * 8 + [80.0, 50.0])
        self.assertEqual(compute_52w_range_pct(ts), 0.0)

    def test_range_pct_midpoint_is_50(self):
        """현재가 = 52주 중간 → 50.0 (len >= 10 필요)"""
        ts = self._make_series([0.0] * 8 + [100.0, 50.0])
        self.assertEqual(compute_52w_range_pct(ts), 50.0)

    def test_range_pct_short_series_returns_none(self):
        """데이터 < 10개면 None 반환"""
        ts = self._make_series([100.0] * 5)
        self.assertIsNone(compute_52w_range_pct(ts))


# ─────────────────────────────────────────────────────────
# 4. classify_all() 워터폴 — 오프라인 분류 로직 검증
# ─────────────────────────────────────────────────────────

def _make_corr_df(tickers: list[str], pairs: dict | None = None) -> pd.DataFrame:
    """테스트용 상관계수 매트릭스 생성.

    pairs: {(t1, t2): r} 형태로 특정 쌍에 상관계수 지정 (기본 0.0)
    대각선은 항상 1.0.
    """
    n = len(tickers)
    data = np.zeros((n, n))
    np.fill_diagonal(data, 1.0)
    df = pd.DataFrame(data, index=tickers, columns=tickers)
    if pairs:
        for (t1, t2), r in pairs.items():
            if t1 in df.index and t2 in df.columns:
                df.loc[t1, t2] = r
                df.loc[t2, t1] = r
    return df


class TestClassifyAll(unittest.TestCase):
    """classify_all() 3-Pass 워터폴 오프라인 테스트"""

    from classify import classify_all  # noqa: F401

    def _run(self, tickers: set, scraped: dict, pairs: dict | None = None) -> dict:
        from classify import classify_all
        ticker_list = list(tickers) + ['VOO', 'GLD', 'XLK']  # 앵커 포함 보장
        df = _make_corr_df(ticker_list, pairs)
        return classify_all(tickers, scraped, df, df)

    # ── Pass 0: 앵커 ──────────────────────────────────────

    def test_anchor_etf_method_is_anchor(self):
        """앵커 ETF는 Pass 0에서 method='anchor'로 즉시 배정"""
        from config import ANCHOR_TO_SECTOR
        result = self._run({'VOO'}, {})
        self.assertEqual(result['VOO']['method'], 'anchor')
        self.assertEqual(result['VOO']['r_anchor'], 1.0)
        self.assertEqual(result['VOO']['sector'], ANCHOR_TO_SECTOR['VOO'])

    def test_all_anchors_classified_as_anchor(self):
        """모든 앵커 ETF가 method='anchor'로 분류됨"""
        from config import ANCHOR_TO_SECTOR
        result = self._run(set(ANCHOR_TO_SECTOR.keys()), {})
        for ticker in ANCHOR_TO_SECTOR:
            with self.subTest(ticker=ticker):
                self.assertEqual(result[ticker]['method'], 'anchor')

    # ── Pass 0.5: 수동 오버라이드 ─────────────────────────

    def test_manual_override_takes_priority_over_keyword(self):
        """MANUAL_SECTOR_OVERRIDES는 키워드보다 우선"""
        from config import MANUAL_SECTOR_OVERRIDES, ANCHOR_TO_SECTOR
        # 앵커가 아닌 오버라이드 티커 선택
        candidates = [t for t in MANUAL_SECTOR_OVERRIDES if t not in ANCHOR_TO_SECTOR]
        self.assertTrue(candidates, "오버라이드 비앵커 후보 없음")
        ticker = candidates[0]
        expected = MANUAL_SECTOR_OVERRIDES[ticker]
        result = self._run({ticker}, {ticker: {'fullname': 'bitcoin crypto gold etf'}})
        self.assertEqual(result[ticker]['method'], 'manual_override')
        self.assertEqual(result[ticker]['sector'], expected)

    # ── Pass 1: 키워드 ────────────────────────────────────

    def test_keyword_classifies_gold_etf(self):
        """'Gold' 포함 ETF는 키워드로 S18 분류"""
        ticker = 'XGOLDTEST'
        scraped = {ticker: {'fullname': 'Aberdeen Physical Gold Shares ETF'}}
        result = self._run({ticker}, scraped)
        self.assertEqual(result[ticker]['sector'], 'S18')
        self.assertEqual(result[ticker]['method'], 'keyword')

    def test_keyword_classifies_bitcoin_etf(self):
        """'Bitcoin' 포함 ETF는 키워드로 S21 분류"""
        ticker = 'XBTCTEST'
        scraped = {ticker: {'fullname': 'iShares Bitcoin Trust ETF'}}
        result = self._run({ticker}, scraped)
        self.assertEqual(result[ticker]['sector'], 'S21')
        self.assertEqual(result[ticker]['method'], 'keyword')

    def test_keyword_classifies_inverse_etf(self):
        """'Bear' 포함 인버스 ETF는 키워드로 S22 분류"""
        ticker = 'XBEARTEST'
        scraped = {ticker: {'fullname': 'Direxion Daily S&P 500 Bear 3X ETF'}}
        result = self._run({ticker}, scraped)
        self.assertEqual(result[ticker]['sector'], 'S22')
        self.assertEqual(result[ticker]['method'], 'keyword')

    # ── Pass 2: 상관계수 ─────────────────────────────────

    def test_high_correlation_to_voo_classifies_as_s01(self):
        """VOO와 상관계수 >= 0.55이면 S01으로 분류"""
        from config import CORR_THRESHOLD
        ticker = 'XSPYTEST'
        result = self._run({ticker}, {}, pairs={('VOO', ticker): CORR_THRESHOLD + 0.1})
        self.assertEqual(result[ticker]['sector'], 'S01')
        self.assertEqual(result[ticker]['method'], 'correlation')
        self.assertGreaterEqual(result[ticker]['r_anchor'], CORR_THRESHOLD)

    def test_correlation_result_has_r_anchor(self):
        """상관계수 분류 결과는 r_anchor >= CORR_THRESHOLD"""
        from config import CORR_THRESHOLD
        ticker = 'XSPYTEST2'
        result = self._run({ticker}, {}, pairs={('VOO', ticker): 0.75})
        self.assertGreaterEqual(result[ticker]['r_anchor'], CORR_THRESHOLD)

    # ── Pass 3: Fallback ──────────────────────────────────

    def test_no_corr_data_falls_to_s24(self):
        """상관계수 데이터 없는 티커는 S24(테마) fallback"""
        from classify import classify_all
        ticker = 'ZZUNKNOWN9'
        # 빈 상관계수 매트릭스 — 테스트 티커 미포함
        df_empty = _make_corr_df(['VOO', 'GLD'])
        result = classify_all({ticker}, {}, df_empty, df_empty)
        self.assertEqual(result[ticker]['sector'], 'S24')
        self.assertEqual(result[ticker]['method'], 'fallback')

    def test_below_threshold_falls_to_s24(self):
        """CORR_THRESHOLD 미만 상관계수 → S24 fallback"""
        from config import CORR_THRESHOLD
        ticker = 'XLOWCORRTEST'
        result = self._run({ticker}, {}, pairs={('VOO', ticker): CORR_THRESHOLD - 0.1})
        self.assertEqual(result[ticker]['sector'], 'S24')

    # ── PROTECT_EQUITIES ──────────────────────────────────

    def test_protect_equities_not_pulled_to_gold(self):
        """PROTECT_EQUITIES 티커는 GLD(비주식) 앵커로 끌려가지 않음"""
        from config import PROTECT_EQUITIES, ANCHOR_TO_SECTOR
        # 앵커가 아닌 PROTECT_EQUITIES 티커 선택
        candidates = [t for t in PROTECT_EQUITIES if t not in ANCHOR_TO_SECTOR]
        self.assertTrue(candidates)
        ticker = candidates[0]
        # GLD와만 높은 상관계수, VOO와는 0.0
        result = self._run({ticker}, {}, pairs={('GLD', ticker): 0.95})
        self.assertNotEqual(result[ticker]['sector'], 'S18',
                            f"{ticker}이 PROTECT_EQUITIES임에도 금 섹터로 분류됨")


# ─────────────────────────────────────────────────────────
# 5. render_html.py — generate_html() 구조 테스트
# ─────────────────────────────────────────────────────────

def _make_sector_meta() -> dict:
    """테스트용 최소 sector_meta 픽스처 (SECTOR_DEFS 기반 자동 생성)"""
    from config import SECTOR_DEFS
    meta = {}
    for sid, sdef in SECTOR_DEFS.items():
        meta[sid] = {
            'count': 10, 'active': 8, 'legacy': 2,
            'avg_cagr': 10.0, 'avg_vol': 15.0, 'avg_sortino': 1.5,
            'name': sdef['name'],
            'name_en': sdef['name_en'],
            'asset_class': sdef['asset_class'],
            'anchor': sdef['anchor'] or '—',
            'icon': sdef['icon'],
            'super_sector': sdef.get('super_sector'),
        }
    return meta


class TestRenderHtml(unittest.TestCase):
    """render_html.generate_html() 구조적 무결성 테스트 (외부 파일 불필요)"""

    @classmethod
    def setUpClass(cls):
        from render_html import generate_html
        cls.html = generate_html(_make_sector_meta())

    def test_returns_string(self):
        """generate_html()은 str을 반환해야 함"""
        self.assertIsInstance(self.html, str)

    def test_starts_with_doctype(self):
        """유효한 HTML5 문서 선언으로 시작"""
        self.assertTrue(self.html.strip().startswith('<!DOCTYPE html>'))

    def test_ends_with_html_tag(self):
        """</html> 태그로 종료"""
        self.assertTrue(self.html.strip().endswith('</html>'))

    def test_contains_all_sector_ids(self):
        """24개 섹터 ID가 모두 HTML에 포함됨"""
        from config import SECTOR_DEFS
        for sid in SECTOR_DEFS:
            self.assertIn(sid, self.html, f"섹터 ID {sid}가 HTML에 없음")

    def test_contains_asset_class_keys(self):
        """자산군 키(EQUITY, FIXED_INCOME 등)가 HTML에 포함됨"""
        from config import ASSET_CLASSES
        for ac in ASSET_CLASSES:
            self.assertIn(ac, self.html, f"자산군 {ac}가 HTML에 없음")

    def test_contains_anchor_tickers(self):
        """앵커 티커(VOO, GLD 등)가 HTML에 포함됨"""
        from config import ANCHOR_TO_SECTOR
        for anchor in ANCHOR_TO_SECTOR:
            self.assertIn(anchor, self.html, f"앵커 티커 {anchor}가 HTML에 없음")

    def test_no_unclosed_script_tags(self):
        """<script> 태그 개수 == </script> 태그 개수"""
        opens = self.html.count('<script')
        closes = self.html.count('</script>')
        self.assertEqual(opens, closes, f"script 태그 불균형: {opens} open vs {closes} close")

    def test_etf_data_json_fetch_present(self):
        """클라이언트가 etf_data.json을 fetch하는 코드가 존재"""
        self.assertIn("etf_data.json", self.html)

    def test_summary_counts_nonzero(self):
        """총 ETF 수 / Active 수가 HTML에 숫자로 렌더링됨 (10 × 24 섹터 = 240)"""
        from config import SECTOR_DEFS
        total = 10 * len(SECTOR_DEFS)
        self.assertIn(str(total), self.html, "총 ETF 수가 HTML에 없음")


if __name__ == '__main__':
    unittest.main(verbosity=2)
