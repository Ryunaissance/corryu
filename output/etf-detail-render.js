// ── etf-detail-render.js ─────────────────────────────────────────────────────
// 렌더링 모듈: 포맷 헬퍼 + 가격 이력 로드 + 수익률 계산 + renderPage
// 의존성: etf-detail-data.js (SUPP, SECTOR_NAMES, inferIssuer)
//         etf-detail-charts.js (공유 상태, initPriceChart, buildSubCharts)
// ─────────────────────────────────────────────────────────────────────────────

// ── 포맷 헬퍼 ────────────────────────────────────────────────────────────────
function fmtAUM(v) {
  if (!v) return '—';
  const m = v / 1e6;
  return m >= 1000 ? '$' + (m/1000).toFixed(1) + 'B' : '$' + Math.round(m) + 'M';
}
function fmtPct(v, dec=1) {
  if (v === null || v === undefined) return '—';
  return (v > 0 ? '+' : '') + v.toFixed(dec) + '%';
}
function fmtNum(v, dec=2) {
  if (v === null || v === undefined) return '—';
  return v.toFixed(dec);
}
function fmtExpRatio(v) {
  if (v === null || v === undefined) return '';
  // v는 소수 형식 (예: 0.0003 → "0.03%")
  const pct = v * 100;
  return pct < 0.01 ? pct.toFixed(4) + '%' : pct.toFixed(2) + '%';
}
function metricColor(key, val) {
  if (val === null || val === undefined) return 'val-neutral';
  if (key === 'z_score')   return val <= -1.5 ? 'val-neg' : val >= 2.0 ? 'val-pos' : 'val-neutral';
  if (key === 'rsi')       return val <= 30 ? 'val-neg' : val >= 70 ? 'val-pos' : 'val-neutral';
  if (key === 'range_52w') return val <= 20 ? 'val-neg' : val >= 80 ? 'val-pos' : 'val-neutral';
  if (key === 'ma200_pct') return val <= -10 ? 'val-neg' : val >= 15 ? 'val-pos' : 'val-neutral';
  if (key === 'mdd_52w')   return val <= -20 ? 'val-pos' : 'val-neutral';
  if (key === 'cagr')      return val >= 15 ? 'val-good' : val < 0 ? 'val-pos' : 'val-neutral';
  if (key === 'sortino')   return val >= 1.2 ? 'val-purple' : val < 0 ? 'val-pos' : 'val-neutral';
  if (key === 'r_anchor')  return Math.abs(val) >= 0.7 ? 'val-pos' : 'val-neutral';
  return 'val-neutral';
}

function renderGauge(val, min, max, color) {
  const pct = Math.max(0, Math.min(100, ((val - min) / (max - min)) * 100));
  return `<div class="gauge-wrap"><div class="gauge-bar"><div class="gauge-fill" style="width:${pct.toFixed(1)}%;background:${color}"></div></div></div>`;
}

// ── 실가격 이력 로드 (Supabase etf_prices, 페이지네이션으로 전체 이력) ─────────
async function loadPriceHistory(ticker) {
  if (!window._sb) return null;
  const PAGE = 1000;
  let all = [], page = 0;
  while (true) {
    const from = page * PAGE, to = from + PAGE - 1;
    const { data, error } = await window._sb
      .from('etf_prices')
      .select('date, open, high, low, close, adj_close, volume')
      .eq('ticker', ticker)
      .order('date', { ascending: true })
      .range(from, to);
    if (error || !data?.length) break;
    all.push(...data);
    if (data.length < PAGE) break;  // 마지막 페이지
    page++;
  }
  return all.length >= 20 ? all : null;
}

