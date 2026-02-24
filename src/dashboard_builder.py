"""
CORRYU ETF Dashboard - HTML 대시보드 생성 (단일 진입점)
데이터 로딩 → 분류 → 레거시 → 지표 → HTML 생성
"""
import json
import os
from datetime import datetime

from config import SECTOR_DEFS, ASSET_CLASSES, MY_PORTFOLIO, OUTPUT_DIR
from data_loader import load_all, get_all_tickers, get_fullname, get_market_cap, get_rank
from classify import classify_all, get_sector_members, fill_anchor_correlations
from verify import verify_mece, spot_check
from legacy import assess_all_legacy
from metrics import compute_etf_metrics, compute_sector_stats


def build_sector_meta(sector_members, all_etf_data):
    """섹터별 메타 정보 JSON 생성"""
    meta = {}
    for sid, sdef in SECTOR_DEFS.items():
        etfs = all_etf_data.get(sid, [])
        stats = compute_sector_stats(etfs)
        meta[sid] = {
            'name': sdef['name'],
            'name_en': sdef['name_en'],
            'asset_class': sdef['asset_class'],
            'anchor': sdef['anchor'] or '—',
            'icon': sdef['icon'],
            **stats,
        }
    return meta


def build_all_etf_data(sector_members, classification, legacy_results,
                       df_price, perf_stats, scraped,
                       df_corr_monthly, df_corr_daily):
    """전체 섹터별 ETF 데이터 JSON 생성"""
    all_data = {}

    for sid in sorted(SECTOR_DEFS.keys()):
        tickers = sector_members.get(sid, set())
        etf_list = []

        for ticker in tickers:
            etf_info = compute_etf_metrics(
                ticker, df_price, perf_stats, scraped, classification,
                df_corr_monthly, df_corr_daily, legacy_results
            )
            etf_info['mine'] = 1 if ticker in MY_PORTFOLIO else 0
            etf_list.append(etf_info)

        # 정렬: 내 보유종목 최우선, 그다음 시가총액 순
        etf_list.sort(key=lambda x: (-x['mine'], x['rk']))
        all_data[sid] = etf_list

    return all_data


def generate_html(sector_meta, all_etf_data):
    """HTML 대시보드 생성"""
    today = datetime.now().strftime('%Y-%m-%d')
    total_etfs = sum(m['count'] for m in sector_meta.values())
    total_sectors = len([s for s in sector_meta.values() if s['count'] > 0])

    # 자산군별 섹터 그룹핑
    ac_sectors = {}
    for sid, sdef in SECTOR_DEFS.items():
        ac = sdef['asset_class']
        if ac not in ac_sectors:
            ac_sectors[ac] = []
        ac_sectors[ac].append(sid)

    json_meta = json.dumps(sector_meta, ensure_ascii=False)
    json_data = json.dumps(all_etf_data, ensure_ascii=False)
    json_ac_sectors = json.dumps(ac_sectors, ensure_ascii=False)
    json_ac_defs = json.dumps({k: v for k, v in ASSET_CLASSES.items()}, ensure_ascii=False)
    json_sector_defs = json.dumps({k: {'name': v['name'], 'name_en': v['name_en'],
                                       'icon': v['icon'], 'anchor': v['anchor'] or '—',
                                       'asset_class': v['asset_class']}
                                  for k, v in SECTOR_DEFS.items()}, ensure_ascii=False)
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
        <h1 class="text-2xl md:text-3xl font-extrabold mb-2 tracking-tight">
            <span class="text-gradient">CORRYU</span> Master Valuation Dashboard
        </h1>
        <p class="text-sm text-gray-500">
            Total <span class="text-white font-bold">{total_etfs:,}</span> ETFs |
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

    <!-- Sector Tabs (Level 2) -->
    <div class="glass p-4 mb-4">
        <div class="flex flex-wrap" id="secTabs"></div>
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
const sectorMeta = {json_meta};
const allData = {json_data};
const acSectors = {json_ac_sectors};
const acDefs = {json_ac_defs};
const sectorDefs = {json_sector_defs};
const myPortfolio = {json_my_portfolio};

