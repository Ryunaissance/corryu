"""render_html.py — HTML 대시보드 렌더러

output/etf_data.json 을 읽어 output/master_dashboard.html 을 생성합니다.
pandas 불필요 · 단독 실행 가능 · Vercel 빌드 커맨드 진입점

Usage:
    python3 render_html.py
"""
import json
import os
import sys
from datetime import datetime

# src/ 모듈 접근
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from config import SECTOR_DEFS, SUPER_SECTOR_DEFS, ASSET_CLASSES, MY_PORTFOLIO, OUTPUT_DIR


def generate_html(sector_meta):
    """HTML 대시보드 생성 (데이터는 etf_data.json 에서 fetch, pandas 불필요)"""
    today = datetime.now().strftime('%Y-%m-%d')
    total_etfs    = sum(m['count']  for m in sector_meta.values())
    total_active  = sum(m['active'] for m in sector_meta.values())
    total_legacy  = sum(m['legacy'] for m in sector_meta.values())
    total_sectors = len([s for s in sector_meta.values() if s['count'] > 0])

    # 자산군별 섹터 그룹핑
    ac_sectors = {}
    for sid, sdef in SECTOR_DEFS.items():
        ac = sdef['asset_class']
        ac_sectors.setdefault(ac, []).append(sid)

    json_ac_sectors  = json.dumps(ac_sectors, ensure_ascii=False)
    json_ac_defs     = json.dumps({k: v for k, v in ASSET_CLASSES.items()}, ensure_ascii=False)
    json_sector_defs = json.dumps(
        {k: {'name': v['name'], 'name_en': v['name_en'],
             'icon': v['icon'], 'anchor': v['anchor'] or '—',
             'asset_class': v['asset_class'],
             'super_sector': v.get('super_sector')}
         for k, v in SECTOR_DEFS.items()}, ensure_ascii=False)
    json_super_sector_defs = json.dumps(
        {k: {'name': v['name'], 'name_en': v['name_en'],
             'anchor': v['anchor'], 'icon': v['icon'],
             'color': v['color'], 'sub_sectors': v['sub_sectors']}
         for k, v in SUPER_SECTOR_DEFS.items()}, ensure_ascii=False)
    json_my_portfolio = json.dumps(MY_PORTFOLIO)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CORRYU Master Valuation Dashboard</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
