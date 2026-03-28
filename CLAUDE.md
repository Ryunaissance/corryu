# CORRYU — AI 작업 가이드

## 프로젝트 한 줄 요약
1,600개+ ETF를 24개 섹터로 자동 분류하고, 각 섹터별 성과·리스크 지표를 계산해 정적 HTML 대시보드로 배포하는 파이프라인.

---

## 핵심 파일 지도

| 목적 | 파일 | 비고 |
|------|------|------|
| 전역 설정 | `src/config.py` | 섹터 정의, 앵커, 임계값, 오버라이드 — **규칙 변경은 여기서만** |
| 분류 엔진 | `src/classify.py` | 3-pass 워터폴 (앵커→키워드→상관계수) |
| 레거시 판별 | `src/legacy.py` | AUM·기간 기준 자동 판별 + 수동 오버라이드 |
| 지표 계산 | `src/metrics.py` | Z-score, RSI, MDD, 52w 레인지 등 |
| 데이터 로딩 | `src/data_loader.py` | parquet → pandas, 상관계수·성과지표 인라인 계산 |
| 전체 재계산 | `scripts/compute_all.py` | **단일 진입점**: `python scripts/compute_all.py` |
| 초기 다운로드 | `scripts/fetch_initial.py` | 최초 1회: yfinance → `raw/*.parquet` |
| 일별 업데이트 | `scripts/fetch_daily.py` | 매일: 최신 가격·메타 → parquet 추가 |
| ETF 개별 JSON | `build_etf_pages.py` | `etf_data.json` → `output/etf-data/{TICKER}.json` (compute_all.py에서 자동 호출, Vercel 빌드 시에도 실행) |
| 배당률 수집 | `scripts/fetch_dividend_yields.py` | 수동 실행: yfinance → data_scraped/ (필요 시만) |
| 수수료 수집 | `scripts/fetch_expense_ratios.py` | 수동 실행: yfinance → data_scraped/ (필요 시만) |
| DB 스키마 | `supabase/migration.sql` | Supabase SQL Editor에서 최초 1회 실행 |
| HTML 렌더러 | `render_html.py` | 템플릿→HTML 변환, pandas 불필요, 단독 실행 가능 |
| MECE 검증 | `src/verify.py` | 빌드 시 자동 실행, 30개 앵커 스팟체크 포함 |

---

## 데이터 원칙

```
raw/prices_close.parquet  ← 신성불가침, append-only (yfinance 수정종가)
raw/meta.parquet          ← 신성불가침, daily 갱신 (AUM·수수료·배당·상장일)

etf_data.json             ← 항상 완전 재생성 (절대 수동 패치 금지)
config.py 규칙 변경       → compute_all.py 재실행으로 즉시 반영
```

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

추가 규칙:
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
# 최초 1회: 전체 이력 다운로드 (약 1~2시간)
python scripts/fetch_initial.py

# 전체 재계산 (config 변경 후, 또는 수동 실행)
python scripts/compute_all.py

# HTML만 재생성 (etf_data.json 변경 없을 때)
python render_html.py

