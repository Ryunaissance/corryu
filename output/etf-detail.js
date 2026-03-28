// ── etf-detail.js ────────────────────────────────────────────────────────────
// ETF 상세 페이지 진입점: URL 파싱, 관심종목, 검색, 데이터 로드 부트스트랩
// 의존성 (로드 순서):
//   1. etf-detail-data.js    — SUPP, SECTOR_NAMES, inferIssuer
//   2. etf-detail-charts.js  — 공유 상태 변수, 차트 함수
//   3. etf-detail-render.js  — 포맷 헬퍼, renderPage, loadPriceHistory
//   4. etf-detail.js         — 이 파일 (진입점)
//   5. etf-detail-comments.js — 댓글 + 좋아요 IIFE
// ─────────────────────────────────────────────────────────────────────────────

// ── URL에서 ticker 추출 ────────────────────────────
var params = new URLSearchParams(location.search);
var TICKER = (params.get('ticker') || 'SPY').toUpperCase().trim();

document.getElementById('nav-breadcrumb').textContent = '/ ' + TICKER;
// 백테스트 링크에 현재 티커를 100% 비중으로 프리셋
document.getElementById('nav-backtest-link').href = `/backtest?portfolio=${TICKER}:100`;
document.title = TICKER + ' ETF 상세 — CORRYU';

// ── Watchlist (localStorage) ──────────────────────
var watchlist = new Set(JSON.parse(localStorage.getItem('corryu_watchlist') || '[]'));
function toggleWatchlist() {
  if (watchlist.has(TICKER)) watchlist.delete(TICKER);
  else watchlist.add(TICKER);
  localStorage.setItem('corryu_watchlist', JSON.stringify([...watchlist]));
  updateStarBtn();
}
function updateStarBtn() {
  const btn = document.getElementById('star-hero-btn');
  if (!btn) return;
  if (watchlist.has(TICKER)) {
    btn.textContent = '★ 관심종목';
    btn.classList.add('starred');
  } else {
    btn.textContent = '☆ 관심종목 추가';
    btn.classList.remove('starred');
  }
}

// ── 검색 ─────────────────────────────────────────
document.getElementById('nav-search-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') goToTicker();
});
function goToTicker() {
  const val = document.getElementById('nav-search-input').value.trim().toUpperCase();
  if (val) location.href = '/etf-detail?ticker=' + encodeURIComponent(val);
}

// ── 데이터 로드 ───────────────────────────────────
// i18n 먼저 초기화 (fetch 실패 시 에러 메시지가 번역되도록)
I18n.init();
let _i18nReady = false;
document.addEventListener('i18n:ready', () => { _i18nReady = true; });

function _applyEtfData(found, foundSid) {
  // localStorage 오버라이드 반영 (읽기 전용)
  const ov = JSON.parse(localStorage.getItem('corryu_user_overrides') || '{}');
  if (ov[TICKER]) {
    if ('is_legacy' in ov[TICKER]) found.is_legacy = ov[TICKER].is_legacy;
    if (ov[TICKER].is_legacy) found._user_override = true;
  }
  renderPage(found, foundSid);
  loadPriceHistory(found.ticker).then(hist => {
    if (hist) {
      priceHistory = hist;
      initPriceChart(document.getElementById('chart-container'), hist, currentChartType);
      updatePerfFromHistory();
      buildSubCharts();
    }
  });
  document.addEventListener('i18n:ready', () => {
    if (currentETF) {
      renderPage(currentETF, foundSid);
      if (priceHistory) {
        initPriceChart(document.getElementById('chart-container'), priceHistory, currentChartType);
        updatePerfFromHistory();
        buildSubCharts();
      }
    }
  });
}

function _showNotFound() {
  document.getElementById('loading-state').style.display = 'none';
  document.getElementById('error-title').textContent = '"' + TICKER + '" ' + I18n.t('detail.not.found');
  document.getElementById('error-msg').textContent   = I18n.t('detail.error.notfound.msg');
  document.getElementById('error-state').style.display = 'flex';
}

function _showLoadError() {
  document.getElementById('loading-state').style.display = 'none';
  document.getElementById('error-title').textContent = I18n.t('detail.error.load.title');
  document.getElementById('error-msg').textContent   = I18n.t('detail.error.load.msg');
  document.getElementById('error-state').style.display = 'flex';
}

// 1단계: 티커별 개별 JSON 로드 시도 (빠름 ~400B)
// 2단계: 실패 시 전체 etf_data.json 폴백
// ※ /etf-data/ 경로 사용 — /etf/:ticker rewrite 충돌 방지
fetch('/etf-data/' + TICKER + '.json')
  .then(r => { if (!r.ok) throw new Error('no per-ticker file'); return r.json(); })
  .then(d => { _applyEtfData(d.etf, d.sid); })
  .catch(() =>
    fetch('/etf_data.json')
      .then(r => { if (!r.ok) throw new Error('fetch failed'); return r.json(); })
      .then(data => {
        let found = null, foundSid = null;
        for (const [sid, etfs] of Object.entries(data.allData || data)) {
          if (!Array.isArray(etfs)) continue;
          const e = etfs.find(x => x.ticker === TICKER);
          if (e) { found = e; foundSid = sid; break; }
        }
        if (!found) { _showNotFound(); return; }
        _applyEtfData(found, foundSid);
      })
      .catch(_showLoadError)
  );