<link href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {{ --bg-primary: #0a0d14; --bg-card: rgba(20,24,38,0.85); --bg-hover: rgba(59,130,246,0.08); --border: rgba(255,255,255,0.07); --text-primary: #e2e8f0; --text-muted: #64748b; --accent: #3b82f6; --accent-glow: rgba(59,130,246,0.3); }}
* {{ box-sizing: border-box; }}
body {{ background-color: var(--bg-primary); color: var(--text-primary); font-family: 'Inter', -apple-system, sans-serif; margin: 0; padding: 16px; }}
.glass {{ background: var(--bg-card); backdrop-filter: blur(16px); border: 1px solid var(--border); border-radius: 14px; }}
.text-gradient {{ background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; }}

/* Asset Class Tabs */
.ac-tab {{ padding: 8px 18px; border-radius: 10px; background: transparent; color: var(--text-muted); border: 1px solid transparent; font-weight: 600; font-size: 0.9rem; cursor: pointer; transition: all 0.2s; white-space: nowrap; }}
.ac-tab:hover {{ color: var(--text-primary); background: var(--bg-hover); }}
.ac-tab.active {{ background: var(--accent); color: #fff; border-color: var(--accent); box-shadow: 0 0 20px var(--accent-glow); }}

/* Sector Tabs */
.sec-tab {{ padding: 6px 14px; border-radius: 8px; background: rgba(255,255,255,0.03); color: var(--text-muted); border: 1px solid rgba(255,255,255,0.06); font-weight: 500; font-size: 0.82rem; cursor: pointer; transition: all 0.15s; white-space: nowrap; margin: 3px; }}
.sec-tab:hover {{ color: var(--text-primary); border-color: rgba(255,255,255,0.15); }}
.sec-tab.active {{ background: rgba(59,130,246,0.15); color: #93c5fd; border-color: rgba(59,130,246,0.4); }}
.sec-tab .sec-count {{ font-size: 0.7rem; opacity: 0.6; margin-left: 4px; }}
/* Super-sector tab */
.super-sec-tab {{ background: rgba(59,130,246,0.07); border-color: rgba(59,130,246,0.2); color: #93c5fd; }}
.super-sec-tab:hover {{ background: rgba(59,130,246,0.15); border-color: rgba(59,130,246,0.4); }}
.super-sec-tab.active {{ background: rgba(59,130,246,0.22); color: #fff; border-color: rgba(59,130,246,0.6); box-shadow: 0 0 12px rgba(59,130,246,0.2); }}
/* Sub-sector tabs row */
#subSecTabs {{ display:none; padding: 6px 0 2px 0; border-top: 1px solid rgba(59,130,246,0.15); margin-top: 4px; }}
.sub-sec-tab {{ font-size: 0.77rem; padding: 4px 11px; }}
.expand-arrow {{ font-size: 0.65rem; margin-left: 4px; opacity: 0.7; }}

/* Summary Cards */
.stat-card {{ display: flex; flex-direction: column; align-items: center; padding: 12px 8px; background: rgba(10,13,20,0.5); border-radius: 10px; border: 1px solid var(--border); min-width: 90px; }}
.stat-card .stat-value {{ font-size: 1.3rem; font-weight: 700; }}
.stat-card .stat-label {{ font-size: 0.7rem; color: var(--text-muted); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}

/* DataTables Override */
table.dataTable {{ border-collapse: collapse; width: 100%; color: #cbd5e1; font-size: 0.88rem; }}
table.dataTable thead th {{ background: rgba(20,24,38,0.95); color: #64748b; border-bottom: 2px solid rgba(255,255,255,0.08); padding: 10px 8px; font-weight: 600; font-size: 0.78rem; text-align: right; text-transform: uppercase; letter-spacing: 0.3px; }}
table.dataTable tbody td {{ border-bottom: 1px solid rgba(255,255,255,0.04); padding: 10px 8px; text-align: right; }}
table.dataTable tbody tr:hover {{ background-color: var(--bg-hover) !important; }}
table.dataTable thead th.text-left, table.dataTable tbody td.text-left {{ text-align: left !important; }}
.dataTables_wrapper .dataTables_filter input {{ color: white; background: rgba(20,24,38,0.95); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 6px 14px; font-size: 0.85rem; }}
.dataTables_wrapper .dataTables_filter input:focus {{ outline: none; border-color: var(--accent); box-shadow: 0 0 8px var(--accent-glow); }}
.dataTables_wrapper .dataTables_length select {{ color: white; background: rgba(20,24,38,0.95); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 4px; }}
.dataTables_wrapper .dataTables_info, .dataTables_wrapper .dataTables_paginate {{ color: var(--text-muted); font-size: 0.8rem; padding-top: 12px; }}
.dataTables_wrapper .dataTables_paginate .paginate_button {{ color: var(--text-muted) !important; border: 1px solid rgba(255,255,255,0.06) !important; border-radius: 6px !important; background: transparent !important; margin: 0 2px; }}
.dataTables_wrapper .dataTables_paginate .paginate_button.current {{ background: var(--accent) !important; color: #fff !important; border-color: var(--accent) !important; }}

/* Legacy badge */
.badge-legacy {{ display: inline-flex; align-items: center; gap: 3px; padding: 2px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; background: rgba(239,68,68,0.12); color: #f87171; border: 1px solid rgba(239,68,68,0.2); }}
.badge-active {{ display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; background: rgba(34,197,94,0.1); color: #4ade80; border: 1px solid rgba(34,197,94,0.15); }}
.badge-short {{ display: inline-flex; align-items: center; padding: 2px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: 600; background: rgba(234,179,8,0.12); color: #facc15; border: 1px solid rgba(234,179,8,0.2); margin-left: 4px; }}
.tag {{ display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: 600; margin: 1px; }}
.value-up {{ color: #f87171; }} .value-down {{ color: #60a5fa; }}
.row-legacy td {{ opacity: 0.45; text-decoration: line-through; }}
.mine-badge {{ background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #000; padding: 2px 8px; border-radius: 4px; font-size: 0.68rem; font-weight: 800; box-shadow: 0 0 10px rgba(251,191,36,0.4); }}

/* Filter controls */
.filter-input {{ background: rgba(20,24,38,0.95); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #e2e8f0; padding: 6px 10px; font-size: 0.82rem; width: 90px; }}
.filter-input:focus {{ outline: none; border-color: var(--accent); }}
.filter-check {{ accent-color: var(--accent); width: 16px; height: 16px; cursor: pointer; }}

/* Tooltip */
.tooltip-container {{ position: relative; cursor: help; }}
.tooltip-content {{ display: none; position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); background: #1e293b; color: #e2e8f0; padding: 8px 12px; border-radius: 8px; font-size: 0.75rem; white-space: nowrap; z-index: 999; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 12px rgba(0,0,0,0.5); max-width: 350px; white-space: normal; }}
.tooltip-container:hover .tooltip-content {{ display: block; }}
</style>
</head>
<body>
<div class="max-w-screen-2xl mx-auto">
    <!-- Header -->
    <div class="glass p-5 mb-5 text-center relative overflow-hidden">
        <div class="absolute top-0 left-0 w-full h-0.5" style="background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899, #f59e0b);"></div>
        <div class="absolute top-4 right-4">
            <a href="graph.html" style="display:inline-flex;align-items:center;gap:6px;padding:7px 16px;border-radius:10px;background:rgba(139,92,246,0.15);color:#a78bfa;border:1px solid rgba(139,92,246,0.35);font-size:0.82rem;font-weight:600;text-decoration:none;transition:all 0.2s;" onmouseover="this.style.background='rgba(139,92,246,0.28)'" onmouseout="this.style.background='rgba(139,92,246,0.15)'">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="5" cy="12" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><line x1="7" y1="11.5" x2="17" y2="6.5"/><line x1="7" y1="12.5" x2="17" y2="17.5"/></svg>
                그래프 보기
            </a>
        </div>
        <h1 class="text-2xl md:text-3xl font-extrabold mb-2 tracking-tight">
            <span class="text-gradient">CORRYU</span> Master Valuation Dashboard
        </h1>
        <p class="text-sm text-gray-500">
            Total <span class="text-white font-bold">{total_etfs:,}</span> ETFs
            <span class="text-gray-600">(레거시 <span class="text-yellow-400 font-bold">{total_legacy:,}</span>개 제외 시 <span class="text-green-400 font-bold">{total_active:,}</span> active)</span> |
            <span class="text-white font-bold">{total_sectors}</span> Sectors |
            Updated: <span class="text-gray-400">{today}</span>
        </p>
    </div>

    <!-- Asset Class Tabs (Level 1) -->
    <div class="glass p-4 mb-4">
        <div class="flex items-center gap-2 overflow-x-auto pb-1" id="acTabs">
            <button class="ac-tab active" data-ac="ALL">전체</button>
        </div>
    </div>

    <!-- Sector Tabs (Level 2) + Sub-sector Tabs (Level 3) -->
    <div class="glass p-4 mb-4">
        <div class="flex flex-wrap" id="secTabs"></div>
        <div class="flex flex-wrap" id="subSecTabs"></div>
    </div>

    <!-- Sector Summary + Filters -->
    <div class="glass p-4 mb-4">
        <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <!-- Summary Cards -->
            <div class="flex items-center gap-3 overflow-x-auto" id="summaryCards">
            </div>
            <!-- Filters -->
            <div class="flex flex-wrap items-center gap-3 text-sm">
                <label class="flex items-center gap-1.5 text-gray-400 cursor-pointer">
                    <input type="checkbox" id="filterLegacy" class="filter-check">
                    <span>Legacy 숨기기</span>
                </label>
                <label class="flex items-center gap-1.5 text-gray-400 cursor-pointer">
                    <input type="checkbox" id="filterShort" class="filter-check">
                    <span>짧은연혁 숨기기</span>
                </label>
                <div class="flex items-center gap-1.5 text-gray-400">
                    <span>Min AUM</span>
                    <input type="number" id="filterAum" class="filter-input" placeholder="$M" value="0">
                    <span>M$</span>
                </div>
                <div class="flex items-center gap-1.5 text-gray-400">
                    <span>Min Sortino</span>
                    <input type="number" id="filterSortino" class="filter-input" placeholder="0" value="" step="0.1">
                </div>
            </div>
        </div>
    </div>

    <!-- Data Table -->
    <div class="glass p-4">
        <table id="masterTable" class="display nowrap" style="width:100%">
            <thead>
                <tr>
                    <th title="연번" style="width:36px;min-width:36px">#</th>
                    <th class="text-left">Ticker</th>
                    <th class="text-left" style="min-width:220px">ETF 명칭</th>
                    <th title="시가총액 순위">Rank</th>
                    <th title="시가총액 ($M)">AUM</th>
                    <th title="섹터 앵커 대비 상관계수">r_Anchor</th>
                    <th title="Z-Score (200일 이평 기준)">Z-Score</th>
                    <th title="200일 이동평균 이격도">200MA</th>
                    <th title="52주 최고가 대비 하락폭">52W MDD</th>
                    <th title="연평균 복리 수익률">CAGR</th>
                    <th title="연환산 변동성">Vol</th>
                    <th title="소르티노 비율">Sortino</th>
                    <th title="최초 상장일">Inception</th>
                    <th title="레거시 상태" style="min-width:80px">Status</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>
    </div>
</div>

<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script>
// sectorMeta, allData는 etf_data.json에서 fetch로 로드됩니다
let sectorMeta = {{}};
let allData = {{}};
const acSectors = {json_ac_sectors};
const acDefs = {json_ac_defs};
const sectorDefs = {json_sector_defs};
const superSectorDefs = {json_super_sector_defs};
const myPortfolio = {json_my_portfolio};

// 섹터ID → 슈퍼섹터ID 역방향 맵
const sectorToSuperSector = {{}};
for (const [ssId, ss] of Object.entries(superSectorDefs)) {{
    for (const sid of ss.sub_sectors) sectorToSuperSector[sid] = ssId;
}}

let state = {{
    activeAC: 'ALL',
    activeSector: 'ALL',       // 'ALL' | 섹터ID | 'SS_<ssId>' (슈퍼섹터 전체)
    expandedSuperSector: null, // null | 슈퍼섹터ID (서브탭 표시 여부)
    hideLegacy: false,
    hideShort: false,
    minAum: 0,
    minSortino: -999
}};

let table;


function formatMCap(val) {{
    if (!val) return '-';
    let m = val / 1e6;
    if (m >= 1000) return '$' + (m/1000).toFixed(1) + 'B';
    return '$' + Math.round(m) + 'M';
}}

function renderACTabs() {{
    let html = '<button class="ac-tab' + (state.activeAC === 'ALL' ? ' active' : '') + '" data-ac="ALL">전체</button>';
    let ordered = Object.entries(acDefs).sort((a,b) => a[1].order - b[1].order);
    for (let [ac, def] of ordered) {{
        let isActive = state.activeAC === ac ? ' active' : '';
        html += '<button class="ac-tab' + isActive + '" data-ac="' + ac + '">' + def.icon + ' ' + def.name + '</button>';
    }}
    $('#acTabs').html(html);
}}

function getSuperSectorMeta(ssId) {{
    let ss = superSectorDefs[ssId];
    if (!ss) return {{}};
    let metas = ss.sub_sectors.map(sid => sectorMeta[sid] || {{}});
    return {{
        count:  metas.reduce((s,m) => s+(m.count||0), 0),
        active: metas.reduce((s,m) => s+(m.active||0), 0),
        legacy: metas.reduce((s,m) => s+(m.legacy||0), 0),
    }};
}}

function renderSectorTabs() {{
    let sectors = [];
    if (state.activeAC === 'ALL') {{
        sectors = Object.keys(sectorDefs).sort();
    }} else {{
        sectors = (acSectors[state.activeAC] || []).sort();
    }}
    let allActive = state.activeSector === 'ALL' ? ' active' : '';
    let totalCount  = sectors.reduce((s, sid) => s + ((sectorMeta[sid]||{{}}).count||0), 0);
    let totalActiveN = sectors.reduce((s, sid) => s + ((sectorMeta[sid]||{{}}).active||0), 0);
    let html = '<button class="sec-tab' + allActive + '" data-sector="ALL">전체<span class="sec-count">' + totalActiveN + '/' + totalCount + '</span></button>';

    let renderedSS = new Set();
    for (let sid of sectors) {{
        let sd = sectorDefs[sid];
        let meta = sectorMeta[sid];
        if (!meta || meta.count === 0) continue;

        let ssId = sd.super_sector;
        if (ssId) {{
            if (renderedSS.has(ssId)) continue;  // 이미 슈퍼섹터 탭 추가됨
            renderedSS.add(ssId);
            let ss = superSectorDefs[ssId];
            let ssMeta = getSuperSectorMeta(ssId);
            let ssIsActive = state.expandedSuperSector === ssId;
            let isActiveSS = (state.activeSector === 'SS_' + ssId) ? ' active' : '';
            let arrow = ssIsActive ? ' ▾' : ' ▸';
            html += '<button class="sec-tab super-sec-tab' + isActiveSS + '" data-supersec="' + ssId + '">';
            html += ss.icon + ' ' + ss.name;
            html += '<span class="sec-count">' + ssMeta.active + '/' + ssMeta.count + '</span>';
            html += '<span class="expand-arrow">' + arrow + '</span></button>';
        }} else {{
            let isActive = state.activeSector === sid ? ' active' : '';
            html += '<button class="sec-tab' + isActive + '" data-sector="' + sid + '">';
            html += sd.icon + ' ' + sd.name;
            html += '<span class="sec-count">' + (meta.active||0) + '/' + meta.count + '</span></button>';
        }}
    }}
    $('#secTabs').html(html);
    renderSubSecTabs();
}}

function renderSubSecTabs() {{
    let ssId = state.expandedSuperSector;
    if (!ssId) {{ $('#subSecTabs').hide(); return; }}
    let ss = superSectorDefs[ssId];
    let html = '';
    for (let sid of ss.sub_sectors) {{
        let sd = sectorDefs[sid];
        let meta = sectorMeta[sid];
        if (!meta || meta.count === 0) continue;
        let isActive = state.activeSector === sid ? ' active' : '';
        html += '<button class="sec-tab sub-sec-tab' + isActive + '" data-sector="' + sid + '">';
        html += sd.icon + ' ' + sd.name;
        html += '<span class="sec-count">' + (meta.active||0) + '/' + meta.count + '</span></button>';
    }}
    $('#subSecTabs').html(html).show();
}}

function renderSummary() {{
    let html = '';
    let sec = state.activeSector;
    if (sec === 'ALL') {{
        let metas = Object.values(sectorMeta);
        let totalCount  = metas.reduce((s,m) => s+(m.count||0), 0);
        let totalActive = metas.reduce((s,m) => s+(m.active||0), 0);
        let totalLegacy = metas.reduce((s,m) => s+(m.legacy||0), 0);
        html += '<div class="stat-card"><div class="stat-value text-white">' + totalCount + '</div><div class="stat-label">ETFs</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-green-400">' + totalActive + '</div><div class="stat-label">Active</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-red-400">' + totalLegacy + '</div><div class="stat-label">Legacy</div></div>';
    }} else if (sec && sec.startsWith('SS_')) {{
        let ssId = sec.slice(3);
        let ssMeta = getSuperSectorMeta(ssId);
        let ss = superSectorDefs[ssId] || {{}};
        html += '<div class="stat-card"><div class="stat-value text-white">' + ssMeta.count + '</div><div class="stat-label">ETFs</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-green-400">' + ssMeta.active + '</div><div class="stat-label">Active</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-red-400">' + ssMeta.legacy + '</div><div class="stat-label">Legacy</div></div>';
        html += '<div class="stat-card" style="min-width:120px"><div class="stat-value text-yellow-300 text-sm">' + (ss.anchor||'—') + '</div><div class="stat-label">Anchor</div></div>';
    }} else {{
        let meta = sectorMeta[sec] || {{}};
        let sd = sectorDefs[sec] || {{}};
        html += '<div class="stat-card"><div class="stat-value text-white">' + (meta.count||0) + '</div><div class="stat-label">ETFs</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-green-400">' + (meta.active||0) + '</div><div class="stat-label">Active</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-red-400">' + (meta.legacy||0) + '</div><div class="stat-label">Legacy</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-blue-300">' + (meta.avg_cagr > 0 ? '+' : '') + (meta.avg_cagr||0).toFixed(1) + '%</div><div class="stat-label">Avg CAGR</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-gray-300">' + (meta.avg_vol||0).toFixed(1) + '%</div><div class="stat-label">Avg Vol</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-purple-400">' + (meta.avg_sortino||0).toFixed(2) + '</div><div class="stat-label">Avg Sortino</div></div>';
        html += '<div class="stat-card" style="min-width:120px"><div class="stat-value text-yellow-300 text-sm">' + (sd.anchor||'—') + '</div><div class="stat-label">Anchor</div></div>';
    }}
    $('#summaryCards').html(html);
}}

function loadSector(sectorId) {{
    state.activeSector = sectorId;
    // 슈퍼섹터 소속 섹터를 직접 클릭하면 해당 슈퍼섹터를 자동 확장
    if (sectorId && !sectorId.startsWith('SS_') && sectorId !== 'ALL') {{
        let sd = sectorDefs[sectorId];
        if (sd && sd.super_sector) {{
            state.expandedSuperSector = sd.super_sector;
        }} else {{
            state.expandedSuperSector = null;
        }}
    }}
    renderSectorTabs();
    renderSummary();
    let data;
    if (sectorId === 'ALL') {{
        data = Object.values(allData).flat();
    }} else if (sectorId && sectorId.startsWith('SS_')) {{
        let ssId = sectorId.slice(3);
        let ss = superSectorDefs[ssId];
        data = ss ? ss.sub_sectors.flatMap(sid => allData[sid] || []) : [];
    }} else {{
        data = allData[sectorId] || [];
    }}
    table.clear().rows.add(data).draw();
}}

function loadSuperSector(ssId) {{
    state.activeSector = 'SS_' + ssId;
    state.expandedSuperSector = ssId;
    renderSectorTabs();
    renderSummary();
    let ss = superSectorDefs[ssId];
    let data = ss ? ss.sub_sectors.flatMap(sid => allData[sid] || []) : [];
    table.clear().rows.add(data).draw();
}}

function initDashboard() {{
    renderACTabs();
    renderSectorTabs();
    renderSummary();

    table = $('#masterTable').DataTable({{
        data: Object.values(allData).flat(),
        pageLength: 50,
        deferRender: true,
        lengthMenu: [[25, 50, 100, 200, -1], [25, 50, 100, 200, "All"]],
        order: [],
        columns: [
            {{
                data: null, orderable: false, searchable: false,
                className: 'text-right text-gray-600',
                render: function(d, type, row, meta) {{
                    if (type !== 'display') return meta.row + meta.settings._iDisplayStart;
                    return '<span style="font-size:0.75rem">' + (meta.row + meta.settings._iDisplayStart + 1) + '</span>';
                }}
            }},
            {{
                data: 'ticker', className: 'text-left font-semibold',
                render: function(d, type, row) {{
                    if (type !== 'display') return d;
                    let isMine = myPortfolio.includes(d);
                    let cls = isMine ? 'text-yellow-400 text-base' : 'text-blue-300';
                    let h = '<span class="'+cls+'">'+d+'</span>';
                    if (row.short_history) h += '<span class="badge-short" title="상장 3년 미만">짧은연혁</span>';
                    return h;
                }}
            }},
            {{
                data: 'name', className: 'text-left text-xs text-gray-400',
                render: function(d, type, row) {{
                    if (type !== 'display') return d;
                    let h = '<div class="leading-tight">'+d+'</div>';
                    if (myPortfolio.includes(row.ticker)) {{
                        h += '<div class="mt-1"><span class="mine-badge">MY</span></div>';
                    }}
                    return h;
                }}
            }},
            {{ data: 'rank', render: function(d,t){{ return t==='display'?(d===9999?'-':d):d; }} }},
            {{ data: 'aum', render: function(d,t){{ return t==='display'?formatMCap(d):d; }} }},
            {{ data: 'r_anchor', render: function(d,t) {{
                if(t!=='display') return d;
                let c = d >= 0.70 ? 'text-pink-400 font-bold' : (d <= -0.3 ? 'text-green-400 font-bold' : 'text-gray-400');
                return '<span class="'+c+'">'+d.toFixed(2)+'</span>';
            }} }},
            {{ data: 'z_score', render: function(d,t,row) {{
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : d;
                let c = d <= -1.5 ? 'value-down font-bold' : (d >= 2.0 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="'+c+'">'+d.toFixed(2)+'</span>';
            }} }},
            {{ data: 'ma200_pct', render: function(d,t,row) {{
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : d;
                let c = d <= -10 ? 'value-down font-bold' : (d >= 15 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="'+c+'">'+(d>0?'+':'')+d.toFixed(1)+'%</span>';
            }} }},
            {{ data: 'mdd_52w', render: function(d,t,row) {{
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : d;
                let c = d <= -20 ? 'value-down font-bold' : 'text-gray-500';
                return '<span class="'+c+'">'+d.toFixed(1)+'%</span>';
            }} }},
            {{ data: 'cagr', render: function(d,t,row) {{
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : (d||0);
                return '<span class="text-gray-300 font-semibold">'+(d>0?'+':'')+d.toFixed(1)+'%</span>';
            }} }},
            {{ data: 'vol', render: function(d,t,row) {{
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : (d||0);
                return '<span class="text-gray-500">'+d.toFixed(1)+'%</span>';
            }} }},
            {{ data: 'sortino', render: function(d,t,row) {{
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : (d===null?-999999:d);
                let c = d > 1.2 ? 'text-purple-400 font-bold' : 'text-gray-500';
                return '<span class="'+c+'">'+d.toFixed(2)+'</span>';
            }} }},
            {{ data: 'inception', className: 'text-xs text-gray-600', render: function(d, t) {{
                if(t !== 'display') return d || '';
                if(!d || d==='1900-01-01') return '-';
                return d.substring(2);
            }} }},
            {{ data: 'is_legacy', render: function(d,t,row) {{
                if(t!=='display') return d ? 1 : 0;
                if(!d) return '<span class="badge-active">Active</span>';
                let detail = (row.legacy_detail||[]).join(' / ');
                return '<span class="badge-legacy">Legacy</span>'
                    + (detail ? '<div class="text-xs text-red-400 mt-0.5 opacity-80">'+detail+'</div>' : '');
            }} }}
        ],
        createdRow: function(row, data) {{
            if (data.is_legacy) $(row).addClass('row-legacy');
        }}
    }});

    // Custom filter
    $.fn.dataTable.ext.search.push(function(settings, searchData, dataIndex) {{
        let row = settings.aoData[dataIndex]._aData;
        if (state.hideLegacy && row.is_legacy) return false;
        if (state.hideShort && row.short_history) return false;
        if (state.minAum > 0 && row.aum < state.minAum * 1e6) return false;
        if (state.minSortino > -999 && !row.short_history) {{
            if (row.sortino < state.minSortino) return false;
        }}
        return true;
    }});

    // Event: Asset Class tab click
    $(document).on('click', '.ac-tab', function() {{
        state.activeAC = $(this).data('ac');
        state.expandedSuperSector = null;
        renderACTabs();
        if (state.activeAC === 'ALL') {{
            loadSector('ALL');
        }} else {{
            let sectors = (acSectors[state.activeAC] || []).sort();
            let firstWithData = sectors.find(s => sectorMeta[s] && sectorMeta[s].count > 0);
            if (firstWithData) loadSector(firstWithData);
            else renderSectorTabs();
        }}
    }});

    // Event: Super-sector tab click (슈퍼섹터 탭 → 서브탭 토글)
    $(document).on('click', '.super-sec-tab', function() {{
        let ssId = $(this).data('supersec');
        if (state.expandedSuperSector === ssId) {{
            // 이미 열려 있으면 닫고 전체 보기
            state.expandedSuperSector = null;
            loadSector('ALL');
        }} else {{
            loadSuperSector(ssId);
        }}
    }});

    // Event: Sector tab click (서브섹터 탭 포함)
    $(document).on('click', '.sec-tab:not(.super-sec-tab)', function() {{
        loadSector($(this).data('sector'));
    }});

    // Event: Filters
    $('#filterLegacy').on('change', function() {{ state.hideLegacy = this.checked; table.draw(); }});
    $('#filterShort').on('change', function() {{ state.hideShort = this.checked; table.draw(); }});
    $('#filterAum').on('input', function() {{ state.minAum = parseFloat(this.value) || 0; table.draw(); }});
    $('#filterSortino').on('input', function() {{
        let v = parseFloat(this.value);
        state.minSortino = isNaN(v) ? -999 : v;
        table.draw();
    }});
}}

$(document).ready(function() {{
    fetch('etf_data.json')
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
            sectorMeta = d.sectorMeta;
            allData = d.allData;
            initDashboard();
        }});
}});
</script>
</body>
</html>"""

    return html


def main():
    etf_data_path = os.path.join(OUTPUT_DIR, 'etf_data.json')
    if not os.path.exists(etf_data_path):
        print(f"ERROR: {etf_data_path} 없음. dashboard_builder.py 를 먼저 실행하세요.")
        sys.exit(1)

    with open(etf_data_path, 'r', encoding='utf-8') as f:
        etf_data = json.load(f)

    sector_meta = etf_data['sectorMeta']
    html = generate_html(sector_meta)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    total = sum(m['count']  for m in sector_meta.values())
    active = sum(m['active'] for m in sector_meta.values())
    legacy = sum(m['legacy'] for m in sector_meta.values())
    print(f"HTML 생성 완료: {out_path}")
    print(f"  전체 {total:,}개 | Active {active:,}개 | Legacy {legacy:,}개")


if __name__ == '__main__':
    main()
