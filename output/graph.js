// ── 상수 ──────────────────────────────────────────────
const DEFAULT_R    = 0.90;
const STATIC_THRESHOLD = 0.90; // r 이하면 정적 렌더링 모드
const LINK_DIST_K  = 800;   // link distance = (1 - r) * K  →  r=1: 0px, r=0: 800px
const LINK_STRENGTH_K = 0.8; // link strength = (r - 0.65) * K  →  r=0.95: 0.24

// ── 전역 상태 ──────────────────────────────────────────
let allNodes    = [];
let allLinks    = [];
let sectorMeta  = {};
let Graph;
let ETF_META = {};
let storeMinR   = 0.70;
let currentR    = DEFAULT_R;
let hiddenSectors = new Set();
let hideShortHistory = false; // 해제된 섯터 ID 입니다
let nodeScaleMult = 4.0; // 노드 크기 배율 (슬라이더 제어)

let hoverNode        = null;
let selectedNode     = null;
let hoverSector      = null;
let highlightNodeIds = new Set();
let searchTicker     = '';
let hideLegacy       = false;
let focusSector      = null;   // 레전드 클릭으로 선택된 섹터 ID (or 'SS_<id>')
let superSectorMode  = false;  // 슈퍼섹터 통합 색상 토글
let superSectorMeta  = {};     // graph_data.json 에서 로드

// ── 색상 조절 헬퍼 ──────────────────────────────
function darkenColor(hex, percent) {
  if (!hex || hex[0] !== '#') return hex;
  const num = parseInt(hex.slice(1), 16),
        amt = Math.round(2.55 * percent),
        R = (num >> 16) - amt,
        G = (num >> 8 & 0x00FF) - amt,
        B = (num & 0x0000FF) - amt;
  return "#" + (0x1000000 + (R<255?R<0?0:R:255)*0x10000 + (G<255?G<0?0:G:255)*0x100 + (B<255?B<0?0:B:255)).toString(16).slice(1);
}

// ── 색상 / 크기 함수 ─────────────────────────────────
function sectorColor(sid) {
  return (sectorMeta[sid] || {}).color || '#888888';
}

function effectiveColor(node) {
  // 슈퍼섹터 모드일 때 해당 섹터는 슈퍼섹터 색으로 통일
  if (superSectorMode) {
    const ss = (sectorMeta[node.s] || {}).ss;
    if (ss && superSectorMeta[ss]) return superSectorMeta[ss].color;
  }
  return sectorColor(node.s);
}

function getNodeColor(node) {
  const base = effectiveColor(node);
  if (searchTicker && node.id === searchTicker) return '#ffffff';
  if (hoverSector) {
    const s = hoverSector;
    const active = s.startsWith('SS_') ? ((sectorMeta[node.s] || {}).ss === s.slice(3)) : (node.s === s);
    return active ? base : base + '18';
  }
  if (hoverNode) {
    if (node === hoverNode)             return base;
    if (highlightNodeIds.has(node.id)) return base;
    return base + '22';  // \ud76c\ub9ac\uac15
  }
  if (focusSector) {
    const s = focusSector;
    const active = s.startsWith('SS_') ? ((sectorMeta[node.s] || {}).ss === s.slice(3)) : (node.s === s);
    return active ? base : base + '18';
  }
  return base;
}

function getNodeVal(node) {
  // 파워 스케일 (0.55승): AUM 차이가 눈에 띄게 나도록
  // $0.1B→1  $1B→1   $10B→3.5  $50B→10  $100B→12  $600B→45
  const aumB = node.a || 0;
  return Math.max(1, Math.pow(aumB + 0.01, 0.85)) * nodeScaleMult;
}