// ── 기간별 수익률 계산 ────────────────────────────────────────────────────────
function calcPeriodReturn(history, calDays) {
  const now = history[history.length - 1].close;
  const cutDate = new Date();
  cutDate.setDate(cutDate.getDate() - calDays);
  const cutStr = cutDate.toISOString().split('T')[0];
  for (let i = history.length - 2; i >= 0; i--) {
    if (history[i].date <= cutStr) return (now / history[i].close - 1) * 100;
  }
  return null;
}
function calcYTD(history) {
  const now = history[history.length - 1].close;
  const ytdStr = new Date().getFullYear() + '-01-01';
  const base = history.find(p => p.date >= ytdStr);
  return base ? (now / base.close - 1) * 100 : null;
}
function calcAnnReturn(history, years) {
  const now = history[history.length - 1].close;
  const cutDate = new Date();
  cutDate.setFullYear(cutDate.getFullYear() - years);
  const cutStr = cutDate.toISOString().split('T')[0];
  const base = history.find(p => p.date >= cutStr);
  if (!base) return null;
  return (Math.pow(now / base.close, 1 / years) - 1) * 100;
}
function updatePerfFromHistory() {
  if (!priceHistory || !currentETF) return;
  const h = priceHistory;
  const ret = {
    '1M':     calcPeriodReturn(h, 30),
    '3M':     calcPeriodReturn(h, 91),
    'YTD':    calcYTD(h),
    '1Y':     calcPeriodReturn(h, 365),
    '3Y_ann': calcAnnReturn(h, 3),
    '5Y_ann': calcAnnReturn(h, 5),
  };
  const periods = [
    { key: '1M',     labelKey: 'detail.perf.period.1M',    ann: false },
    { key: '3M',     labelKey: 'detail.perf.period.3M',    ann: false },
    { key: 'YTD',    labelKey: 'detail.perf.period.YTD',   ann: false },
    { key: '1Y',     labelKey: 'detail.perf.period.1Y',    ann: false },
    { key: '3Y_ann', labelKey: 'detail.perf.period.3Y_ann',ann: true },
    { key: '5Y_ann', labelKey: 'detail.perf.period.5Y_ann',ann: true },
  ];
  document.getElementById('perf-table-body').innerHTML = periods.map(p => {
    const v = ret[p.key];
    const cls = v === null ? 'ret-na' : v >= 0 ? 'ret-pos' : 'ret-neg';
    const annLabel = p.ann ? I18n.t('detail.perf.ann') : I18n.t('detail.perf.accumulated');
    return `<tr>
      <td class="perf-period">${I18n.t(p.labelKey)}</td>
      <td class="${cls}">${v === null ? '—' : fmtPct(v)}</td>
      <td style="color:var(--text-muted);font-size:0.75rem">${annLabel}</td>
    </tr>`;
  }).join('');
}

