// ── etf-detail-charts.js ─────────────────────────────────────────────────────
// 차트 전용 모듈: 공유 상태 변수 + LightweightCharts 기반 인터랙티브 차트
// 의존성: LightweightCharts (CDN), etf-detail-data.js
// 로드 순서: etf-detail-data.js → etf-detail-charts.js
// ─────────────────────────────────────────────────────────────────────────────

// ── 공유 상태 변수 (var → window 프로퍼티로 노출, 타 모듈에서 접근 가능) ──────
var currentETF = null;
var priceHistory = null;
var lwChart = null;
var lwSeries = null;
var currentChartType = 'line';
var activeIndicators = { ma20:false, ma50:false, ma200:true, bb:false, volume:false, rsi:true, zscore:true, range52w:false, mdd:false };
var overlaySeriesMap = {};
var subChartMap = {};
var isSyncing = false;

const OVERLAY_CONF = {
  ma20:  { color:'#f59e0b', period:20  },
  ma50:  { color:'#3b82f6', period:50  },
  ma200: { color:'#a78bfa', period:200 },
};
const SUBCHART_CONF = {
  volume:   { label:'Volume',    height:60,  color:'#60a5fa', refs:[] },
  rsi:      { label:'RSI',       height:90,  color:'#f59e0b', refs:[{v:70,c:'rgba(248,113,113,0.45)'},{v:30,c:'rgba(96,165,250,0.45)'}] },
  zscore:   { label:'Z-Score',   height:90,  color:'#a78bfa', refs:[{v:2,c:'rgba(248,113,113,0.45)'},{v:0,c:'rgba(148,163,184,0.18)'},{v:-2,c:'rgba(96,165,250,0.45)'}] },
  range52w: { label:'52W Range', height:80,  color:'#34d399', refs:[{v:80,c:'rgba(248,113,113,0.45)'},{v:20,c:'rgba(96,165,250,0.45)'}] },
  mdd:      { label:'MDD',       height:80,  color:'#f87171', refs:[{v:-10,c:'rgba(251,191,36,0.45)'},{v:-20,c:'rgba(248,113,113,0.45)'}] },
};

// ── 난수 생성 (SVG 차트용) ────────────────────────────────────────────────────
function seededRand(seed) {
  let s = Math.abs(seed) % 2147483647 || 1;
  return () => { s = s * 16807 % 2147483647; return (s - 1) / 2147483646; };
}
function generatePrices(ticker, cagr, vol, n) {
  const seed = [...ticker].reduce((acc, c, i) => acc + c.charCodeAt(0) * (i * 31 + 7), 42);
  const rand = seededRand(seed);
  const mu  = (cagr || 10) / 100 / 252;
  const sig = (vol  || 18) / 100 / Math.sqrt(252);
  let prices = [100];
  for (let i = 1; i < n; i++) {
    let z = 0;
    for (let j = 0; j < 12; j++) z += rand();
    z = (z - 6);
    prices.push(prices[i - 1] * Math.exp(mu - 0.5 * sig * sig + sig * z));
  }
  return prices;
}

