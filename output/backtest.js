// ─────────────────────────────────────────────────────────────────────────────
// 상수 & 색상
// ─────────────────────────────────────────────────────────────────────────────
const COLORS = ['#3b82f6','#a78bfa','#f59e0b','#4ade80','#f87171','#38bdf8','#fb923c','#c084fc','#22d3ee','#a3e635'];
const PRESETS_DEF = {
  '6040':      [['SPY',60],['BND',40]],
  allweather:  [['SPY',30],['TLT',40],['GLD',15],['IEI',7.5],['DBC',7.5]],
  golden:      [['SPY',20],['IWM',20],['TLT',20],['SHY',20],['GLD',20]],
  tech:        [['QQQ',50],['SOXX',25],['VGT',25]],
  global:      [['VTI',40],['VEA',20],['VWO',10],['BND',20],['GLD',10]],
};

// ─────────────────────────────────────────────────────────────────────────────
// 상태
// ─────────────────────────────────────────────────────────────────────────────
let allData = {};
let btData  = {};          // 실제 연도별 수익률 {TICKER: {YEAR: return}}
let DATA_END_YEAR = 2025;  // backtest_data.json 마지막 연도 (로드 후 갱신)
let period  = 5;
let lastResult = null;

// ─────────────────────────────────────────────────────────────────────────────
// 포트폴리오 행 관리
// ─────────────────────────────────────────────────────────────────────────────
let rows = []; // [{id, ticker, weight}]
let rowId = 0;

function addRow(ticker='', weight='') {
  if (rows.length >= 10) return;
  const id = ++rowId;
  rows.push({id, ticker, weight});
  renderRows();
}

function removeRow(id) {
  rows = rows.filter(r => r.id !== id);
  renderRows();
}

function renderRows() {
  const container = document.getElementById('port-rows');
  container.innerHTML = rows.map((r, i) => `
    <div class="port-row" data-id="${r.id}">
      <input class="ticker-inp" type="text" placeholder="${I18n.t('bt.placeholder.ticker')}" value="${r.ticker}"
        oninput="updateRow(${r.id},'ticker',this.value)" onblur="this.value=this.value.toUpperCase()" maxlength="10">
      <div style="position:relative">
        <input class="weight-inp" type="number" placeholder="%" min="0" max="100" step="0.5" value="${r.weight}"
          oninput="updateRow(${r.id},'weight',this.value)" style="padding-right:18px">
        <span style="position:absolute;right:7px;top:50%;transform:translateY(-50%);font-size:.72rem;color:var(--t3);pointer-events:none">%</span>
      </div>
      <button class="del-btn" onclick="removeRow(${r.id})">✕</button>
    </div>`).join('');
  document.getElementById('add-row-btn').style.display = rows.length >= 10 ? 'none' : 'flex';
  updateWeightSum();
}

function updateRow(id, field, val) {
  const r = rows.find(r => r.id === id);
  if (r) r[field] = field === 'ticker' ? val.toUpperCase() : val;
  updateWeightSum();
}

function updateWeightSum() {
  const total = rows.reduce((s, r) => s + (parseFloat(r.weight) || 0), 0);
  const pct = Math.min(100, total);
  const fill = document.getElementById('ws-fill');
  const label = document.getElementById('ws-label');
  fill.style.width = pct + '%';
  fill.style.background = Math.abs(total - 100) < 0.1 ? '#4ade80' : total > 100 ? '#f87171' : '#f59e0b';
  label.style.color = Math.abs(total - 100) < 0.1 ? '#4ade80' : total > 100 ? '#f87171' : '#f59e0b';
  label.textContent = total.toFixed(1) + '%';
}

function equalWeight() {
  if (rows.length === 0) return;
  const w = (100 / rows.length).toFixed(1);
  rows.forEach(r => r.weight = w);
  renderRows();
}

function setPeriod(yr) {
  period = yr;
  document.querySelectorAll('#period-tabs .sg-tab').forEach(t => t.classList.toggle('on', +t.dataset.yr === yr));
}

function loadPreset(key) {
  const def = PRESETS_DEF[key];
  if (!def) return;
  rows = [];
  def.forEach(([ticker, weight]) => { const id = ++rowId; rows.push({id, ticker, weight}); });
  renderRows();
}