let state = {{
    activeAC: 'ALL',
    activeSector: 'S01',
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

function renderSectorTabs() {{
    let sectors = [];
    if (state.activeAC === 'ALL') {{
        sectors = Object.keys(sectorDefs).sort();
    }} else {{
        sectors = (acSectors[state.activeAC] || []).sort();
    }}
    let html = '';
    for (let sid of sectors) {{
        let sd = sectorDefs[sid];
        let meta = sectorMeta[sid];
        if (!meta || meta.count === 0) continue;
        let isActive = state.activeSector === sid ? ' active' : '';
        html += '<button class="sec-tab' + isActive + '" data-sector="' + sid + '">';
        html += sd.icon + ' ' + sd.name;
        html += '<span class="sec-count">' + meta.count + '</span></button>';
    }}
    $('#secTabs').html(html);
}}

function renderSummary() {{
    let meta = sectorMeta[state.activeSector] || {{}};
    let sd = sectorDefs[state.activeSector] || {{}};
    let html = '';
    html += '<div class="stat-card"><div class="stat-value text-white">' + (meta.count||0) + '</div><div class="stat-label">ETFs</div></div>';
    html += '<div class="stat-card"><div class="stat-value text-green-400">' + (meta.active||0) + '</div><div class="stat-label">Active</div></div>';
    html += '<div class="stat-card"><div class="stat-value text-red-400">' + (meta.legacy||0) + '</div><div class="stat-label">Legacy</div></div>';
    html += '<div class="stat-card"><div class="stat-value text-blue-300">' + (meta.avg_cagr > 0 ? '+' : '') + (meta.avg_cagr||0).toFixed(1) + '%</div><div class="stat-label">Avg CAGR</div></div>';
    html += '<div class="stat-card"><div class="stat-value text-gray-300">' + (meta.avg_vol||0).toFixed(1) + '%</div><div class="stat-label">Avg Vol</div></div>';
    html += '<div class="stat-card"><div class="stat-value text-purple-400">' + (meta.avg_sortino||0).toFixed(2) + '</div><div class="stat-label">Avg Sortino</div></div>';
    html += '<div class="stat-card" style="min-width:120px"><div class="stat-value text-yellow-300 text-sm">' + (sd.anchor||'—') + '</div><div class="stat-label">Anchor</div></div>';
    $('#summaryCards').html(html);
}}

function loadSector(sectorId) {{
    state.activeSector = sectorId;
    renderSectorTabs();
    renderSummary();
    let data = allData[sectorId] || [];
    table.clear().rows.add(data).draw();
}}

$(document).ready(function() {{
    renderACTabs();
    renderSectorTabs();
    renderSummary();

    table = $('#masterTable').DataTable({{
        data: allData[state.activeSector] || [],
        pageLength: 50,
        deferRender: true,
        lengthMenu: [[25, 50, 100, 200, -1], [25, 50, 100, 200, "All"]],
        order: [],
        columns: [
            {{
                data: 't', className: 'text-left font-semibold',
                render: function(d, type, row) {{
                    if (type !== 'display') return d;
                    let isMine = myPortfolio.includes(d);
                    let cls = isMine ? 'text-yellow-400 text-base' : 'text-blue-300';
                    let h = '<span class="'+cls+'">'+d+'</span>';
                    if (row.sh) h += '<span class="badge-short" title="상장 3년 미만">짧은연혁</span>';
                    return h;
                }}
            }},
            {{
                data: 'n', className: 'text-left text-xs text-gray-400',
                render: function(d, type, row) {{
                    if (type !== 'display') return d;
                    let h = '<div class="leading-tight">'+d+'</div>';
                    if (myPortfolio.includes(row.t)) {{
                        h += '<div class="mt-1"><span class="mine-badge">MY</span></div>';
                    }}
                    return h;
                }}
            }},
            {{ data: 'rk', render: function(d,t){{ return t==='display'?(d===9999?'-':d):d; }} }},
            {{ data: 'mc', render: function(d,t){{ return t==='display'?formatMCap(d):d; }} }},
            {{ data: 'r', render: function(d,t) {{
                if(t!=='display') return d;
                let c = d >= 0.70 ? 'text-pink-400 font-bold' : (d <= -0.3 ? 'text-green-400 font-bold' : 'text-gray-400');
                return '<span class="'+c+'">'+d.toFixed(2)+'</span>';
            }} }},
            {{ data: 'z', render: function(d,t,row) {{
                if(row.sh && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.sh ? -999999 : d;
                let c = d <= -1.5 ? 'value-down font-bold' : (d >= 2.0 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="'+c+'">'+d.toFixed(2)+'</span>';
            }} }},
            {{ data: 'ma', render: function(d,t,row) {{
                if(row.sh && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.sh ? -999999 : d;
                let c = d <= -10 ? 'value-down font-bold' : (d >= 15 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="'+c+'">'+(d>0?'+':'')+d.toFixed(1)+'%</span>';
            }} }},
            {{ data: 'h52', render: function(d,t,row) {{
                if(row.sh && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.sh ? -999999 : d;
                let c = d <= -20 ? 'value-down font-bold' : 'text-gray-500';
                return '<span class="'+c+'">'+d.toFixed(1)+'%</span>';
            }} }},
            {{ data: 'cagr', render: function(d,t,row) {{
                if(row.sh && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.sh ? -999999 : (d||0);
                return '<span class="text-gray-300 font-semibold">'+(d>0?'+':'')+d.toFixed(1)+'%</span>';
            }} }},
            {{ data: 'v', render: function(d,t,row) {{
                if(row.sh && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.sh ? -999999 : (d||0);
                return '<span class="text-gray-500">'+d.toFixed(1)+'%</span>';
            }} }},
            {{ data: 's', render: function(d,t,row) {{
                if(row.sh && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.sh ? -999999 : (d===null?-999999:d);
                let c = d > 1.2 ? 'text-purple-400 font-bold' : 'text-gray-500';
                return '<span class="'+c+'">'+d.toFixed(2)+'</span>';
            }} }},
            {{ data: 'inc', className: 'text-xs text-gray-600', render: function(d) {{
                if(!d || d==='1900-01-01') return '-';
                return d.substring(2);
            }} }},
            {{ data: 'isl', render: function(d,t,row) {{
                if(t!=='display') return d ? 1 : 0;
                if(!d) return '<span class="badge-active">Active</span>';
                let detail = (row.ld||[]).join(' / ');
                return '<span class="badge-legacy">Legacy</span>'
                    + (detail ? '<div class="text-xs text-red-400 mt-0.5 opacity-80">'+detail+'</div>' : '');
            }} }}
        ],
        createdRow: function(row, data) {{
            if (data.isl) $(row).addClass('row-legacy');
        }}
    }});

    // Custom filter
    $.fn.dataTable.ext.search.push(function(settings, searchData, dataIndex) {{
        let row = settings.aoData[dataIndex]._aData;
        if (state.hideLegacy && row.isl) return false;
        if (state.hideShort && row.sh) return false;
        if (state.minAum > 0 && row.mc < state.minAum * 1e6) return false;
        if (state.minSortino > -999 && !row.sh) {{
            if (row.s < state.minSortino) return false;
        }}
        return true;
    }});

    // Event: Asset Class tab click
    $(document).on('click', '.ac-tab', function() {{
        state.activeAC = $(this).data('ac');
        renderACTabs();
        // 해당 자산군의 첫 번째 섹터로 자동 전환
        let sectors = state.activeAC === 'ALL'
            ? Object.keys(sectorDefs).sort()
            : (acSectors[state.activeAC] || []).sort();
        let firstWithData = sectors.find(s => sectorMeta[s] && sectorMeta[s].count > 0);
        if (firstWithData) loadSector(firstWithData);
        else renderSectorTabs();
    }});

    // Event: Sector tab click
    $(document).on('click', '.sec-tab', function() {{
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
}});
</script>
</body>
</html>"""

    return html


def main():
    """메인 실행: 데이터 로딩 → 분류 → 레거시 → 지표 → HTML"""
    # 1. 데이터 로딩
    df_price, perf_stats, scraped, df_corr_monthly, df_corr_daily = load_all()
    all_tickers = get_all_tickers(df_corr_daily)
    print(f"\n전체 ETF 유니버스: {len(all_tickers)}개")

    # 2. MECE 분류
    print("\n=== 섹터 분류 실행 ===")
    classification = classify_all(all_tickers, scraped, df_corr_monthly, df_corr_daily)
    sector_members = get_sector_members(classification)
    fill_anchor_correlations(classification, sector_members, df_corr_monthly, df_corr_daily)

    # 3. MECE 검증
    print("\n=== MECE 검증 ===")
    verify_mece(classification, all_tickers)
    spot_check(classification, scraped)

    # 4. 레거시 판별
    print("\n=== 레거시 판별 ===")
    legacy_results = assess_all_legacy(
        sector_members, classification,
        df_corr_monthly, df_corr_daily,
        scraped, perf_stats, df_price
    )

    # 5. 전체 ETF 데이터 생성
    print("\n대시보드 데이터 생성 중...")
    all_etf_data = build_all_etf_data(
        sector_members, classification, legacy_results,
        df_price, perf_stats, scraped,
        df_corr_monthly, df_corr_daily
    )

    # 6. 섹터 메타 생성
    sector_meta = build_sector_meta(sector_members, all_etf_data)

    # 7. HTML 생성
    print("HTML 대시보드 생성 중...")
    html = generate_html(sector_meta, all_etf_data)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, 'master_dashboard.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n{'='*50}")
    print(f"대시보드 생성 완료: {out_path}")
    print(f"  전체 ETF: {sum(m['count'] for m in sector_meta.values()):,}개")
    print(f"  Active: {sum(m['active'] for m in sector_meta.values()):,}개")
    print(f"  Legacy: {sum(m['legacy'] for m in sector_meta.values()):,}개")
    print(f"{'='*50}")

    # 8. classification.json 저장
    cls_path = os.path.join(OUTPUT_DIR, 'classification.json')
    cls_export = {}
    for ticker, info in classification.items():
        sid = info['sector']
        sdef = SECTOR_DEFS[sid]
        cls_export[ticker] = {
            'sector_id': sid,
            'sector_name': sdef['name'],
            'asset_class': sdef['asset_class'],
            'method': info['method'],
            'r_anchor': info['r_anchor'],
            'is_legacy': legacy_results.get(ticker, {}).get('is_legacy', False),
            'legacy_reasons': legacy_results.get(ticker, {}).get('reasons', []),
        }
    with open(cls_path, 'w', encoding='utf-8') as f:
        json.dump(cls_export, f, ensure_ascii=False, indent=2)
    print(f"분류 JSON 저장: {cls_path}")


if __name__ == '__main__':
    main()