// ── Lightweight Charts 기반 인터랙티브 차트 ─────────────────────────────────
function initPriceChart(container, data, type) {
  if (!container || !data || data.length < 2) return;
  if (lwChart) { try { lwChart.remove(); } catch(e) {} lwChart = null; lwSeries = null; }
  overlaySeriesMap = {};

  const hasSubCharts = Object.keys(SUBCHART_CONF).some(k => activeIndicators[k]);
  lwChart = LightweightCharts.createChart(container, {
    width:  container.clientWidth,
    height: container.clientHeight || 300,
    layout: { background: { type:'solid', color:'transparent' }, textColor:'#64748b', fontFamily:"'Inter',monospace", fontSize:11 },
    grid: { vertLines: { color:'rgba(255,255,255,0.04)' }, horzLines: { color:'rgba(255,255,255,0.04)' } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor:'rgba(255,255,255,0.08)' },
    timeScale: { borderColor:'rgba(255,255,255,0.08)', timeVisible:false, visible: !hasSubCharts },
    handleScroll: { mouseWheel:true, pressedMouseMove:true, horzTouchDrag:true },
    handleScale: { mouseWheel:true, pinch:true },
  });

  if (type === 'candle') {
    lwSeries = lwChart.addCandlestickSeries({ upColor:'#4ade80', downColor:'#f87171', borderUpColor:'#4ade80', borderDownColor:'#f87171', wickUpColor:'#4ade80', wickDownColor:'#f87171' });
    lwSeries.setData(data.map(d => ({ time:d.date, open:d.open??d.close, high:d.high??d.close, low:d.low??d.close, close:d.close })));
  } else {
    lwSeries = lwChart.addAreaSeries({ lineColor:'#4ade80', topColor:'rgba(74,222,128,0.15)', bottomColor:'rgba(74,222,128,0)', lineWidth:2, priceLineVisible:false, crosshairMarkerVisible:true });
    lwSeries.setData(data.map(d => ({ time:d.date, value:d.close })));
  }

  const overAdj = data.map(d => d.close);
  ['ma20','ma50','ma200'].forEach(key => {
    if (!activeIndicators[key]) return;
    const cfg = OVERLAY_CONF[key];
    const s = lwChart.addLineSeries({ color:cfg.color, lineWidth:1.5, priceLineVisible:false, crosshairMarkerVisible:false, lastValueVisible:false });
    s.setData(calcMASeries(overAdj, cfg.period));
    overlaySeriesMap[key] = s;
  });
  if (activeIndicators.bb) {
    const bb = calcBBData(overAdj);
    const addLine = (d, c, ls) => { const s = lwChart.addLineSeries({ color:c, lineWidth:1, priceLineVisible:false, crosshairMarkerVisible:false, lastValueVisible:false, lineStyle:ls }); s.setData(d); return s; };
    overlaySeriesMap.bbUpper = addLine(bb.upper, 'rgba(96,165,250,0.65)', 0);
    overlaySeriesMap.bbLower = addLine(bb.lower, 'rgba(96,165,250,0.65)', 0);
    overlaySeriesMap.bbMid   = addLine(bb.mid,   'rgba(71,85,105,0.8)',   2);
  }

  const lastDate = data[data.length - 1].date;
  const oneYAgo = new Date(lastDate); oneYAgo.setFullYear(oneYAgo.getFullYear() - 1);
  const fromStr = oneYAgo.toISOString().split('T')[0];
  if (data.some(d => d.date <= fromStr)) lwChart.timeScale().setVisibleRange({ from: fromStr, to: lastDate });
  else lwChart.timeScale().fitContent();

  function updateRangeReturn() {
    const range = lwChart.timeScale().getVisibleRange();
    if (!range) return;
    const fromD = data.find(d => d.date >= range.from);
    let toD = null;
    for (let i = data.length - 1; i >= 0; i--) { if (data[i].date <= range.to) { toD = data[i]; break; } }
    if (!fromD || !toD || fromD === toD) return;
    const ret = (toD.close / fromD.close - 1) * 100;
    const pctEl = document.getElementById('chart-pct');
    if (pctEl) { pctEl.textContent = (ret >= 0 ? '+' : '') + ret.toFixed(1) + '%'; pctEl.className = 'chart-pct ' + (ret >= 0 ? 'ret-pos' : 'ret-neg'); }
    const lblEl = document.getElementById('chart-period-label');
    if (lblEl) lblEl.textContent = fromD.date + ' ~ ' + toD.date;
  }
  lwChart.timeScale().subscribeVisibleTimeRangeChange(range => {
    updateRangeReturn();
    if (!range || isSyncing) return;
    isSyncing = true;
    Object.values(subChartMap).forEach(sc => { try { sc.chart.timeScale().setVisibleRange(range); } catch(e) {} });
    isSyncing = false;
  });
  setTimeout(updateRangeReturn, 80);

  const tooltip = document.getElementById('price-tooltip');
  lwChart.subscribeCrosshairMove(param => {
    if (!tooltip) return;
    if (!param.time || !param.point || !lwSeries || !param.seriesData.get(lwSeries)) { tooltip.style.display = 'none'; return; }
    const pt = param.seriesData.get(lwSeries);
    let html;
    if (type === 'candle') {
      const up = pt.close >= pt.open, c = up ? '#4ade80' : '#f87171';
      html = `<div style="color:#475569;font-size:0.7rem;margin-bottom:3px">${param.time}</div><table style="border-spacing:0 2px">
        <tr><td style="color:#475569;padding-right:10px">O</td><td style="color:${c};font-weight:700">${pt.open.toFixed(2)}</td></tr>
        <tr><td style="color:#475569;padding-right:10px">H</td><td style="color:#4ade80">${pt.high.toFixed(2)}</td></tr>
        <tr><td style="color:#475569;padding-right:10px">L</td><td style="color:#f87171">${pt.low.toFixed(2)}</td></tr>
        <tr><td style="color:#475569;padding-right:10px">C</td><td style="color:${c};font-weight:700">${pt.close.toFixed(2)}</td></tr></table>`;
    } else {
      html = `<div style="color:#475569;font-size:0.7rem;margin-bottom:2px">${param.time}</div><div style="color:#4ade80;font-weight:800;font-size:1rem">${pt.value.toFixed(2)}</div>`;
    }
    tooltip.innerHTML = html; tooltip.style.display = 'block';
    let x = param.point.x + 14, y = Math.max(4, param.point.y - 10);
    if (x + 140 > container.clientWidth) x = param.point.x - 144;
    tooltip.style.left = x + 'px'; tooltip.style.top = y + 'px';
  });

  new ResizeObserver(() => { if (lwChart) lwChart.applyOptions({ width: container.clientWidth }); }).observe(container);
}

