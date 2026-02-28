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


if __name__ == '__main__':
    unittest.main(verbosity=2)