# 그래프 데이터 재계산
python build_graph.py
```

출력: `output/etf_data.json` (625KB), `output/etf-data/{TICKER}.json` (개별 ETF, 자동 생성), `output/graph_data.json` (2MB), `output/*.html` (13개)

---

## 데이터 흐름

```
yfinance (최초 1회 또는 매일 증분)
  └─ raw/prices_close.parquet  (수정종가, append-only)
  └─ raw/meta.parquet          (AUM·수수료·배당, daily 갱신)

scripts/compute_all.py
  ├─ data_loader.load_price_data()    → df_price
  ├─ data_loader.load_scraped_info()  → scraped
  ├─ data_loader.compute_perf_stats() → perf_stats (CAGR·Vol·Sortino)
  ├─ data_loader.compute_corr_*()     → df_corr_monthly, df_corr_daily
  ├─ classify_all()  → classification dict
  ├─ assess_all_legacy() → legacy_results dict
  ├─ compute_etf_metrics() × N → output/etf_data.json
  │                                   ├─ build_etf_pages.py → output/etf-data/{TICKER}.json (자동 호출)
  │                                   └─ render_html.py → output/*.html
  └─ (완료)
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
    'mdd_52w': -8.2, 'rsi': 58.2,
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
5. `python scripts/compute_all.py` 실행

### 특정 ETF 강제 섹터 배정
1. `src/config.py` → `MANUAL_SECTOR_OVERRIDES`에 `'TICKER': 'S##'` 추가
2. `python scripts/compute_all.py` 실행 (JSON 패치 불필요)

### 특정 ETF 레거시 처리
1. `src/config.py` → `MANUAL_LEGACY_OVERRIDES`에 `'TICKER': '이유'` 추가
2. `python scripts/compute_all.py` 실행

### 내 포트폴리오 종목 변경
1. `src/config.py` → `MY_PORTFOLIO` 리스트 수정
2. `python scripts/compute_all.py` 실행

---

## 배포 구조

- **호스팅**: Vercel (정적 파일: `output/` 디렉토리)
- **서버리스 API**: `api/yf.js` (Yahoo Finance 프록시), `api/sync.js` (사용자 오버라이드 저장)
- **DB**: Supabase (댓글, 투표 — 가격 데이터 제거됨)
- **CI/CD**: GitHub Actions
  - `daily_update.yml`: 평일 UTC 22:00 (ET 17:00), yfinance → parquet → compute_all → commit

---

## 프론트엔드 아키텍처

### JS 모듈화 — Dashboard (4개 파일)

로드 순서가 곧 의존성 순서. **반드시 이 순서대로 로드됨** (`output/index.html` `<script>` 태그 순서 확인).

| 순서 | 파일 | 역할 | 핵심 전역 |
|------|------|------|-----------|
| 1 | `dashboard-state.js` | 전역 상태(`var`), 필터 상태, Admin 로직, 공유 유틸 | `allData`, `currentSector`, `isAdmin` |
| 2 | `dashboard-overrides.js` | localStorage 오버라이드, 섹터 이동 모달, YF API r_anchor 재계산 | — |
| 3 | `dashboard.js` | DataTable 초기화, 컬럼 정의, 탭/필터 이벤트 | — |
| 4 | `dashboard-likes.js` | 좋아요 버튼, 인기 종목 랭킹(IIFE), Supabase Auth | — |

### JS 모듈화 — ETF 상세 페이지 (5개 파일)

`output/etf-detail.html`에서 다음 순서로 로드. **순서 변경 금지**.

| 순서 | 파일 | 역할 | 핵심 전역 |
|------|------|------|-----------|
| 1 | `etf-detail-data.js` | 정적 보조 데이터: `SUPP`, `SECTOR_NAMES`, `inferIssuer()` | `SUPP`, `SECTOR_NAMES` |
| 2 | `etf-detail-charts.js` | 공유 상태 + 차트 함수 (LightweightCharts) | `currentETF`, `priceHistory`, `lwChart`, `currentChartType`, `activeIndicators` |
| 3 | `etf-detail-render.js` | 포맷 헬퍼, `renderPage()`, `loadPriceHistory()`, `updatePerfFromHistory()` | — |
| 4 | `etf-detail.js` | 진입점: URL 파싱, 관심종목, 검색, 데이터 fetch 부트스트랩 | `TICKER`, `watchlist` |
| 5 | `etf-detail-comments.js` | 댓글 CRUD + 좋아요 (두 개의 IIFE) | — |

### ⚠️ 크로스 파일 전역 변수 패턴

여러 스크립트 파일에서 공유해야 하는 변수는 반드시 **`var`** 로 선언해야 함.

```javascript
// ✅ 올바름 — window 프로퍼티가 되어 다른 파일에서 접근 가능
var currentETF = null;
var priceHistory = null;

// ❌ 잘못됨 — 모듈 스코프에 갇혀 다른 script 파일에서 접근 불가
let currentETF = null;   // 다른 파일에서 ReferenceError
const TICKER = 'SPY';    // 다른 파일에서 ReferenceError
```

이 프로젝트는 번들러 없이 vanilla JS 멀티 파일 구조이므로 공유 상태는 `var` 필수.
함수·객체 등 불변 선언도 마찬가지 (`var` 또는 `window.XXX = ...` 패턴).

### 네비게이션 (DRY — 단일 진실의 원천)

- `nav.js`의 `allLinks` 배열이 **모든 페이지 메뉴의 유일한 원천**.
- 메뉴 추가/변경은 `allLinks`만 수정하면 데스크탑·모바일 드로어 모두 자동 반영.
- 모바일 드로어(`nav-mob-drawer`)는 **HTML에 하드코딩하지 말 것** — `nav.js`의 `injectMobileDrawer()`가 런타임에 동적 생성.
- HTML의 `nav-mob-drawer` div는 항상 빈 채로 두거나 주석만:
  ```html
  <div id="nav-mob-drawer" class="nav-mob-drawer">
    <!-- nav.js의 injectMobileDrawer()가 allLinks 배열로 동적 생성 -->
  </div>
  ```

### Supabase 인증 클라이언트 (`output/supabase-client.js`)

```javascript
const SUPABASE_URL = 'https://pksehljuhuowmhzgetxp.supabase.co';
const SUPABASE_KEY = 'sb_publishable_...';
```

**하드코딩이 의도적이며 올바름.** anon (publishable) key는 브라우저 노출용으로 설계된 공개 키이며, 보안은 Supabase RLS(Row Level Security) 정책으로 보장됨. 환경변수로 바꾸지 말 것. 참고: https://supabase.com/docs/guides/api/api-keys

### CSS 구조

| 파일 | 역할 |
|------|------|
| `responsive.css` | 레이아웃, 글래스모피즘, 네비게이션, 모바일 드로어 공통 스타일 |
| `dashboard.css` | DataTable 커스텀, 통계 카드, FAB (대시보드 전용) |
| 인라인 `<style>` | 각 페이지 전용 스타일 — CSS 변수(`var(--bg)` 등) 참조 권장 |

---

## 주의사항

- `render_html.py`는 pandas 없이 동작 — `src/` 모듈과 독립적
- `PROTECT_EQUITIES` 수정 시 분류 결과 전체에 영향, 반드시 `spot_check()` 확인
- `graph_data.json`은 2MB로 크기가 큼 — 그래프 관련 코드 수정 후 `build_graph.py` 재실행 필요
- 레거시 면제(`LEGACY_EXEMPTIONS`)는 앵커 ETF 자동 생성 — 직접 수정 불필요
- 섹터 S23(레버리지 롱)은 폐지됨 — 레버리지 상품은 기초자산 섹터로 상관계수 분류
- `raw/` 파일은 Git에 포함 (~10MB parquet) — GitHub Actions에서 자동 commit·push