function setChartType(type) {
  currentChartType = type;
  document.querySelectorAll('.chart-type-btn').forEach(b => b.classList.toggle('active', b.dataset.type === type));
  if (priceHistory) {
    initPriceChart(document.getElementById('chart-container'), priceHistory, type);
    buildSubCharts();
  }
}

// ── 지표 시계열 계산 ──────────────────────────────────────────────────────────
function calcZScoreSeries(adj) {
  const w = 200, s = [];
  for (let i = w - 1; i < adj.length; i++) {
    const sl = adj.slice(i - w + 1, i + 1);
    const mean = sl.reduce((a, b) => a + b, 0) / w;
    const std  = Math.sqrt(sl.reduce((a, b) => a + (b - mean) ** 2, 0) / w);
    s.push(std === 0 ? 0 : (adj[i] - mean) / std);
  }
  return s;
}
function calcRSISeries(adj, period = 14) {
  if (adj.length < period + 1) return [];
  const gains = [], losses = [];
  for (let i = 1; i < adj.length; i++) {
    const d = adj[i] - adj[i - 1];
    gains.push(Math.max(0, d));
    losses.push(Math.max(0, -d));
  }
  const alpha = 1 / period;
  let sumG = 0, sumL = 0;
  for (let i = 0; i < period; i++) { sumG += gains[i]; sumL += losses[i]; }
  let avgG = sumG / period, avgL = sumL / period;
  const s = [avgL === 0 ? 100 : 100 - 100 / (1 + avgG / avgL)];
  for (let i = period; i < gains.length; i++) {
    avgG = avgG * (1 - alpha) + gains[i] * alpha;
    avgL = avgL * (1 - alpha) + losses[i] * alpha;
    s.push(avgL === 0 ? 100 : 100 - 100 / (1 + avgG / avgL));
  }
  return s;
}
function calc52WRangeSeries(adj) {
  const w = 252, s = [];
  for (let i = w - 1; i < adj.length; i++) {
    const sl = adj.slice(i - w + 1, i + 1);
    const lo = Math.min(...sl), hi = Math.max(...sl);
    s.push(hi === lo ? 50 : (adj[i] - lo) / (hi - lo) * 100);
  }
  return s;
}
function calcMDDSeries(adj) {
  const w = 252, s = [];
  for (let i = w - 1; i < adj.length; i++) {
    const hi = Math.max(...adj.slice(i - w + 1, i + 1));
    s.push((adj[i] / hi - 1) * 100);
  }
  return s;
}
function calcMetricSeries(adj, metricType) {
  let s;
  if      (metricType === 'zscore')   s = calcZScoreSeries(adj);
  else if (metricType === 'rsi')      s = calcRSISeries(adj);
  else if (metricType === 'range52w') s = calc52WRangeSeries(adj);
  else if (metricType === 'mdd')      s = calcMDDSeries(adj);
  else return [];
  return s.slice(-252);
}
function calcMASeries(adj, period) {
  if (!priceHistory || adj.length < period) return [];
  const result = [];
  for (let i = period - 1; i < adj.length; i++) {
    const sl = adj.slice(i - period + 1, i + 1);
    result.push({ time: priceHistory[i].date, value: sl.reduce((a, b) => a + b, 0) / period });
  }
  return result;
}
function calcBBData(adj, period = 20, mult = 2) {
  if (!priceHistory || adj.length < period) return { upper: [], lower: [], mid: [] };
  const upper = [], lower = [], mid = [];
  for (let i = period - 1; i < adj.length; i++) {
    const sl = adj.slice(i - period + 1, i + 1);
    const mean = sl.reduce((a, b) => a + b, 0) / period;
    const std = Math.sqrt(sl.reduce((a, b) => a + (b - mean) ** 2, 0) / period);
    const t = priceHistory[i].date;
    upper.push({ time: t, value: mean + mult * std });
    lower.push({ time: t, value: mean - mult * std });
    mid.push({ time: t, value: mean });
  }
  return { upper, lower, mid };
}
function getSubChartData(key) {
  if (!priceHistory) return [];
  const adj = priceHistory.map(d => d.close);
  if (key === 'volume') {
    return priceHistory.map(d => ({
      time: d.date, value: d.volume ?? 0,
      color: (d.close >= (d.open ?? d.close)) ? 'rgba(74,222,128,0.45)' : 'rgba(248,113,113,0.45)',
    }));
  }
  let series;
  if      (key === 'rsi')      series = calcRSISeries(adj);
  else if (key === 'zscore')   series = calcZScoreSeries(adj);
  else if (key === 'range52w') series = calc52WRangeSeries(adj);
  else if (key === 'mdd')      series = calcMDDSeries(adj);
  else return [];
  const startIdx = priceHistory.length - series.length;
  return series.map((val, i) => ({ time: priceHistory[startIdx + i].date, value: val }));
}