// ── 메인 렌더 함수 ────────────────────────────────────────────────────────────
function renderPage(etf, sectorId) {
  currentETF = etf;
  const supp = SUPP[etf.ticker] || {};
  const sector = SECTOR_NAMES[sectorId] || sectorId || '—';

  // ── Hero ───────────────────────────────────────
  document.getElementById('h-ticker').textContent = etf.ticker;
  document.getElementById('h-ticker').style.color = '#e2e8f0';
  document.getElementById('h-name').textContent   = etf.name;
  document.getElementById('h-aum').textContent     = fmtAUM(etf.aum);
  document.getElementById('h-desc').textContent    = supp.desc || I18n.t('detail.desc.pending');
  document.getElementById('h-datadate').textContent = '2026-02-26';
  document.getElementById('note-datadate').textContent = '2026-02-26';

  const badgesHtml =
    `<span class="badge badge-sector">${sector}</span>` +
    (etf.is_legacy ? '<span class="badge badge-legacy">Legacy</span>' : '<span class="badge badge-active">Active</span>') +
    (etf.short_history ? `<span class="badge badge-short">${I18n.t('detail.short.badge')}</span>` : '');
  document.getElementById('h-badges').innerHTML = badgesHtml;
  updateStarBtn();

  // ── Quick Stats ─────────────────────────────────
  document.getElementById('qs-exp').textContent      = supp.exp      || fmtExpRatio(etf.exp_ratio) || I18n.t('detail.data.pending');
  document.getElementById('qs-inception').textContent = (etf.inception && etf.inception !== '1900-01-01') ? etf.inception : '—';
  document.getElementById('qs-issuer').textContent   = supp.issuer   || inferIssuer(etf.name) || I18n.t('detail.data.pending');
  document.getElementById('qs-bench').textContent    = supp.bench    || I18n.t('detail.data.pending');
  document.getElementById('qs-numh').textContent     = supp.numH !== undefined ? I18n.t('detail.numh.format', { n: supp.numH.toLocaleString() }) : '—';

  // ── 차트 ────────────────────────────────────────
  if (priceHistory) initPriceChart(document.getElementById('chart-container'), priceHistory, currentChartType);
  document.getElementById('chart-cagr').textContent = fmtPct(etf.cagr);
  document.getElementById('chart-vol').textContent  = fmtPct(etf.vol);

  // ── 기간별 수익률 (실데이터 로드 후 updatePerfFromHistory()로 갱신) ──
  if (priceHistory) {
    updatePerfFromHistory();
  } else {
    const perfPeriods = [
      { key: '1M',     labelKey: 'detail.perf.period.1M',    ann: false },
      { key: '3M',     labelKey: 'detail.perf.period.3M',    ann: false },
      { key: 'YTD',    labelKey: 'detail.perf.period.YTD',   ann: false },
      { key: '1Y',     labelKey: 'detail.perf.period.1Y',    ann: false },
      { key: '3Y_ann', labelKey: 'detail.perf.period.3Y_ann',ann: true },
      { key: '5Y_ann', labelKey: 'detail.perf.period.5Y_ann',ann: true },
    ];
    document.getElementById('perf-table-body').innerHTML = perfPeriods.map(p => {
      const annLabel = p.ann ? I18n.t('detail.perf.ann') : I18n.t('detail.perf.accumulated');
      return `<tr>
        <td class="perf-period">${I18n.t(p.labelKey)}</td>
        <td class="ret-na">—</td>
        <td style="color:var(--text-muted);font-size:0.75rem">${annLabel}</td>
      </tr>`;
    }).join('');
  }

  // ── 상위 구성종목 ───────────────────────────────
  const holdings = supp.holdings;
  let holdHtml = '';
  if (!holdings || holdings.length === 0) {
    holdHtml = `<div style="text-align:center;padding:24px;color:var(--text-muted);font-size:0.85rem">${I18n.t('detail.holdings.empty')}</div>`;
  } else {
    const maxW = Math.max(...holdings.map(h => h[2]));
    holdHtml = holdings.map(([tk, nm, wt], i) =>
      `<div class="holding-row">
        <span class="holding-rank">${i+1}</span>
        <span class="holding-ticker">${tk}</span>
        <span class="holding-name">${nm}</span>
        <div class="holding-bar-wrap">
          <div class="holding-bar-bg"><div class="holding-bar" style="width:${(wt/maxW*100).toFixed(1)}%"></div></div>
        </div>
        <span class="holding-weight">${wt.toFixed(2)}%</span>
      </div>`
    ).join('');
    const top10Sum = holdings.reduce((s, h) => s + h[2], 0);
    holdHtml += `<div class="holdings-footer">
      <span>${I18n.t('detail.holdings.sum', { pct: top10Sum.toFixed(1) })}</span>
      <span>${I18n.t('detail.holdings.total', { n: (supp.numH || '?').toLocaleString() })}</span>
    </div>`;
  }
  document.getElementById('holdings-container').innerHTML = holdHtml;

  // ── 분석 지표 ───────────────────────────────────
  const metrics = [
    { label: 'Z-Score', key: 'z_score',   val: etf.short_history ? null : etf.z_score,   fmt: v => fmtNum(v, 2),   gauge: [v => renderGauge(v, -3, 3, '#3b82f6')] },
    { label: I18n.t('detail.metric.rsi'), key: 'rsi',     val: etf.rsi,           fmt: v => fmtNum(v, 0) + '  ', gauge: [v => renderGauge(v, 0, 100, '#f59e0b')] },
    { label: '52W Range', key: 'range_52w', val: etf.range_52w,    fmt: v => fmtNum(v, 0) + '%',  gauge: [v => renderGauge(v, 0, 100, '#8b5cf6')] },
    { label: I18n.t('detail.metric.ma200'), key: 'ma200_pct', val: etf.short_history ? null : etf.ma200_pct, fmt: v => fmtPct(v), gauge: [] },
    { label: '52W MDD',   key: 'mdd_52w',  val: etf.short_history ? null : etf.mdd_52w,  fmt: v => fmtPct(v), gauge: [] },
    { label: 'r_Anchor',  key: 'r_anchor', val: etf.r_anchor,      fmt: v => fmtNum(v, 2), gauge: [] },
    { label: 'SMH Corr',  key: 'smh_corr', val: etf.smh_corr,      fmt: v => v !== null && v !== undefined ? fmtNum(v, 2) : '—', gauge: [] },
    { label: 'CAGR',      key: 'cagr',     val: etf.short_history ? null : etf.cagr,     fmt: v => fmtPct(v), gauge: [] },
    { label: I18n.t('detail.metric.vol'), key: 'vol',  val: etf.short_history ? null : etf.vol,      fmt: v => fmtPct(v, 1), gauge: [] },
    { label: 'Sortino',   key: 'sortino',  val: etf.short_history ? null : etf.sortino,  fmt: v => fmtNum(v, 2), gauge: [] },
  ];
  const metricsHtml = metrics.map(m => {
    const display = m.val === null || m.val === undefined ? '—' : m.fmt(m.val);
    const cls     = m.val !== null && m.val !== undefined ? metricColor(m.key, m.val) : 'val-neutral';
    return `<div class="metric-row">
      <span class="metric-label">${m.label}</span>
      <span class="metric-value ${cls}">${display}</span>
    </div>`;
  }).join('');
  document.getElementById('metrics-container').innerHTML = metricsHtml;

  // ── 펀드 정보 ───────────────────────────────────
  const infoRows = [
    { label: 'Rank',                           val: etf.rank === 9999 ? '—' : ('#' + etf.rank) },
    { label: 'AUM',                            val: fmtAUM(etf.aum) },
    { label: I18n.t('detail.info.fee'),        val: supp.exp       || fmtExpRatio(etf.exp_ratio) || '—' },
    { label: I18n.t('detail.info.issuer'),     val: supp.issuer    || inferIssuer(etf.name) || '—' },
    { label: I18n.t('detail.info.structure'),  val: supp.structure || '—' },
    { label: I18n.t('detail.info.div'),        val: supp.div       || '—' },
    { label: I18n.t('detail.info.divyield'),   val: supp.divYield  || '—' },
    { label: I18n.t('detail.info.bench'),      val: supp.bench     || '—' },
    { label: I18n.t('detail.info.inception'),  val: (etf.inception && etf.inception !== '1900-01-01') ? etf.inception : '—' },
    { label: I18n.t('detail.info.sector'),     val: sector },
    { label: 'Status',                         val: etf.is_legacy ? (etf._user_override ? 'User Legacy' : 'Legacy') : 'Active' },
  ];
  const infoHtml = infoRows.map(r =>
    `<div class="info-row"><span class="info-label">${r.label}</span><span class="info-value">${r.val}</span></div>`
  ).join('');
  document.getElementById('fund-info-container').innerHTML = infoHtml;

  // ── 비교하기 버튼 URL 세팅 ──
  const compareLink = document.getElementById('compare-hero-link');
  if (compareLink) compareLink.href = '/compare?tickers=' + encodeURIComponent(etf.ticker);

  // ── 서브차트 초기화 ──
  // short_history ETF는 Z-Score 없음 — zscore 서브차트 비활성화
  if (etf.short_history) activeIndicators.zscore = false;
  const zchk = document.getElementById('ind-zscore');
  if (zchk) zchk.checked = activeIndicators.zscore;
  buildSubCharts();

  // 페이지 표시
  document.getElementById('loading-state').style.display = 'none';
  document.getElementById('page-content').style.display = 'block';
}