// ─────────────────────────────────────────────────────────────────────────────
// 실데이터 수익률 조회 (backtest_data.json 기반)
// ─────────────────────────────────────────────────────────────────────────────
function getActualReturn(ticker, year) {
  const rec = btData[ticker];
  if (rec) {
    const v = rec[String(year)];
    if (v !== undefined) return v;
  }
  // 데이터 없는 연도(상장 전 등) → ETF의 전체기간 CAGR로 대체
  const etf = allData[ticker];
  return etf ? (etf.cagr || 10) / 100 : 0.10;
}

// DCA 주기 토글
function onDcaFreqChange() {
  const freq = document.getElementById('dca-freq').value;
  document.getElementById('dca-amt-wrap').style.visibility = freq !== 'none' ? 'visible' : 'hidden';
}

function runBacktest() {
  setErr('');
  const holdings = [];
  for (const r of rows) {
    const t = r.ticker.trim().toUpperCase();
    const w = parseFloat(r.weight);
    if (!t || !w) continue;
    if (!allData[t]) { setErr(I18n.t('bt.error.notfound', { t })); return; }
    holdings.push({ etf: allData[t], weight: w / 100 });
  }
  if (holdings.length < 1) { setErr(I18n.t('bt.error.empty')); return; }
  const totalW = holdings.reduce((s, h) => s + h.weight, 0);
  if (Math.abs(totalW - 1) > 0.005) { setErr(I18n.t('bt.error.weight', { w: (totalW*100).toFixed(1) })); return; }

  const initVal = parseFloat(document.getElementById('init-sel').value);
  const rawBench = document.getElementById('bench-input').value.trim().toUpperCase();
  const benchTicker = rawBench || 'none';
  if (benchTicker !== 'none' && !btData[benchTicker] && !allData[benchTicker]) {
    setErr(`벤치마크 티커 "${benchTicker}"를 찾을 수 없습니다.`); return;
  }
  const dcaFreq   = document.getElementById('dca-freq').value;
  const dcaAmount = dcaFreq !== 'none' ? (parseFloat(document.getElementById('dca-amt').value) || 0) : 0;
  const hasDCA    = dcaFreq !== 'none' && dcaAmount > 0;

  const currYear  = DATA_END_YEAR + 1; // 마지막 완성 연도 다음 = 시뮬레이션 상한
  const startYear = currYear - period;

  // 연도별 실수익률 사전 빌드
  const pre = {}; // "TICKER:YEAR" → annual return
  for (const h of holdings) {
    for (let y = startYear; y < currYear; y++)
      pre[h.etf.ticker + ':' + y] = getActualReturn(h.etf.ticker, y);
  }
  if (benchTicker !== 'none') {
    for (let y = startYear; y < currYear; y++)
      pre[benchTicker + ':' + y] = getActualReturn(benchTicker, y);
  }

  // DCA 적립 간격 (월 단위)
  const dcaEvery = { monthly: 1, quarterly: 3, semiannual: 6, annually: 12 }[dcaFreq] ?? Infinity;

  // ── 월별 시뮬레이션 ─────────────────────────────────────
  let portVal       = initVal;
  let benchVal      = initVal;
  let totalInvested = initVal;

  const portSeries     = [{ year: startYear, val: initVal }];
  const benchSeries    = benchTicker !== 'none' ? [{ year: startYear, val: initVal }] : [];
  const investedSeries = [{ year: startYear, val: initVal }];
  const monthlyVals    = [initVal]; // MDD 계산용
  const annualData     = [];

  let portYearStart  = initVal;
  let benchYearStart = initVal;

  for (let m = 0; m < period * 12; m++) {
    const year      = startYear + Math.floor(m / 12);
    const monthOfYr = m % 12;

    // 연간 수익률 → 월 수익률
    const portAnnual  = holdings.reduce((s, h) => s + h.weight * (pre[h.etf.ticker + ':' + year] || 0), 0);
    const benchAnnual = benchTicker !== 'none' ? (pre[benchTicker + ':' + year] || 0) : 0;
    const portMo  = Math.pow(1 + portAnnual,  1 / 12) - 1;
    const benchMo = Math.pow(1 + benchAnnual, 1 / 12) - 1;

    portVal  *= (1 + portMo);
    benchVal *= (1 + benchMo);

    // 적립식 입금 (m=0은 초기 납입이므로 스킵)
    if (hasDCA && m > 0 && m % dcaEvery === 0) {
      portVal       += dcaAmount;
      totalInvested += dcaAmount;
    }

    monthlyVals.push(portVal);

    // 연말 데이터 기록
    if (monthOfYr === 11) {
      annualData.push({
        year,
        portRet:  portVal  / portYearStart  - 1,
        benchRet: benchTicker !== 'none' ? benchVal / benchYearStart - 1 : 0,
      });
      portSeries.push({ year: year + 1, val: portVal });
      investedSeries.push({ year: year + 1, val: totalInvested });
      if (benchTicker !== 'none') benchSeries.push({ year: year + 1, val: benchVal });
      portYearStart  = portVal;
      benchYearStart = benchVal;
    }
  }

  // ── 통계 ────────────────────────────────────────────────
  const portReturns = annualData.map(d => d.portRet);
  const n    = portReturns.length;
  const mean = portReturns.reduce((s, r) => s + r, 0) / n;
  const vol  = Math.sqrt(portReturns.reduce((s, r) => s + (r - mean) ** 2, 0) / Math.max(n - 1, 1)) * 100;

  // MDD (월별 기준)
  let peak = monthlyVals[0], mdd = 0;
  for (const v of monthlyVals) {
    peak = Math.max(peak, v);
    mdd  = Math.min(mdd, (v - peak) / peak);
  }

  // 수익률
  const totalGain = portVal - totalInvested;
  const totalRet  = (portVal / totalInvested - 1) * 100;
  // DCA 없을 때는 initVal 기준 CAGR, DCA 있을 때는 최종/납입 기준 단순연환산
  const cagr = hasDCA
    ? (Math.pow(Math.max(portVal / totalInvested, 1e-6), 1 / n) - 1) * 100
    : (Math.pow(portVal / initVal, 1 / n) - 1) * 100;

  const rfr = 0.04;
  const sharpe = vol > 0 ? (cagr / 100 - rfr) / (vol / 100) : 0;
  const downR  = portReturns.filter(r => r < 0);
  const downD  = Math.sqrt(downR.reduce((s, r) => s + r ** 2, 0) / Math.max(n, 1));
  const sortino = downD > 0 ? (cagr / 100 - rfr) / downD : 5;

  const benchCAGR = benchTicker !== 'none'
    ? (Math.pow(benchVal / initVal, 1 / n) - 1) * 100 : null;
  const alpha = benchCAGR != null ? cagr - benchCAGR : null;

  lastResult = {
    holdings, period, portSeries, benchSeries, investedSeries, annualData, benchTicker,
    hasDCA, dcaAmount, dcaFreq,
    stats: { cagr, vol, mdd: mdd * 100, sharpe, sortino, totalRet, alpha, initVal, totalInvested, portVal, totalGain },
  };

  showResults(lastResult);
}