function buildSubCharts() {
  Object.values(subChartMap).forEach(sc => { try { sc.chart.remove(); } catch(e) {} });
  subChartMap = {};
  const wrapper = document.getElementById('sub-charts-wrapper');
  if (!wrapper) return;
  wrapper.innerHTML = '';
  if (!priceHistory || !lwChart) return;

  const order = ['volume','rsi','zscore','range52w','mdd'];
  const keys  = order.filter(k => activeIndicators[k]);

  lwChart.applyOptions({ timeScale: { visible: keys.length === 0 } });
  if (keys.length === 0) return;

  const mainRange = lwChart.timeScale().getVisibleRange();

  keys.forEach((key, idx) => {
    const cfg = SUBCHART_CONF[key];
    const isLast = idx === keys.length - 1;

    const wrap = document.createElement('div');
    wrap.className = 'sub-chart-wrap';
    const labelEl = document.createElement('div');
    labelEl.className = 'sub-chart-label';
    labelEl.textContent = cfg.label;
    wrap.appendChild(labelEl);
    const chartEl = document.createElement('div');
    chartEl.style.cssText = `width:100%;height:${cfg.height}px`;
    wrap.appendChild(chartEl);
    wrapper.appendChild(wrap);

    const chart = LightweightCharts.createChart(chartEl, {
      width: wrapper.clientWidth || 600, height: cfg.height,
      layout: { background: { type:'solid', color:'transparent' }, textColor:'#64748b', fontSize:10 },
      grid: { vertLines: { color:'rgba(255,255,255,0.03)' }, horzLines: { color:'rgba(255,255,255,0.04)' } },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      rightPriceScale: { borderColor:'rgba(255,255,255,0.08)', minimumWidth:50 },
      timeScale: { borderColor:'rgba(255,255,255,0.08)', visible: isLast, timeVisible: isLast },
      handleScroll: { mouseWheel:true, pressedMouseMove:true, horzTouchDrag:true },
      handleScale: { mouseWheel:true, pinch:true },
    });

    const data = getSubChartData(key);
    let series;
    if (key === 'volume') {
      series = chart.addHistogramSeries({ color: cfg.color, priceFormat: { type:'volume' } });
      chart.priceScale('right').applyOptions({ scaleMargins: { top:0.1, bottom:0 } });
    } else {
      series = chart.addLineSeries({ color:cfg.color, lineWidth:1.5, priceLineVisible:false, lastValueVisible:true });
      cfg.refs.forEach(r => series.createPriceLine({ price:r.v, color:r.c, lineWidth:1, lineStyle:1, axisLabelVisible:false }));
    }
    series.setData(data);

    chart.timeScale().subscribeVisibleTimeRangeChange(range => {
      if (!range || isSyncing) return;
      isSyncing = true;
      try { if (lwChart) lwChart.timeScale().setVisibleRange(range); } catch(e) {}
      Object.entries(subChartMap).forEach(([k, sc]) => { if (k !== key) try { sc.chart.timeScale().setVisibleRange(range); } catch(e) {} });
      isSyncing = false;
    });

    new ResizeObserver(() => chart.applyOptions({ width: chartEl.clientWidth })).observe(chartEl);
    subChartMap[key] = { chart, series };
  });

  if (mainRange) {
    setTimeout(() => {
      isSyncing = true;
      Object.values(subChartMap).forEach(sc => { try { sc.chart.timeScale().setVisibleRange(mainRange); } catch(e) {} });
      isSyncing = false;
    }, 60);
  }
}

