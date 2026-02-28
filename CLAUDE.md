# CORRYU — AI 작업 가이드

## 프로젝트 한 줄 요약
1,600개+ ETF를 24개 섹터로 자동 분류하고, 각 섹터별 성과·리스크 지표를 계산해 정적 HTML 대시보드로 배포하는 파이프라인.

---

## 핵심 파일 지도

| 목적 | 파일 | 비고 |
|------|------|------|
| 전역 설정 | `src/config.py` | 섹터 정의, 앵커, 임계값, 오버라이드 — **규칙 변경은 여기서만** |
| 분류 엔진 | `src/classify.py` | 3-pass 워터폴 (앵커→키워드→상관계수) |
| 레거시 판별 | `src/legacy.py` | AUM·기간·중복 기준 자동 판별 + 수동 오버라이드 |
| 지표 계산 | `src/metrics.py` | Z-score, RSI, MDD, 52w 레인지 등 |
| 데이터 로딩 | `src/data_loader.py` | Supabase → pandas DataFrame |
| 빌드 오케스트레이터 | `src/dashboard_builder.py` | 단일 진입점: `python src/dashboard_builder.py` |
| HTML 렌더러 | `render_html.py` | 템플릿→HTML 변환, pandas 불필요, 단독 실행 가능 |
| MECE 검증 | `src/verify.py` | 빌드 시 자동 실행, 30개 앵커 스팟체크 포함 |

---

## 섹터 구조 (24개)

```
EQUITY (13)      S01–S13  앵커: VOO, XLK, XLV, XLF, XLY, XLP, XLI, XLU, XLC, XLB, VEA, VWO, IWM
FIXED_INCOME (4) S14–S17  앵커: BND, SHV, HYG, SCHP
REAL_ASSETS (3)  S18–S20  앵커: GLD, XLE, VNQ
ALTERNATIVE (2)  S21–S22  앵커: GBTC, SQQQ
THEMATIC (1)     S24      앵커 없음
```

슈퍼섹터 `EQUITY_MARKET` = S01, S02, S04, S07, S09, S11, S13 (QQQ 앵커로 r_anchor 재계산)

---

## 분류 3-pass 로직

```
Pass 0   앵커 ETF → 자기 섹터 (r_anchor=1.0, method='anchor')
Pass 0.5 MANUAL_SECTOR_OVERRIDES 적용 (우라늄 6종 등)
Pass 1   KEYWORD_RULES 텍스트 매칭 (인버스, 크립토, TIPS, 단기채, 하이일드, REITs, 금)
Pass 2   월간 상관계수 >= 0.55 → 가장 높은 섹터
Pass 3   일간 상관계수 폴백
없으면   S24(테마)
```

**PROTECT_EQUITIES**: VOO, QQQ 등 핵심 주식 ETF는 비주식 앵커에 끌려가지 않도록 보호.

---

## 레거시 판별 기준

자동 레거시 처리 조건 (하나라도 해당):
- 상장일 > `2021-05-20` (약 3년 미만)
- AUM < $100M
- 거래일 < 750일

추가 규칙:
- 같은 섹터 내 AUM 상위 20개 중 r ≥ 0.95인 중복 ETF
- `MANUAL_LEGACY_OVERRIDES` 명시 항목 (290개+)

면제: `LEGACY_EXEMPTIONS` = 모든 앵커 ETF 자동 면제

---

## 스모크 테스트

외부 데이터(Supabase) 없이 실행 가능. AI 수정 후 항상 실행할 것.

```bash
python tests/test_smoke.py
```

커버 범위 (39개 테스트, ~0.01초):
- **config 무결성**: 섹터 ID 형식, 앵커 역방향 매핑, 오버라이드 유효성, 슈퍼섹터 일관성
- **키워드 분류**: SQQQ→S22, IBIT→S21, GLD→S18, Goldman Sachs→NOT S18 (exclude_if), 단기채→NOT S22
- **지표 수식**: Z-score 부호, RSI 범위(0~100)/경계, MDD 부호, 52w 레인지 0·50·100%

---

## 빌드 파이프라인

```bash
# 전체 빌드 (분류 + 지표 + HTML)
cd src && python dashboard_builder.py

# HTML만 재생성 (데이터 변경 없을 때)
python render_html.py

# 그래프 데이터 재계산
python build_graph.py

# 상관계수 행렬 업데이트
python build_monthly_corr.py

# r_anchor 패치 (슈퍼섹터 QQQ 기준 재계산)
python patch_r_anchor_qqq.py
```

출력: `output/etf_data.json` (625KB), `output/graph_data.json` (2MB), `output/*.html` (13개)

---

## 데이터 흐름

```
Supabase (가격 이력)
  └─ data_loader.load_all()
       └─ df_price, perf_stats, scraped, df_corr_monthly, df_corr_daily
            └─ classify_all() → classification dict
            └─ assess_all_legacy() → legacy_results dict
            └─ compute_etf_metrics() × N → all_etf_data dict
                 └─ output/etf_data.json
                      └─ render_html.py → output/*.html
```

---

## 핵심 데이터 구조

```python
# classification[ticker]
{
    'sector': 'S01',
    'method': 'anchor' | 'manual_override' | 'keyword' | 'correlation' | 'fallback',
    'r_anchor': 0.87,
}

# all_etf_data[sector_id][i]
{
    'ticker': 'VOO',
    'name': 'Vanguard S&P 500 ETF',
    'cagr': 12.5, 'vol': 16.3, 'sortino': 2.15,
    'mdd': -33.7, 'rsi': 58.2,
    'is_legacy': False, 'mine': 1,
    'rank': 1,    # AUM 순위
}
```

---

## 자주 하는 수정 작업

### 섹터 추가/변경
1. `src/config.py` → `SECTOR_DEFS`에 섹터 추가
2. 앵커 ETF가 있으면 `ANCHOR_TO_SECTOR`는 자동 업데이트됨
3. 키워드 규칙이 필요하면 `KEYWORD_RULES`에 추가
4. `src/verify.py` → `spot_check()` expected dict 업데이트

### 특정 ETF 강제 섹터 배정
`src/config.py` → `MANUAL_SECTOR_OVERRIDES`에 `'TICKER': 'S##'` 추가

### 특정 ETF 레거시 처리
`src/config.py` → `MANUAL_LEGACY_OVERRIDES`에 `'TICKER': '이유'` 추가

### 내 포트폴리오 종목 변경
`src/config.py` → `MY_PORTFOLIO` 리스트 수정

---

## 배포 구조

- **호스팅**: Vercel (정적 파일: `output/` 디렉토리)
- **서버리스 API**: `api/yf.js` (Yahoo Finance 프록시), `api/sync.js` (사용자 오버라이드 저장)
- **DB**: Supabase (가격 이력, 댓글, 투표)
- **CI/CD**: GitHub Actions
  - `daily_price_update.yml`: 평일 오전 6시 UTC, Supabase 가격 갱신
  - `patch_r_anchor.yml`: 상관계수 메트릭 업데이트

---

## 주의사항

- `render_html.py`는 pandas 없이 동작 — `src/` 모듈과 독립적
- `PROTECT_EQUITIES` 수정 시 분류 결과 전체에 영향, 반드시 `spot_check()` 확인
- `graph_data.json`은 2MB로 크기가 큼 — 그래프 관련 코드 수정 후 `build_graph.py` 재실행 필요
- 레거시 면제(`LEGACY_EXEMPTIONS`)는 앵커 ETF 자동 생성 — 직접 수정 불필요
- 섹터 S23(레버리지 롱)은 폐지됨 — 레버리지 상품은 기초자산 섹터로 상관계수 분류