// ─────────────────────────────────────────────────────────────────────────────
// 결과 렌더링
// ─────────────────────────────────────────────────────────────────────────────
function showResults(result) {
  document.getElementById('empty-hint').style.display = 'none';
  const res = document.getElementById('results');
  res.style.display = 'block';

  const { stats, holdings, portSeries, benchSeries, investedSeries, annualData, benchTicker, hasDCA } = result;

  // ── 통계 카드 ──
  const alphaCard = stats.alpha != null
    ? `<div class="stat-card"><div class="stat-label">${I18n.t('bt.stat.alpha.label')}</div><div class="stat-val ${stats.alpha>=0?'pos':'neg'}">${stats.alpha>=0?'+':''}${stats.alpha.toFixed(1)}%</div><div class="stat-sub">${I18n.t('bt.stat.alpha.sub')}</div></div>` : '';

  const dcaCards = hasDCA ? `
    <div class="stat-card">
      <div class="stat-label">${I18n.t('bt.stat.invested.label')}</div>
      <div class="stat-val mu">$${fmtD(stats.totalInvested)}</div>
      <div class="stat-sub">${I18n.t('bt.stat.invested.sub')}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">${I18n.t('bt.stat.profit.label')}</div>
      <div class="stat-val ${stats.totalGain>=0?'pos':'neg'}">${stats.totalGain>=0?'+':''}$${fmtD(Math.abs(stats.totalGain))}</div>
      <div class="stat-sub">${I18n.t('bt.stat.profit.sub')}</div>
    </div>` : '';

  // DCA 없을 때: "총 수익률" 카드는 initVal 기준
  const retLabel = hasDCA ? I18n.t('bt.stat.ret.label.dca') : I18n.t('bt.stat.ret.label');
  const retSub   = hasDCA
    ? `$${fmtD(stats.totalInvested)} → $${fmtD(stats.portVal)}`
    : `$${fmtD(stats.initVal)} → $${fmtD(stats.portVal)}`;

  document.getElementById('stat-cards').innerHTML = `
    <div class="stat-card">
      <div class="stat-label">${retLabel}</div>
      <div class="stat-val ${stats.totalRet>=0?'pos':'neg'}">${stats.totalRet>=0?'+':''}${stats.totalRet.toFixed(1)}%</div>
      <div class="stat-sub">${retSub}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">CAGR</div>
      <div class="stat-val ${stats.cagr>=0?'pos':'neg'}">${stats.cagr>=0?'+':''}${stats.cagr.toFixed(1)}%</div>
      <div class="stat-sub">${hasDCA ? I18n.t('bt.stat.ret.sub.dca') : I18n.t('bt.stat.ret.sub')}</div>
    </div>
    ${dcaCards}
    <div class="stat-card">
      <div class="stat-label">${I18n.t('bt.stat.vol.label')}</div>
      <div class="stat-val amb">${stats.vol.toFixed(1)}%</div>
      <div class="stat-sub">${I18n.t('bt.stat.vol.sub')}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">${I18n.t('bt.stat.mdd.label')}</div>
      <div class="stat-val neg">${stats.mdd.toFixed(1)}%</div>
      <div class="stat-sub">${I18n.t('bt.stat.mdd.sub')}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Sharpe</div>
      <div class="stat-val ${stats.sharpe>=1?'pos':'mu'}">${stats.sharpe.toFixed(2)}</div>
      <div class="stat-sub">${I18n.t('bt.stat.sharpe.sub')}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Sortino</div>
      <div class="stat-val ${stats.sortino>=1.2?'pos':'mu'}">${Math.min(stats.sortino,9.99).toFixed(2)}</div>
      <div class="stat-sub">${I18n.t('bt.stat.sortino.sub')}</div>
    </div>
    ${alphaCard}`;

  // ── 누적 수익 라인 차트 ──
  drawCumChart(portSeries, benchSeries, investedSeries, benchTicker, stats.initVal, hasDCA);

  // ── 연도별 바 차트 ──
  drawAnnualChart(annualData, benchTicker);

  // ── 포트폴리오 구성 바 ──
  const allocBars = holdings.map((h, i) => `
    <div class="alloc-row">
      <span class="alloc-ticker" style="color:${COLORS[i%COLORS.length]}">${h.etf.ticker}</span>
      <div class="alloc-bar-wrap"><div class="alloc-bar-fill" style="width:${(h.weight*100).toFixed(1)}%;background:${COLORS[i%COLORS.length]}"></div></div>
      <span class="alloc-pct">${(h.weight*100).toFixed(1)}%</span>
    </div>`).join('');
  document.getElementById('alloc-bars').innerHTML = allocBars;

  // 범례
  const legend = `
    <div class="legend-item"><div class="legend-dot" style="background:#60a5fa"></div>${I18n.t('bt.legend.port')}</div>
    ${benchTicker !== 'none' ? `<div class="legend-item"><div class="legend-dot" style="background:#475569;border-top:1px dashed #64748b"></div>${I18n.t('bt.legend.bench', { t: benchTicker })}</div>` : ''}
    ${hasDCA ? `<div class="legend-item"><div class="legend-dot" style="background:#f59e0b;border-top:1px dashed #f59e0b"></div>${I18n.t('bt.legend.invested')}</div>` : ''}`;
  document.getElementById('cum-legend').innerHTML = legend;

  res.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ─────────────────────────────────────────────────────────────────────────────
// SVG 누적 수익 라인 차트
// ─────────────────────────────────────────────────────────────────────────────
function drawCumChart(portSeries, benchSeries, investedSeries, benchTicker, initVal, hasDCA) {
  const W=700, H=240, P={t:16,r:24,b:36,l:72};
  const cw=W-P.l-P.r, ch=H-P.t-P.b;

  const allVals = portSeries.map(d=>d.val)
    .concat(benchTicker!=='none' ? benchSeries.map(d=>d.val) : [])
    .concat(hasDCA ? investedSeries.map(d=>d.val) : []);
  const minV = Math.min(...allVals) * 0.97;
  const maxV = Math.max(...allVals) * 1.03;
  const years = portSeries.map(d=>d.year);
  const minY = years[0], maxY = years[years.length-1];

  const toX = y => P.l + ((y - minY) / (maxY - minY)) * cw;
  const toY = v => P.t + ch - ((v - minV) / (maxV - minV)) * ch;

  // Y 그리드 레이블
  const yTicks = [];
  const valRange = maxV - minV;
  const rawStep = valRange / 4;
  const mag = Math.pow(10, Math.floor(Math.log10(Math.max(rawStep, 1))));
  const step = Math.ceil(rawStep / mag) * mag;
  for (let v = Math.ceil(minV/step)*step; v <= maxV; v += step) yTicks.push(v);

  const grid = yTicks.map(v => {
    const pct = ((v/initVal - 1) * 100);
    return `<line x1="${P.l}" y1="${toY(v).toFixed(1)}" x2="${P.l+cw}" y2="${toY(v).toFixed(1)}" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
      <text x="${(P.l-6).toFixed(1)}" y="${(toY(v)+3.5).toFixed(1)}" text-anchor="end" font-size="9.5" fill="#475569" font-family="monospace">${pct>=0?'+':''}${pct.toFixed(0)}%</text>`;
  }).join('');

  const xLabels = years.map(y =>
    `<text x="${toX(y).toFixed(1)}" y="${(H-5).toFixed(1)}" text-anchor="middle" font-size="9.5" fill="#475569" font-family="monospace">${y}</text>`
  ).join('');

  // 기준선 (원금)
  const baseLine = `<line x1="${P.l}" y1="${toY(initVal).toFixed(1)}" x2="${P.l+cw}" y2="${toY(initVal).toFixed(1)}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="3,3" stroke-width="1"/>`;

  // 납입금 누적 선 (DCA 활성 시)
  let investedLine = '';
  if (hasDCA && investedSeries.length > 1) {
    const iPath = 'M ' + investedSeries.map(d => `${toX(d.year).toFixed(1)} ${toY(d.val).toFixed(1)}`).join(' L ');
    investedLine = `<path d="${iPath}" fill="none" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="4,3" opacity=".7"/>`;
  }

  // 포트폴리오 라인 + 면적
  const portPath = 'M ' + portSeries.map(d => `${toX(d.year).toFixed(1)} ${toY(d.val).toFixed(1)}`).join(' L ');
  const areaPath = `${portPath} L ${toX(maxY).toFixed(1)} ${toY(minV).toFixed(1)} L ${toX(minY).toFixed(1)} ${toY(minV).toFixed(1)} Z`;
  const portLine = `
    <defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#3b82f6" stop-opacity=".25"/><stop offset="100%" stop-color="#3b82f6" stop-opacity="0"/></linearGradient></defs>
    <path d="${areaPath}" fill="url(#ag)"/>
    <path d="${portPath}" fill="none" stroke="#3b82f6" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;

  // 벤치마크 라인
  let benchLine = '';
  if (benchTicker !== 'none' && benchSeries.length) {
    const bPath = 'M ' + benchSeries.map(d => `${toX(d.year).toFixed(1)} ${toY(d.val).toFixed(1)}`).join(' L ');
    benchLine = `<path d="${bPath}" fill="none" stroke="#475569" stroke-width="1.5" stroke-dasharray="5,3"/>`;
  }

  // 끝점 레이블
  const lastPort = portSeries[portSeries.length-1];
  const endText  = hasDCA
    ? `$${fmtD(lastPort.val)}`
    : `${((lastPort.val/initVal-1)*100)>=0?'+':''}${((lastPort.val/initVal-1)*100).toFixed(1)}%`;
  const endColor = lastPort.val >= initVal ? '#4ade80' : '#f87171';
  const endLabel = `<text x="${(toX(lastPort.year)+4).toFixed(1)}" y="${(toY(lastPort.val)-4).toFixed(1)}" font-size="10" font-weight="700" fill="${endColor}" font-family="Inter,sans-serif">${endText}</text>`;

  document.getElementById('cum-chart').innerHTML = `
    <svg viewBox="0 0 ${W} ${H}" width="100%" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
      ${grid}${xLabels}${baseLine}${investedLine}${portLine}${benchLine}${endLabel}
    </svg>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// SVG 연도별 수익률 바 차트
// ─────────────────────────────────────────────────────────────────────────────
function drawAnnualChart(annualData, benchTicker) {
  const W=700, H=200, P={t:16,r:20,b:36,l:56};
  const cw=W-P.l-P.r, ch=H-P.t-P.b;
  const n = annualData.length;
  const hasBench = benchTicker !== 'none';
  const barW = (cw / n) * (hasBench ? 0.37 : 0.6);
  const gap  = (cw / n);

  const portRets  = annualData.map(d => d.portRet * 100);
  const benchRets = hasBench ? annualData.map(d => d.benchRet * 100) : [];
  const allRets   = portRets.concat(benchRets);
  const maxAbs    = Math.max(15, ...allRets.map(Math.abs)) * 1.15;

  const toY = pct => P.t + ch/2 - (pct / maxAbs) * (ch/2);
  const zero = P.t + ch / 2;

  // Y 그리드
  const yLabels = [-maxAbs*0.67, 0, maxAbs*0.67].map(v =>
    `<line x1="${P.l}" y1="${toY(v).toFixed(1)}" x2="${P.l+cw}" y2="${toY(v).toFixed(1)}" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
     <text x="${(P.l-5).toFixed(1)}" y="${(toY(v)+3.5).toFixed(1)}" text-anchor="end" font-size="9" fill="#475569" font-family="monospace">${v>0?'+':''}${v.toFixed(0)}%</text>`
  ).join('');

  // 0선
  const zeroLine = `<line x1="${P.l}" y1="${zero.toFixed(1)}" x2="${P.l+cw}" y2="${zero.toFixed(1)}" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>`;

  const bars = annualData.map((d, i) => {
    const cx   = P.l + i * gap + gap / 2;
    const portH = Math.abs(d.portRet * 100) / maxAbs * (ch / 2);
    const portY = d.portRet >= 0 ? zero - portH : zero;
    const portColor = d.portRet >= 0 ? '#3b82f6' : '#ef4444';
    let benchBar = '';
    if (hasBench) {
      const bH = Math.abs(d.benchRet * 100) / maxAbs * (ch / 2);
      const bY = d.benchRet >= 0 ? zero - bH : zero;
      benchBar = `<rect x="${(cx + barW*0.1).toFixed(1)}" y="${bY.toFixed(1)}" width="${barW.toFixed(1)}" height="${Math.max(bH,1).toFixed(1)}" fill="${d.benchRet>=0?'#475569':'#7f1d1d'}" rx="2" opacity=".7"/>`;
    }
    const portX = hasBench ? cx - barW * 1.1 : cx - barW / 2;
    return `
      <rect x="${portX.toFixed(1)}" y="${portY.toFixed(1)}" width="${barW.toFixed(1)}" height="${Math.max(portH,1).toFixed(1)}" fill="${portColor}" rx="2"/>
      ${benchBar}
      <text x="${cx.toFixed(1)}" y="${(H-6).toFixed(1)}" text-anchor="middle" font-size="9" fill="#475569" font-family="monospace">${d.year}</text>
      <text x="${portX+barW/2}" y="${(d.portRet>=0?portY-3:portY+portH+9).toFixed(1)}" text-anchor="middle" font-size="8.5" font-weight="700" fill="${d.portRet>=0?'#60a5fa':'#f87171'}" font-family="monospace">${d.portRet>=0?'+':''}${(d.portRet*100).toFixed(0)}%</text>`;
  }).join('');

  document.getElementById('annual-chart').innerHTML = `
    <svg viewBox="0 0 ${W} ${H}" width="100%" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
      ${yLabels}${zeroLine}${bars}
    </svg>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// 공유 기능
// ─────────────────────────────────────────────────────────────────────────────
function buildShareURL() {
  const portfolio = rows
    .filter(r => r.ticker && r.weight)
    .map(r => `${r.ticker.toUpperCase()}:${r.weight}`)
    .join(',');
  const dcaFreq = document.getElementById('dca-freq').value;
  const dcaAmt  = document.getElementById('dca-amt').value;
  let url = `${location.origin}/backtest?portfolio=${encodeURIComponent(portfolio)}&period=${period}`;
  if (dcaFreq !== 'none') url += `&dca=${dcaFreq}&dca_amt=${dcaAmt}`;
  return url;
}

function shareURL() {
  navigator.clipboard.writeText(buildShareURL()).then(() => {
    const btn = document.getElementById('share-url-btn');
    btn.classList.add('copied');
    btn.textContent = I18n.t('bt.btn.copied');
    setTimeout(() => { btn.classList.remove('copied'); btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg> ${I18n.t('bt.btn.share.link')}`; }, 2500);
  });
}