function toggleIndicator(key, enabled) {
  activeIndicators[key] = enabled;
  if (['ma20','ma50','ma200','bb'].includes(key)) {
    if (!lwChart || !priceHistory) return;
    const overAdj = priceHistory.map(d => d.close);
    if (key === 'bb') {
      ['bbUpper','bbLower','bbMid'].forEach(k => {
        if (overlaySeriesMap[k]) { try { lwChart.removeSeries(overlaySeriesMap[k]); } catch(e) {} delete overlaySeriesMap[k]; }
      });
      if (enabled) {
        const bb = calcBBData(overAdj);
        const addLine = (d, c, ls) => { const s = lwChart.addLineSeries({ color:c, lineWidth:1, priceLineVisible:false, crosshairMarkerVisible:false, lastValueVisible:false, lineStyle:ls }); s.setData(d); return s; };
        overlaySeriesMap.bbUpper = addLine(bb.upper, 'rgba(96,165,250,0.65)', 0);
        overlaySeriesMap.bbLower = addLine(bb.lower, 'rgba(96,165,250,0.65)', 0);
        overlaySeriesMap.bbMid   = addLine(bb.mid,   'rgba(71,85,105,0.8)',   2);
      }
    } else {
      if (overlaySeriesMap[key]) { try { lwChart.removeSeries(overlaySeriesMap[key]); } catch(e) {} delete overlaySeriesMap[key]; }
      if (enabled) {
        const cfg = OVERLAY_CONF[key];
        const s = lwChart.addLineSeries({ color:cfg.color, lineWidth:1.5, priceLineVisible:false, crosshairMarkerVisible:false, lastValueVisible:false });
        s.setData(calcMASeries(overAdj, cfg.period));
        overlaySeriesMap[key] = s;
      }
    }
  } else {
    buildSubCharts();
  }
}
function toggleIndicatorPanel() {
  const panel = document.getElementById('ind-panel');
  const btn   = document.getElementById('ind-settings-btn');
  if (!panel) return;
  const isOpen = panel.classList.toggle('open');
  if (btn) btn.classList.toggle('active', isOpen);
}