function hexToRgba(hex, alpha) {
  if (!hex || hex[0] !== '#') return `rgba(148,163,184,${alpha})`;
  const r = parseInt(hex.slice(1, 3), 16),
        g = parseInt(hex.slice(3, 5), 16),
        b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function getLinkColor(link) {
  const sn = typeof link.source === 'object' ? link.source : null;
  const tn = typeof link.target === 'object' ? link.target : null;
  const sid = sn ? sn.id : link.source;
  const tid = tn ? tn.id : link.target;

  const t = Math.max(0, (link.r - storeMinR) / (1 - storeMinR));
  const sameSector = (sn && tn && sn.s === tn.s);
  const baseColorHex = sameSector ? sectorColor(sn.s) : '#94a3b8';

  if (hoverSector) {
    const s = hoverSector;
    const active = s.startsWith('SS_') ? ((sn && (sectorMeta[sn.s] || {}).ss === s.slice(3)) || (tn && (sectorMeta[tn.s] || {}).ss === s.slice(3))) : ((sn && sn.s === s) || (tn && tn.s === s));
    if (active) return hexToRgba(baseColorHex, 0.15 + t * 0.40);
    return 'rgba(255,255,255,0.01)';
  }
  if (hoverNode) {
    const active = sid === hoverNode.id || tid === hoverNode.id;
    if (!active) return 'rgba(255,255,255,0.02)';
    const tLink = Math.max(0, Math.min(1, (link.r - 0.8) / 0.2));
    return `rgba(${Math.round(255*tLink)},${Math.round(120+80*tLink)},${Math.round(255*(1-tLink))},0.85)`;
  }
  if (focusSector) {
    const s = focusSector;
    const active = s.startsWith('SS_') ? ((sn && (sectorMeta[sn.s] || {}).ss === s.slice(3)) || (tn && (sectorMeta[tn.s] || {}).ss === s.slice(3))) : ((sn && sn.s === s) || (tn && tn.s === s));
    if (active) return hexToRgba(baseColorHex, 0.15 + t * 0.40);
    return 'rgba(255,255,255,0.01)';
  }

  // 기본 상태
  const alpha = sameSector ? (0.08 + t * 0.25) : (0.04 + t * 0.18);
  return hexToRgba(baseColorHex, alpha);
}

function getLinkWidth(link) {
  if (hoverNode) {
    const sid = typeof link.source === 'object' ? link.source.id : link.source;
    const tid = typeof link.target === 'object' ? link.target.id : link.target;
    return (sid === hoverNode.id || tid === hoverNode.id) ? 1.8 : 0.1;
  }
  return Math.max(0.1, (link.r - 0.88) * 4);
}

// ── 통계 업데이트 ─────────────────────────────────────
function updateStats(nNodes, nLinks, simRunning) {
  const el = document.getElementById('stats');
  el.innerHTML =
    `${I18n.t('graph.nodes',{count:'<b>'+nNodes.toLocaleString()+'</b>'})} &nbsp;|&nbsp; ${I18n.t('graph.edges',{count:'<b>'+nLinks.toLocaleString()+'</b>'})}` +
    (simRunning ? `<br><span class="sim-running">${I18n.t('graph.layout')}</span>` : '');
}

function fmtAUM(b) {
  if (b >= 100) return `$${b.toFixed(0)}B`;
  if (b >= 1)   return `$${b.toFixed(1)}B`;
  if (b >= 0.1) return `$${(b * 1000).toFixed(0)}M`;
  return '<$100M';
}

// ── 레전드 렌더 ──────────────────────────────────────
const SVG_EYE_ON  = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
const SVG_EYE_OFF = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

function renderLegend() {
  const AC_ORDER = ['EQUITY','FIXED_INCOME','REAL_ASSETS','ALTERNATIVE','THEMATIC'];
  const AC_KO = {
    EQUITY: '주식', FIXED_INCOME: '채권',
    REAL_ASSETS: '실물자산', ALTERNATIVE: '대안', THEMATIC: '테마'
  };
  const grouped = {};
  for (const [sid, s] of Object.entries(sectorMeta)) {
    (grouped[s.ac] = grouped[s.ac] || []).push({ sid, ...s });
  }

  let html = '';
  for (const ac of AC_ORDER) {
    if (!grouped[ac]) continue;
    html += `<div class="legend-ac">${AC_KO[ac]}</div>`;

    let renderedSS = new Set();
    for (const s of grouped[ac]) {
      const ss = s.ss;  // 슈퍼섹터 ID (있으면)
      if (superSectorMode && ss && superSectorMeta[ss]) {
        // 슈퍼섹터 통합 항목 (처음 한 번만 렌더)
        if (!renderedSS.has(ss)) {
          renderedSS.add(ss);
          const ssDef = superSectorMeta[ss];
          const isHidden = hiddenSectors.has('SS_' + ss);
          html += `
            <div class="legend-item${isHidden ? ' hidden-sector' : ''}" data-sid="SS_${ss}" title="${ssDef.name_en}">
              <div class="legend-dot" style="background:${ssDef.color}"></div>
              <span class="legend-text">${ssDef.name}</span>
              <button class="legend-toggle" data-toggle="SS_${ss}" title="토글">${isHidden ? SVG_EYE_OFF : SVG_EYE_ON}</button>
            </div>`;
        }
      } else {
        // 개별 섹터 항목
        const color = (superSectorMode && ss && superSectorMeta[ss])
          ? superSectorMeta[ss].color : s.color;
        const isHidden = hiddenSectors.has(s.sid);
        html += `
          <div class="legend-item${isHidden ? ' hidden-sector' : ''}" data-sid="${s.sid}" title="${s.name_en}">
            <div class="legend-dot" style="background:${color}"></div>
            <span class="legend-text">${s.name}</span>
            <button class="legend-toggle" data-toggle="${s.sid}" title="토글">${isHidden ? SVG_EYE_OFF : SVG_EYE_ON}</button>
          </div>`;
      }
    }
  }
  const container = document.getElementById('legend-items');
  container.innerHTML = html;
}

// ── 레이아웃 오버레이 제어 ────────────────────────────
function showLayoutOverlay(show, msg) {
  const el = document.getElementById('layout-overlay');
  el.style.display = show ? 'flex' : 'none';
  if (msg) document.getElementById('layout-msg').textContent = msg;
}

// ── 필터 적용 (슬라이더 변경 시) ───────────────────────
function applyFilter(minR) {
  currentR = minR;

  // 신규 등장 노드 좌표 초기화 (레거시 토글 시 undefined → (0,0) 폭발 방지)
  const currentlyVisibleIds = new Set(
    (Graph && Graph.graphData ? Graph.graphData().nodes : []).map(n => n.id)
  );
  let cx = 0, cy = 0, cnt = 0;
  allNodes.forEach(n => {
    if (currentlyVisibleIds.has(n.id) && n.x !== undefined) {
      cx += n.x; cy += n.y; cnt++;
    }
  });
  if (cnt > 0) { cx /= cnt; cy /= cnt; }
  allNodes.forEach(n => {
    if (!currentlyVisibleIds.has(n.id) && n.x === undefined) {
      n.x = cx + (Math.random() - 0.5) * 100;
      n.y = cy + (Math.random() - 0.5) * 100;
    }
  });

  const visibleNodes = allNodes
    .filter(n => !hideLegacy || !n.l)
    .filter(n => !hideShortHistory || !n.sh)
    .filter(n => !hiddenSectors.has(n.s));
  const visibleIds   = new Set(visibleNodes.map(n => n.id));
  const filtered     = allLinks.filter(l => l.r >= minR && visibleIds.has(l.s) && visibleIds.has(l.t));
  Graph.graphData({ nodes: visibleNodes, links: filtered });

  // ── 노드/엣지 수에 비례하는 동적 물리 파라미터 ──
  const nNodes = visibleNodes.length;
  const nEdges = filtered.length;

  // 1) 반발력: 노드가 많을수록, 임계값이 낮을수록 더 세게 밀어내야 공간 확보
  //    기본 r=0.95 → ~100노드 → charge -200
  //    r=0.70 → ~1300노드 → charge -800 정도로 스케일
  const baseCharge = -600; // 반발력 약홄 조절 (-80 → -100)
  const chargeScale = Math.max(1, Math.pow(nNodes / 100, 0.6)); // 반발력 산출 강화 (0.5 → 0.6 승)
  const charge = baseCharge * chargeScale;

  // 2) 링크 거리: r이 낮을수록 이미 링크 인력이 세지므로 distance를 키워 균형 유지
  //    기본 LINK_DIST_K=800 → r=0.95일 때 (1-0.95)*800 = 40px
  //    r=0.70일 때 (1-0.70)*800 = 240px → 충분히 멀어짐
  const distK = LINK_DIST_K * Math.max(1, Math.pow((1 - minR) * 15, 1.2)); // 확장산식 고도화 (8 → 15x 파워) // 확장성 강화 (3 → 5)

  // 3) 링크 강도: 엣지가 많을수록 약하게 해야 뭉침 방지
  const edgeDensity = nEdges / Math.max(1, nNodes);
  const strengthScale = Math.max(0.01, 1 / Math.max(1, edgeDensity / 5)); // 바닥 제한 완화 (0.1 → 0.01)

  const lf = Graph.d3Force('link');
  if (lf) {
    lf.distance(l => Math.max(10, (1 - (l.r || 0.9)) * distK))
      .strength(l => Math.max(0, ((l.r || 0.9) - 0.65) * LINK_STRENGTH_K * strengthScale));
  }

  // 4) Repulsion
  Graph.d3Force('charge').strength(charge);

  // 5) Collision (Suggestion 5) - Prevent node overlap
  Graph.d3Force('collide', d3.forceCollide().radius(n => Math.sqrt(getNodeVal(n)) * 4 + 1.5).iterations(2));

  // 6) Soft Boundary (Suggestion 3) - Keep graph within reach
  Graph.d3Force('x', d3.forceX().strength(0.015));
  Graph.d3Force('y', d3.forceY().strength(0.015));

  // ── 하이브리드 렌더링 모드 ──────────────────────────────
  if (minR < STATIC_THRESHOLD) {
    // 정적 모드: 빠른 감쇠로 즉시 수렴, 오버레이 표시
    const warmTicks = Math.round(50 + (1 - minR) * 500); // r=0.89→55틱, r=0.70→200틱
    const nodeCount = visibleNodes.length;
    const msg = `레이아웃 계산 중... (${nodeCount.toLocaleString()}개 노드)`;
    showLayoutOverlay(true, msg);
    Graph.d3AlphaDecay(0.02).d3VelocityDecay(0.5).d3AlphaMin(0.002).cooldownTime(10000); // 더 오래, 더 멀리 까지 배치
  } else {
    // 애니메이션 모드: 느린 감쇠로 부드럽게 수렴
    showLayoutOverlay(false);
    Graph.d3AlphaDecay(0.04).d3VelocityDecay(0.55).d3AlphaMin(0.01).cooldownTime(8000);
  }

  Graph.d3ReheatSimulation();
  updateStats(allNodes.length, filtered.length, true);
}

// ── 데이터 로드 & 그래프 초기화 ──────────────────────
const progFill = document.getElementById('progress-fill');
progFill.style.width = '20%';

fetch('graph_data.json')
  .then(res => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    progFill.style.width = '55%';
    return res.json();
  })
  .then(data => {
    progFill.style.width = '85%';

    allNodes        = data.nodes;
    allLinks        = data.links;
    sectorMeta      = data.sectors;
    superSectorMeta = data.super_sectors || {};
    storeMinR       = data.meta.store_min_r;

    // 오버라이드 적용 함수 (localStorage + 서버)
    function applyOverrides(ov) {
      if (!ov || !Object.keys(ov).length) return;
      allNodes.forEach(node => {
        if (node.id in ov && 'is_legacy' in ov[node.id])
          node.l = ov[node.id].is_legacy ? 1 : 0;
      });
    }
    function updateLegacyCount() {
      const lc = allNodes.filter(n => n.l).length;
      document.getElementById('legacy-count').textContent = `(${lc}개)`;
      const sc = allNodes.filter(n => n.sh).length;
      document.getElementById('sh-count').textContent = `(${sc}개)`;
    }

    // 1) localStorage 오버라이드 즉시 반영
    try {
      applyOverrides(JSON.parse(localStorage.getItem('corryu_user_overrides') || '{}'));
    } catch(e) {}
    updateLegacyCount();

    // 2) 서버 오버라이드 비동기 반영 (다기기 동기화)
    fetch('/api/sync?t=' + Date.now()).then(r => r.ok ? r.json() : null).then(d => {
      if (!d || !d.content) return;
      const { _meta, ...cleanOv } = d.content;
      if (Object.keys(cleanOv).length) {
        applyOverrides(cleanOv);
        updateLegacyCount();
        localStorage.setItem('corryu_user_overrides', JSON.stringify(cleanOv));
        if (_meta && _meta.ts) localStorage.setItem('corryu_overrides_ts', String(_meta.ts));
      }
    }).catch(() => {});

    // 슬라이더 최솟값 동기화
    const slider = document.getElementById('r-slider');
    const minInt = Math.round(storeMinR * 100);
    slider.min = minInt;
    document.getElementById('r-min-label').textContent = storeMinR.toFixed(2);

    renderLegend();

    // ── Legend Click (단일 등록 — renderLegend 내부 중복 등록 방지) ───
    const legendContainer = document.getElementById('legend-items');
    legendContainer.addEventListener('click', e => {
      const toggleBtn = e.target.closest('.legend-toggle');
      if (toggleBtn) {
        e.stopPropagation();
        const sid = toggleBtn.dataset.toggle;
        if (hiddenSectors.has(sid)) hiddenSectors.delete(sid);
        else hiddenSectors.add(sid);
        renderLegend();
        if (Graph) applyFilter(currentR);
        return;
      }
      const item = e.target.closest('.legend-item');
      if (!item) return;
      const sid = item.dataset.sid;
      focusSector = focusSector === sid ? null : sid;
      legendContainer.querySelectorAll('.legend-item').forEach(el => {
        el.classList.remove('active', 'dimmed');
        if (focusSector) {
          if (el.dataset.sid === focusSector) el.classList.add('active');
          else el.classList.add('dimmed');
        }
      });
      if (Graph) Graph.refresh();
    });

    // ── Legend Hover Highlights (New Delegated) ─────────
    legendContainer.addEventListener('mouseover', e => {
      const item = e.target.closest('.legend-item');
      const sid = item ? item.dataset.sid : null;
      if (hoverSector !== sid) {
        hoverSector = sid;
        // console.log('Hover Sector:', sid);
        if (Graph) {
           Graph.nodeRelSize(Graph.nodeRelSize()); // Re-evaluate attributes
           Graph.refresh();
        }
      }
    });
    legendContainer.addEventListener('mouseleave', () => {
      if (hoverSector !== null) {
        hoverSector = null;
        if (Graph) Graph.refresh();
      }
    });

    // ── ForceGraph 초기화 ────────────────────────────
    Graph = ForceGraph()(document.getElementById('graph-container'))
      .backgroundColor('#0d1117')
      .nodeId('id')
      .linkSource('s')
      .linkTarget('t')
      .nodeLabel(() => '')          // 커스텀 툴팁 사용
      .nodeVal(getNodeVal)
      .nodeCanvasObject((node, ctx, globalScale) => {
        const r = Math.sqrt(getNodeVal(node)) * 4 * Math.pow(1 / Math.max(0.1, globalScale), 0.45); // Ratio-preserving zoom scaling
        const color = getNodeColor(node);

        // 그림자 효과 (호버 시에만)
        if (node === hoverNode) {
          ctx.shadowColor = 'rgba(0,0,0,0.5)';
          ctx.shadowBlur = 10 / globalScale;
        }

        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
        ctx.fillStyle = color;
        ctx.fill();

        // 테두리 (호버 시)
        if (node === hoverNode) {
          ctx.shadowBlur = 0;
          const bc = darkenColor(effectiveColor(node), 40);
          ctx.strokeStyle = bc;
          ctx.lineWidth = 2.5 / globalScale;
          ctx.stroke();

          // 내부 하이라이트 (약간 밝은 점)
          ctx.beginPath();
          ctx.arc(node.x, node.y, r * 0.9, 0, 2 * Math.PI, false);
          ctx.strokeStyle = 'rgba(255,255,255,0.2)';
          ctx.lineWidth = 1 / globalScale;
          ctx.stroke();
        }
      })
      .onRenderFramePost((ctx, globalScale) => {
        const anchorNodes = (Graph.graphData().nodes || []).filter(n => n.anchor);
        if (!anchorNodes.length) return;
        const fontSize = Math.max(12, 14 / Math.max(1, Math.log2(globalScale + 1)));
        ctx.font = `800 ${fontSize}px 'SF Mono',Consolas,Menlo,monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        anchorNodes.forEach(node => {
          const r = Math.sqrt(getNodeVal(node)) * 4 * Math.pow(1 / Math.max(0.1, globalScale), 0.45); // Ratio-preserving zoom scaling
          const x = node.x, y = node.y + r + 3;
          // 배경 박스
          const metrics = ctx.measureText(node.id);
          const tw = metrics.width, th = fontSize;
          const pad = 3;
          ctx.fillStyle = 'rgba(13,17,23,0.82)';
          ctx.fillRect(x - tw/2 - pad, y - pad/2, tw + pad*2, th + pad);
          // 텍스트
          ctx.fillStyle = '#ffffff';
          ctx.fillText(node.id, x, y);
        });
      })
      .linkColor(getLinkColor)
      .linkWidth(getLinkWidth)
      .linkCurvature(0)
      .d3AlphaDecay(0.04)
      .d3VelocityDecay(0.55)
      .d3AlphaMin(0.01)
      .cooldownTime(8000)
      .enableNodeDrag(false)
      .enableZoomInteraction(true)
      .onEngineStop(() => {
        showLayoutOverlay(false);
        const gd = Graph.graphData();
        updateStats(gd.nodes.length, gd.links.length, false);
      })
      .onNodeHover(node => {
        hoverNode = node || selectedNode || null;
        highlightNodeIds.clear();

        if (node) {
          highlightNodeIds.add(node.id);
          (Graph.graphData().links || []).forEach(l => {
            const s = typeof l.source === 'object' ? l.source.id : l.source;
            const t = typeof l.target === 'object' ? l.target.id : l.target;
            if (s === node.id || t === node.id) {
              highlightNodeIds.add(s);
              highlightNodeIds.add(t);
            }
          });

          // 이웃 수 계산
          const neighborCount = highlightNodeIds.size - 1;
          const sc = sectorMeta[node.s] || {};
          document.getElementById('tt-ticker').style.color = sc.color || '#e6edf3';
          document.getElementById('tt-ticker').textContent = node.id;
          document.getElementById('tt-name').textContent   = node.n;
          const scName = (I18n.locale()==='ko'||!sc.name_en) ? sc.name : sc.name_en;
          document.getElementById('tt-meta').innerHTML = `
            <div class="tt-row">
              <span class="tt-key">${I18n.t('graph.tooltip.sector')}</span>
              <span class="tt-val" style="color:${sc.color}">${scName || node.s}</span>
            </div>
            <div class="tt-row">
              <span class="tt-key">AUM</span>
              <span class="tt-val">${fmtAUM(node.a)}</span>
            </div>
            <div class="tt-row">
              <span class="tt-key">${I18n.t('graph.tooltip.connections',{r:currentR.toFixed(2)})}</span>
              <span class="tt-val">${I18n.t('graph.neighbors',{count:neighborCount})}</span>
            </div>`;
          document.getElementById('tooltip').style.display = 'block';
        } else {
          document.getElementById('tooltip').style.display = 'none';
        }
        requestAnimationFrame(() => { if (Graph) Graph.refresh(); });
      })
      .onNodeClick(node => {
        // Focus node on click without zoom
        selectedNode = node;
        hoverNode = node;
        Graph.refresh();
      })
      .onBackgroundClick(() => {
        selectedNode = null;
        hoverNode = null;
        if (focusSector) {
          focusSector = null;
          document.querySelectorAll('.legend-item').forEach(el => el.classList.remove('active', 'dimmed'));
          Graph.refresh();
        } else {
          Graph.zoomToFit(400, 40);
        }
      });

    progFill.style.width = '100%';
    setTimeout(() => { progFill.style.width = '0%'; }, 600);

    // 기본 임계값으로 데이터 적용
    applyFilter(DEFAULT_R);
  })
  .catch(err => {
    console.error(err);
    document.getElementById('error-screen').classList.add('show');
  });

// ── 툴팁 마우스 추적 ─────────────────────────────────
document.getElementById('graph-container').addEventListener('mousemove', e => {
  const tt = document.getElementById('tooltip');
  if (tt.style.display === 'none') return;
  const x = e.clientX + 14;
  const y = e.clientY + 14;
  tt.style.left = (x + tt.offsetWidth  > window.innerWidth  ? x - tt.offsetWidth  - 28 : x) + 'px';
  tt.style.top  = (y + tt.offsetHeight > window.innerHeight ? y - tt.offsetHeight - 28 : y) + 'px';
});

// ── 슬라이더 ─────────────────────────────────────────
document.getElementById('r-slider').addEventListener('input', e => {
  const v = parseInt(e.target.value) / 100;
  document.getElementById('r-val').textContent = v.toFixed(2);
  applyFilter(v);
});

document.getElementById('node-size-slider').addEventListener('input', e => {
  nodeScaleMult = parseInt(e.target.value) / 100;
  document.getElementById('node-size-val').textContent = nodeScaleMult.toFixed(1) + 'x';
  if (Graph) { Graph.nodeVal(getNodeVal); Graph.refresh(); }
});

// ── 슬라이더 +/- 버튼 ───────────────────────────────
function nudgeSlider(sliderId, labelId, delta, scale, fmt) {
  const slider = document.getElementById(sliderId);
  const newVal = Math.min(parseInt(slider.max), Math.max(parseInt(slider.min), parseInt(slider.value) + delta));
  slider.value = newVal;
  slider.dispatchEvent(new Event('input'));
}
document.getElementById('r-minus').addEventListener('click', () => nudgeSlider('r-slider', 'r-val', -5, 100, v => v.toFixed(2)));
document.getElementById('r-plus' ).addEventListener('click', () => nudgeSlider('r-slider', 'r-val', +5, 100, v => v.toFixed(2)));
document.getElementById('ns-minus').addEventListener('click', () => nudgeSlider('node-size-slider', 'node-size-val', -100, 100, v => v.toFixed(1)+'x'));
document.getElementById('ns-plus' ).addEventListener('click', () => nudgeSlider('node-size-slider', 'node-size-val', +100, 100, v => v.toFixed(1)+'x'));

// ── 레거시 토글 ──────────────────────────────────────
document.getElementById('hide-legacy').addEventListener('change', e => {
  hideLegacy = e.target.checked;
  // Reset coordinates to prevent gradual scattering when toggling
  if (Graph) applyFilter(currentR);
});

// ── 짧은 연혁 토글 ───────────────────────────────────
document.getElementById('hide-short-history').addEventListener('change', e => {
  hideShortHistory = e.target.checked;
  if (Graph) applyFilter(currentR);
});

// ── 슈퍼섹터 토글 ────────────────────────────────────
document.getElementById('super-sector-toggle').addEventListener('change', e => {
  superSectorMode = e.target.checked;
  focusSector = null;  // 포커스 초기화
  if (Graph) {
    renderLegend();  // 레전드 재렌더 (슈퍼섹터/서브섹터 항목 전환)
    Graph.refresh();
  }
});

// ── 검색 ─────────────────────────────────────────────
document.getElementById('search').addEventListener('input', e => {
  searchTicker = e.target.value.trim().toUpperCase();
  if (!Graph) return;
  if (searchTicker) {
    const gNode = (Graph.graphData().nodes || []).find(n => n.id === searchTicker);
    if (gNode && gNode.x != null) {
      Graph.centerAt(gNode.x, gNode.y, 500);
      Graph.zoom(6, 500);
    }
  }
  Graph.refresh();
});

// ── i18n 초기화 ───────────────────────────────────────
I18n.init().then(() => {
  // 언어 전환 시 레전드·툴팁·통계 즉시 갱신
  document.addEventListener('i18n:ready', () => {
    renderLegend();
    if (Graph) {
      const gd = Graph.graphData();
      updateStats((gd.nodes||[]).length, (gd.links||[]).length, false);
    }
  });
});

// ── 모바일 패널 토글 ──────────────────────────────────
(function(){var toggle=document.getElementById('mob-panel-toggle'),panel=document.getElementById('controls');if(!toggle||!panel)return;toggle.addEventListener('click',function(){panel.classList.toggle('mob-visible');});})();