function shareText() {
  if (!lastResult) return;
  const s = lastResult.stats;
  const holdings = lastResult.holdings.map(h => `${h.etf.ticker} ${(h.weight*100).toFixed(0)}%`).join(' + ');
  const text = `📊 CORRYU 백테스트 결과\n포트폴리오: ${holdings}\n기간: ${period}년\n\nCAGR ${s.cagr>=0?'+':''}${s.cagr.toFixed(1)}% | 총수익 ${s.totalRet>=0?'+':''}${s.totalRet.toFixed(1)}%\n변동성 ${s.vol.toFixed(1)}% | MDD ${s.mdd.toFixed(1)}% | Sharpe ${s.sharpe.toFixed(2)}\n\n${buildShareURL()}`;
  navigator.clipboard.writeText(text).then(() => alert(I18n.t('bt.btn.copied')));
}

// ─────────────────────────────────────────────────────────────────────────────
// 유틸
// ─────────────────────────────────────────────────────────────────────────────
function setErr(msg) { document.getElementById('err-msg').textContent = msg; }
function fmtD(v) { return v >= 1e6 ? (v/1e6).toFixed(2)+'M' : v >= 1e3 ? (v/1e3).toFixed(1)+'K' : Math.round(v).toString(); }

// URL 파라미터로 초기 포트폴리오 로드
function loadFromURL() {
  const params = new URLSearchParams(location.search);
  const portfolio = params.get('portfolio');
  const prd = parseInt(params.get('period'));
  if (prd && [3,5,7,10].includes(prd)) setPeriod(prd);
  // DCA 복원
  const dca    = params.get('dca');
  const dcaAmt = params.get('dca_amt');
  if (dca && ['monthly','quarterly','semiannual','annually'].includes(dca)) {
    document.getElementById('dca-freq').value = dca;
    onDcaFreqChange();
    if (dcaAmt) document.getElementById('dca-amt').value = dcaAmt;
  }
  if (portfolio) {
    rows = [];
    portfolio.split(',').forEach(item => {
      const [ticker, weight] = item.split(':');
      if (ticker && weight) { const id = ++rowId; rows.push({ id, ticker: ticker.toUpperCase(), weight }); }
    });
    renderRows();
    if (rows.length >= 1 && Object.keys(allData).length > 0) runBacktest();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 초기화
// ─────────────────────────────────────────────────────────────────────────────
// 기본 행 2개
addRow('SPY', 60);
addRow('BND', 40);

const lb = document.getElementById('lb');
lb.style.width = '20%';
Promise.all([
  fetch('/etf_data.json').then(r => r.json()),
  fetch('/backtest_data.json').then(r => r.json()),
]).then(([etfJson, btJson]) => {
  // ETF 메타 로드
  const sectors = etfJson.allData || etfJson;
  for (const [sid, etfs] of Object.entries(sectors)) {
    if (!Array.isArray(etfs)) continue;
    for (const etf of etfs) allData[etf.ticker] = { ...etf, _sid: sid };
  }
  // 실수익률 데이터 로드
  btData = btJson;
  // 마지막 완성 연도 계산 (SPY 기준, 없으면 기본값 유지)
  if (btData['SPY']) {
    DATA_END_YEAR = Math.max(...Object.keys(btData['SPY']).map(Number));
  }
  lb.style.width = '100%';
  setTimeout(() => { lb.style.width = '0'; lb.style.transition = 'none'; }, 400);
  loadFromURL();
  I18n.init();
}).catch(() => setErr(I18n.t('bt.error.load')));

document.addEventListener('i18n:ready', () => {
  renderRows();
  if (lastResult) showResults(lastResult);
});