function generateChartSVG(ticker, cagr, vol, n) {
  const prices = generatePrices(ticker, cagr, vol, n);
  const N = prices.length;
  const W = 700, H = 200;
  const P = { t: 18, r: 10, b: 30, l: 50 };
  const cw = W - P.l - P.r, ch = H - P.t - P.b;

  const minP = Math.min(...prices) * 0.998;
  const maxP = Math.max(...prices) * 1.002;
  const rng  = maxP - minP || 1;
  const toX  = i => P.l + (i / (N - 1)) * cw;
  const toY  = p => P.t + ch - ((p - minP) / rng) * ch;

  const pts = prices.map((p, i) => toX(i).toFixed(1) + ',' + toY(p).toFixed(1));
  const line = 'M ' + pts.join(' L ');
  const area = line + ' L ' + toX(N-1).toFixed(1) + ',' + (P.t+ch) + ' L ' + P.l + ',' + (P.t+ch) + ' Z';
  const isUp = prices[N-1] >= prices[0];
  const col  = isUp ? '#4ade80' : '#f87171';
  const pct  = ((prices[N-1] / prices[0] - 1) * 100).toFixed(1);

  const gridY = [0, 0.25, 0.5, 0.75, 1.0].map(f => {
    const yv  = (P.t + ch - f * ch).toFixed(1);
    const pv  = ((minP + f * rng) / prices[0] - 1) * 100;
    const lbl = (pv > 0 ? '+' : '') + pv.toFixed(0) + '%';
    return `<line x1="${P.l}" y1="${yv}" x2="${P.l+cw}" y2="${yv}" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
    <text x="${P.l-6}" y="${(+yv+3.5).toFixed(1)}" text-anchor="end" font-size="10" fill="rgba(100,116,139,0.7)" font-family="monospace">${lbl}</text>`;
  }).join('');

  const xPts = n <= 22 ? ['4주 전','3주 전','2주 전','1주 전','현재']
             : n <= 65 ? ['3개월 전','2개월 전','1개월 전','현재','']
             : n <= 130? ['6개월 전','4개월 전','2개월 전','현재','']
             :           ['1년 전','9개월 전','6개월 전','3개월 전','현재'];
  const gridX = xPts.map((lbl, i) => {
    const xv = (P.l + (i / (xPts.length - 1)) * cw).toFixed(1);
    return `<text x="${xv}" y="${H-5}" text-anchor="middle" font-size="10" fill="rgba(100,116,139,0.6)" font-family="Inter,sans-serif">${lbl}</text>`;
  }).join('');

  return {
    svg: `<svg viewBox="0 0 ${W} ${H}" width="100%" height="100%" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${col}" stop-opacity="0.18"/><stop offset="100%" stop-color="${col}" stop-opacity="0"/></linearGradient></defs>
  ${gridY}${gridX}
  <path d="${area}" fill="url(#ag)"/>
  <path d="${line}" stroke="${col}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="${P.l}" cy="${toY(prices[0]).toFixed(1)}" r="3" fill="${col}" opacity="0.5"/>
  <circle cx="${(P.l+cw).toFixed(1)}" cy="${toY(prices[N-1]).toFixed(1)}" r="4" fill="${col}"/>
</svg>`, pct, isUp
  };
}
