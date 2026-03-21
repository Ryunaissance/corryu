// sectorMeta, allData는 etf_data.json에서 fetch로 로드됩니다
let sectorMeta = {};
let allData = {};

function recalcSectorMeta() {
    for (let sid in allData) {
        if (!allData.hasOwnProperty(sid)) continue;
        let list = allData[sid];
        let total = list.length;
        let active = list.filter(e => !e.is_legacy).length;
        let legacy = total - active;
        let sumCAGR = list.reduce((s,e) => s + (e.cagr||0), 0);
        let sumVol = list.reduce((s,e) => s + (e.vol||0), 0);
        let sumSortino = list.reduce((s,e) => s + (e.sortino||0), 0);
        
        sectorMeta[sid] = {
            count: total,
            active: active,
            legacy: legacy,
            avg_cagr: total > 0 ? sumCAGR / total : 0,
            avg_vol: total > 0 ? sumVol / total : 0,
            avg_sortino: total > 0 ? sumSortino / total : 0
        };
    }
    // 전체 요약 (Summary 카드용) 갱신
    let totalETFs = 0, totalActive = 0, totalLegacy = 0;
    for (let sid in sectorMeta) {
        totalETFs += sectorMeta[sid].count;
        totalActive += sectorMeta[sid].active;
        totalLegacy += sectorMeta[sid].legacy;
    }
    $('#hdr-total').text(totalETFs.toLocaleString());
    $('#hdr-active').text(totalActive.toLocaleString());
    $('#hdr-legacy').text(totalLegacy.toLocaleString());
}
const acSectors = window.CORRYU_CONFIG.ac_sectors;

// ── 체크박스 선택 상태 ─────────────────────────────────
const selectedTickers = new Set();

// ── Admin 권한 감지 ──────────────────────────────────
const _adminEmails = new Set(window.CORRYU_CONFIG.admin_emails);
let _isAdmin = false;

async function detectAdmin() {
    if (typeof CorryuAuth === 'undefined' || !CorryuAuth.isConfigured) return false;
    try {
        const user = await CorryuAuth.getUser();
        if (!user) return false;
        if (user.app_metadata && user.app_metadata.role === 'admin') return true;
        if (user.email && _adminEmails.has(user.email)) return true;
        return false;
    } catch(e) { return false; }
}

function stripLegacyForNonAdmin() {
    for (const sid of Object.keys(allData)) {
        for (const etf of allData[sid]) {
            etf.is_legacy = false;
            etf.legacy_reasons = [];
            etf.legacy_detail = [];
        }
    }
}

function applyAdminUI(isAdmin) {
    _isAdmin = isAdmin;
    if (!isAdmin) {
        $('#filterLegacy').closest('label').hide();
        $('#fab-btn-legacy, #fab-btn-unlegacy').hide();
        var $ll = $('#hdr-legacy-label');
        if ($ll.length) $ll.hide();
    }
}

// ── localStorage 레거시 오버라이드 ───────────────────
const USER_OVERRIDES_KEY = 'corryu_user_overrides';

function getUserOverrides() {
    try { return JSON.parse(localStorage.getItem(USER_OVERRIDES_KEY) || '{}'); }
    catch(e) { return {}; }
}
function saveUserOverrides(ov) {
    localStorage.setItem(USER_OVERRIDES_KEY, JSON.stringify(ov));
    localStorage.setItem('corryu_overrides_ts', String(Date.now()));
    pushRemoteOverrides(ov);  // async, non-blocking
}

function applyUserOverrides() {
    const ov = getUserOverrides();
    if (!Object.keys(ov).length) return;
    applyOverridesToData(ov);
}
const acDefs = window.CORRYU_CONFIG.ac_defs;
const sectorDefs = window.CORRYU_CONFIG.sector_defs;
const superSectorDefs = window.CORRYU_CONFIG.super_sector_defs;
const myPortfolio = window.CORRYU_CONFIG.my_portfolio;

// 섹터ID → 슈퍼섹터ID 역방향 맵
const sectorToSuperSector = {};
for (const [ssId, ss] of Object.entries(superSectorDefs)) {
    for (const sid of ss.sub_sectors) sectorToSuperSector[sid] = ssId;
}

let state = {
    activeAC: 'ALL',
    activeSector: 'ALL',       // 'ALL' | 섹터ID | 'SS_<ssId>' (슈퍼섹터 전체)
    expandedSuperSector: null, // null | 슈퍼섹터ID (서브탭 표시 여부)
    hideLegacy: false,
    hideShort: false,
    minAum: 0,
    minSortino: -999
};

let table;
let likedTickers = new Set();
let _currentUserId = null;

function applyHearts() {
    document.querySelectorAll('.star-btn[data-like]').forEach(function(btn) {
        var t = btn.dataset.like;
        var liked = likedTickers.has(t);
        btn.classList.toggle('starred', liked);
        btn.textContent = liked ? '♥' : '♡';
    });
}

function formatMCap(val) {
    if (!val) return '-';
    let m = val / 1e6;
    if (m >= 1000) return '$' + (m/1000).toFixed(1) + 'B';
    return '$' + Math.round(m) + 'M';
}

function renderACTabs() {
    let html = '<button class="ac-tab' + (state.activeAC === 'ALL' ? ' active' : '') + '" data-ac="ALL">전체</button>';
    let ordered = Object.entries(acDefs).sort((a,b) => a[1].order - b[1].order);
    for (let [ac, def] of ordered) {
        let isActive = state.activeAC === ac ? ' active' : '';
        html += '<button class="ac-tab' + isActive + '" data-ac="' + ac + '">' + def.icon + ' ' + def.name + '</button>';
    }
    $('#acTabs').html(html);
}

function getSuperSectorMeta(ssId) {
    let ss = superSectorDefs[ssId];
    if (!ss) return {};
    let metas = ss.sub_sectors.map(sid => sectorMeta[sid] || {});
    return {
        count:  metas.reduce((s,m) => s+(m.count||0), 0),
        active: metas.reduce((s,m) => s+(m.active||0), 0)
    };
}

function applySmhCorr() {
    try {
        const smhData = JSON.parse(localStorage.getItem('corryu_smh_corr') || 'null');
        if (!smhData) return;
        for (const sid of Object.keys(allData)) {
            for (const etf of allData[sid]) {
                if (etf.ticker in smhData) etf.smh_corr = smhData[etf.ticker];
            }
        }
    } catch(e) {}
}

// 모든 섹터에서 ticker로 ETF 검색 → { etf, sid } | null
function findETFAnywhere(ticker) {
    for (const sid of Object.keys(allData)) {
        const idx = allData[sid].findIndex(e => e.ticker === ticker);
        if (idx !== -1) return { etf: allData[sid][idx], sid, idx };
    }
    return null;
}

function applyOverridesToData(ov) {
    // ① 현재 모든 섹터에 있는 ETF 수집 (이동됐을 수도 있음)
    const etfMap = {};
    for (const sid of Object.keys(allData)) {
        for (const etf of allData[sid]) etfMap[etf.ticker] = etf;
    }
    // ② 모든 섹터 배열 초기화 후 원래 섹터에 재배치 + 레거시 상태 원복
    for (const sid of Object.keys(allData)) allData[sid] = [];
    for (const [ticker, etf] of Object.entries(etfMap)) {
        const origSid = etf._original_sector || etf._build_sector;
        if (!origSid || allData[origSid] === undefined) continue;
        if (!etf._user_override) {
            etf.is_legacy      = etf._orig_legacy;
            etf.legacy_detail  = etf._orig_legacy_detail ? etf._orig_legacy_detail.slice() : [];
            etf.legacy_reasons = etf._orig_legacy_reasons ? etf._orig_legacy_reasons.slice() : [];
        }
        if (!etf._user_override_r_anchor) {
            etf.r_anchor = etf._orig_r_anchor;
        }
        delete etf._user_sector;
        delete etf._original_sector;
        allData[origSid].push(etf);
    }
    // ③ 레거시 오버라이드 적용
    for (const [ticker, o] of Object.entries(ov)) {
        if (!('is_legacy' in o)) continue;
        const found = findETFAnywhere(ticker);
        if (!found) continue;
        found.etf.is_legacy      = o.is_legacy;
        found.etf._user_override = true;
        found.etf.legacy_detail  = o.is_legacy ? ['사용자 직접 지정'] : [];
        found.etf.legacy_reasons = o.is_legacy ? ['user_override'] : [];
    }
    // ④ 섹터 이동 오버라이드 적용
    for (const [ticker, o] of Object.entries(ov)) {
        const buildSid = etfMap[ticker] ? etfMap[ticker]._build_sector : null;
        if (!o.sector || o.sector === buildSid) continue;
        const currentFound = findETFAnywhere(ticker);
        if (!currentFound) continue;
        const { etf, sid: oldSid, idx } = currentFound;
        const newSid  = o.sector;
        if (allData[newSid] === undefined) continue;
        allData[oldSid].splice(idx, 1);
        etf._user_sector    = newSid;
        etf._original_sector = oldSid;
        allData[newSid].push(etf);
    }
    // ⑤ r_anchor 오버라이드 적용
    for (const [ticker, o] of Object.entries(ov)) {
        if (o.r_anchor === undefined) continue;
        const found = findETFAnywhere(ticker);
        if (!found) continue;
        found.etf.r_anchor = o.r_anchor;
        found.etf._user_override_r_anchor = true;
    }
}

function renderSectorTabs() {
    let sectors = [];
    if (state.activeAC === 'ALL') {
        sectors = Object.keys(sectorDefs).sort();
    } else {
        sectors = (acSectors[state.activeAC] || []).sort();
    }
    let allActive = state.activeSector === 'ALL' ? ' active' : '';
    let totalCount  = sectors.reduce((s, sid) => s + ((sectorMeta[sid]||{}).count||0), 0);
    let totalActiveN = sectors.reduce((s, sid) => s + ((sectorMeta[sid]||{}).active||0), 0);
    let html = '<button class="sec-tab' + allActive + '" data-sector="ALL">전체<span class="sec-count">' + totalActiveN + '/' + totalCount + '</span></button>';

    let renderedSS = new Set();
    for (let sid of sectors) {
        let sd = sectorDefs[sid];
        let meta = sectorMeta[sid];
        if (!meta || meta.count === 0) continue;

        let ssId = sd.super_sector;
        if (ssId) {
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
        } else {
            let isActive = state.activeSector === sid ? ' active' : '';
            html += '<button class="sec-tab' + isActive + '" data-sector="' + sid + '">';
            html += sd.icon + ' ' + sd.name;
            html += '<span class="sec-count">' + (meta.active||0) + '/' + meta.count + '</span></button>';
        }
    }
    $('#secTabs').html(html);
    renderSubSecTabs();
}

function renderSubSecTabs() {
    let ssId = state.expandedSuperSector;
    if (!ssId) { $('#subSecTabs').hide(); return; }
    let ss = superSectorDefs[ssId];
    let html = '';
    for (let sid of ss.sub_sectors) {
        let sd = sectorDefs[sid];
        let meta = sectorMeta[sid];
        if (!meta || meta.count === 0) continue;
        let isActive = state.activeSector === sid ? ' active' : '';
        html += '<button class="sec-tab sub-sec-tab' + isActive + '" data-sector="' + sid + '">';
        html += sd.icon + ' ' + sd.name;
        html += '<span class="sec-count">' + (meta.active||0) + '/' + meta.count + '</span></button>';
    }
    $('#subSecTabs').html(html).show();
}

function renderSummary() {
    let html = '';
    let sec = state.activeSector;
    if (sec === 'ALL') {
        let metas = Object.values(sectorMeta);
        let totalCount  = metas.reduce((s,m) => s+(m.count||0), 0);
        let totalActive = metas.reduce((s,m) => s+(m.active||0), 0);
        let totalLegacy = metas.reduce((s,m) => s+(m.legacy||0), 0);
        html += '<div class="stat-card"><div class="stat-value text-white">' + totalCount + '</div><div class="stat-label">ETFs</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-green-400">' + totalActive + '</div><div class="stat-label">Active</div></div>';
        if (_isAdmin) html += '<div class="stat-card"><div class="stat-value text-red-400">' + totalLegacy + '</div><div class="stat-label">Legacy</div></div>';
    } else if (sec && sec.startsWith('SS_')) {
        let ssId = sec.slice(3);
        let ssMeta = getSuperSectorMeta(ssId);
        let ss = superSectorDefs[ssId] || {};
        html += '<div class="stat-card"><div class="stat-value text-white">' + ssMeta.count + '</div><div class="stat-label">ETFs</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-green-400">' + ssMeta.active + '</div><div class="stat-label">Active</div></div>';
        if (_isAdmin) html += '<div class="stat-card"><div class="stat-value text-red-400">' + ssMeta.legacy + '</div><div class="stat-label">Legacy</div></div>';
        html += '<div class="stat-card" style="min-width:120px"><div class="stat-value text-yellow-300 text-sm">' + (ss.anchor||'—') + '</div><div class="stat-label">Anchor</div></div>';
    } else {
        let meta = sectorMeta[sec] || {};
        let sd = sectorDefs[sec] || {};
        html += '<div class="stat-card"><div class="stat-value text-white">' + (meta.count||0) + '</div><div class="stat-label">ETFs</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-green-400">' + (meta.active||0) + '</div><div class="stat-label">Active</div></div>';
        if (_isAdmin) html += '<div class="stat-card"><div class="stat-value text-red-400">' + (meta.legacy||0) + '</div><div class="stat-label">Legacy</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-blue-300">' + (meta.avg_cagr > 0 ? '+' : '') + (meta.avg_cagr||0).toFixed(1) + '%</div><div class="stat-label">Avg CAGR</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-gray-300">' + (meta.avg_vol||0).toFixed(1) + '%</div><div class="stat-label">Avg Vol</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-purple-400">' + (meta.avg_sortino||0).toFixed(2) + '</div><div class="stat-label">Avg Sortino</div></div>';
        html += '<div class="stat-card" style="min-width:120px"><div class="stat-value text-yellow-300 text-sm">' + (sd.anchor||'—') + '</div><div class="stat-label">Anchor</div></div>';
    }
    $('#summaryCards').html(html);
}

function loadSector(sectorId) {
    state.activeSector = sectorId;
    // 슈퍼섹터 소속 섹터를 직접 클릭하면 해당 슈퍼섹터를 자동 확장
    if (sectorId && !sectorId.startsWith('SS_') && sectorId !== 'ALL') {
        let sd = sectorDefs[sectorId];
        if (sd && sd.super_sector) {
            state.expandedSuperSector = sd.super_sector;
        } else {
            state.expandedSuperSector = null;
        }
    }
    renderSectorTabs();
    renderSummary();
    let data;
    if (sectorId === 'ALL') {
        data = Object.keys(allData).reduce(function(acc, k) { return acc.concat(allData[k]); }, []);
    } else if (sectorId && sectorId.startsWith('SS_')) {
        let ssId = sectorId.slice(3);
        let ss = superSectorDefs[ssId];
        data = ss ? ss.sub_sectors.reduce(function(acc, sid) { return acc.concat(allData[sid] || []); }, []) : [];
    } else {
        data = allData[sectorId] || [];
    }
    table.clear().rows.add(data).draw();
    if (typeof applyHearts === 'function') applyHearts();
}

function loadSuperSector(ssId) {
    state.activeSector = 'SS_' + ssId;
    state.expandedSuperSector = ssId;
    renderSectorTabs();
    renderSummary();
    let ss = superSectorDefs[ssId];
    let data = ss ? ss.sub_sectors.flatMap(sid => allData[sid] || []) : [];
    table.clear().rows.add(data).draw();
    if (typeof applyHearts === 'function') applyHearts();
}

// ── 토스트 알림 (전역) ────────────────────────────────────
let _toastTimer = null;
function showToast(msg, durationMs) {
    let el = document.getElementById('r-toast');
    if (!el) {
        el = document.createElement('div');
        el.id = 'r-toast';
        el.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#1e293b;color:#e2e8f0;padding:9px 18px;border-radius:10px;font-size:0.85rem;border:1px solid rgba(255,255,255,0.12);box-shadow:0 4px 20px rgba(0,0,0,0.5);z-index:9999;pointer-events:none;transition:opacity 0.3s;opacity:0;white-space:nowrap;';
        document.body.appendChild(el);
    }
    if (_toastTimer) clearTimeout(_toastTimer);
    el.textContent = msg;
    el.style.opacity = '1';
    _toastTimer = setTimeout(function() { el.style.opacity = '0'; }, durationMs || 3000);
}

function initDashboard() {
    renderACTabs();
    renderSectorTabs();
    renderSummary();

    table = $('#masterTable').DataTable({
        data: Object.keys(allData).reduce(function(acc, k) { return acc.concat(allData[k]); }, []),
        pageLength: 50,
        deferRender: true,
        lengthMenu: [[25, 50, 100, 200, -1], [25, 50, 100, 200, "All"]],
        order: [],
        columns: [
            {
                data: null, orderable: false, searchable: false,
                className: 'text-center',
                render: function(d, type, row) {
                    if (type !== 'display') return '';
                    let checked = selectedTickers.has(row.ticker) ? ' checked' : '';
                    return '<input type="checkbox" class="row-cb"' + checked + ' data-ticker="' + row.ticker + '">';
                }
            },
            {
                data: null, orderable: false, searchable: false,
                className: 'text-right text-gray-600',
                render: function(d, type, row, meta) {
                    if (type !== 'display') return meta.row + meta.settings._iDisplayStart;
                    return '<span style="font-size:0.75rem">' + (meta.row + meta.settings._iDisplayStart + 1) + '</span>';
                }
            },
            {
                data: 'ticker', className: 'text-left font-semibold',
                render: function(d, type, row) {
                    if (type !== 'display') return d;
                    let isMine = myPortfolio.includes(d);
                    let cls = isMine ? 'text-yellow-400 text-base' : 'text-blue-300';
                    let h = '<button class="star-btn" data-like="' + d + '" title="좋아요">♡</button>';
                    h += '<span class="'+cls+'">'+d+'</span>';
                    if (row.short_history) h += '<span class="badge-short" title="상장 3년 미만">짧은연혁</span>';
                    return h;
                }
            },
            {
                data: 'name', className: 'text-left text-xs text-gray-400',
                render: function(d, type, row) {
                    if (type !== 'display') return d;
                    let h = '<div class="leading-tight">'+d+'</div>';
                    if (myPortfolio.includes(row.ticker)) {
                        h += '<div class="mt-1"><span class="mine-badge">MY</span></div>';
                    }
                    return h;
                }
            },
            { data: 'rank', render: function(d,t){ return t==='display'?(d===9999?'-':d):d; } },
            { data: 'aum', render: function(d,t){ return t==='display'?formatMCap(d):d; } },
            { data: 'r_anchor', render: function(d,t) {
                if(t!=='display') return d;
                let c = d >= 0.70 ? 'text-pink-400 font-bold' : (d <= -0.3 ? 'text-green-400 font-bold' : 'text-gray-400');
                return '<span class="'+c+'">'+d.toFixed(2)+'</span>';
            } },
            { data: 'smh_corr', defaultContent: null, render: function(d,t) {
                if(t!=='display') return (d===null||d===undefined) ? -9999 : d;
                if(d===null||d===undefined) return '<span class="text-gray-700">–</span>';
                let c = d >= 0.70 ? 'text-violet-400 font-bold' : (d <= -0.3 ? 'text-green-400 font-bold' : 'text-gray-400');
                return '<span class="'+c+'">'+d.toFixed(2)+'</span>';
            } },
            { data: 'z_score', render: function(d,t,row) {
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : d;
                let c = d <= -1.5 ? 'value-down font-bold' : (d >= 2.0 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="'+c+'">'+d.toFixed(2)+'</span>';
            } },
            { data: 'ma200_pct', render: function(d,t,row) {
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : d;
                let c = d <= -10 ? 'value-down font-bold' : (d >= 15 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="'+c+'">'+(d>0?'+':'')+d.toFixed(1)+'%</span>';
            } },
            { data: 'rsi', defaultContent: null, render: function(d,t,row) {
                if(d === null || d === undefined) return t==='display' ? '<span class="text-gray-600">-</span>' : -1;
                if(t!=='display') return d;
                let c = d <= 30 ? 'value-down font-bold' : (d >= 70 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="'+c+'">'+d.toFixed(0)+'</span>';
            } },
            { data: 'range_52w', defaultContent: null, render: function(d,t,row) {
                if(d === null || d === undefined) return t==='display' ? '<span class="text-gray-600">-</span>' : -1;
                if(t!=='display') return d;
                let c = d <= 20 ? 'value-down font-bold' : (d >= 80 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="'+c+'">'+d.toFixed(0)+'%</span>';
            } },
            { data: 'mdd_52w', render: function(d,t,row) {
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : d;
                let c = d <= -20 ? 'value-down font-bold' : 'text-gray-500';
                return '<span class="'+c+'">'+d.toFixed(1)+'%</span>';
            } },
            { data: 'cagr', render: function(d,t,row) {
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : (d||0);
                return '<span class="text-gray-300 font-semibold">'+(d>0?'+':'')+d.toFixed(1)+'%</span>';
            } },
            { data: 'vol', render: function(d,t,row) {
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : (d||0);
                return '<span class="text-gray-500">'+d.toFixed(1)+'%</span>';
            } },
            { data: 'sortino', render: function(d,t,row) {
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : (d===null?-999999:d);
                let c = d > 1.2 ? 'text-purple-400 font-bold' : 'text-gray-500';
                return '<span class="'+c+'">'+d.toFixed(2)+'</span>';
            } },
            { data: 'div_yield', render: function(d,t) {
                if(t!=='display') return d==null ? -1 : d;
                if(d==null) return '<span class="text-gray-600">—</span>';
                let c = d >= 3 ? 'text-green-400 font-bold' : d >= 1 ? 'text-green-300' : 'text-gray-500';
                return '<span class="'+c+'">'+d.toFixed(2)+'%</span>';
            } },
            { data: 'inception', className: 'text-xs text-gray-600', render: function(d, t) {
                if(t !== 'display') return d || '';
                if(!d || d==='1900-01-01') return '-';
                return d.substring(2);
            } },
            { data: 'is_legacy', render: function(d,t,row) {
                if(t!=='display') return d ? 1 : 0;
                let out = '';
                if(!d) {
                    out = '<span class="badge-active">Active</span>';
                } else {
                    let detail = (row.legacy_detail||[]).join(' / ');
                    let badge = row._user_override
                        ? '<span class="badge-user-legacy">User Legacy</span>'
                        : '<span class="badge-legacy">Legacy</span>';
                    out = badge + (detail ? '<div class="text-xs text-orange-400 mt-0.5 opacity-80">'+detail+'</div>' : '');
                }
                if(row._user_sector) {
                    let sd = sectorDefs[row._user_sector] || {};
                    out += '<div style="margin-top:2px"><span class="badge-user-sector">'+(sd.icon||'')+'&nbsp;'+(sd.name||row._user_sector)+'</span></div>';
                }
                return out;
            } }
        ],
        rowCallback: function(row, data) {
            if (data.is_legacy) $(row).addClass('row-legacy');
            else $(row).removeClass('row-legacy');
            if (selectedTickers.has(data.ticker)) $(row).addClass('row-selected');
            else $(row).removeClass('row-selected');
        },
        drawCallback: function() {
            if (typeof applyHearts === 'function') applyHearts();
        }
    });

    // Custom filter
    $.fn.dataTable.ext.search.push(function(settings, searchData, dataIndex) {
        let row = settings.aoData[dataIndex]._aData;
        if (state.hideLegacy && row.is_legacy) return false;
        if (state.hideShort && row.short_history) return false;
        if (state.minAum > 0 && row.aum < state.minAum * 1e6) return false;
        if (state.minSortino > -999 && !row.short_history) {
            if (row.sortino < state.minSortino) return false;
        }
        return true;
    });

    // Event: Asset Class tab click
    $(document).on('click', '.ac-tab', function() {
        state.activeAC = $(this).data('ac');
        state.expandedSuperSector = null;
        renderACTabs();
        if (state.activeAC === 'ALL') {
            loadSector('ALL');
        } else {
            let sectors = (acSectors[state.activeAC] || []).sort();
            let firstWithData = sectors.find(s => sectorMeta[s] && sectorMeta[s].count > 0);
            if (firstWithData) loadSector(firstWithData);
            else renderSectorTabs();
        }
    });

    // Event: Super-sector tab click (슈퍼섹터 탭 → 서브탭 토글)
    $(document).on('click', '.super-sec-tab', function() {
        let ssId = $(this).data('supersec');
        if (state.expandedSuperSector === ssId) {
            // 이미 열려 있으면 닫고 전체 보기
            state.expandedSuperSector = null;
            loadSector('ALL');
        } else {
            loadSuperSector(ssId);
        }
    });

    // Event: Sector tab click (서브섹터 탭 포함)
    $(document).on('click', '.sec-tab:not(.super-sec-tab)', function() {
        loadSector($(this).data('sector'));
    });

    // Event: Filters
    $('#filterLegacy').on('change', function() { state.hideLegacy = this.checked; table.draw(); });
    $('#filterShort').on('change', function() { state.hideShort = this.checked; table.draw(); });
    $('#filterAum').on('input', function() { state.minAum = parseFloat(this.value) || 0; table.draw(); });
    $('#filterSortino').on('input', function() {
        let v = parseFloat(this.value);
        state.minSortino = isNaN(v) ? -999 : v;
        table.draw();
    });

    // ── 체크박스 이벤트 ───────────────────────────────
    window.updateFAB = function updateFAB() {
        let n = selectedTickers.size;
        $('#fab-count').text(n);
        n > 0 ? $('#fab').show() : $('#fab').hide();
        // 전체선택 체크박스 상태 동기화
        let visibleTickers = [];
        table.rows({ filter: 'applied', page: 'current' }).every(function() {
            visibleTickers.push(this.data().ticker);
        });
        let allChecked = visibleTickers.length > 0 && visibleTickers.every(t => selectedTickers.has(t));
        $('#select-all-cb').prop('checked', allChecked);
    }

    // 개별 체크박스
    $('#masterTable').on('change', 'input.row-cb', function() {
        let ticker = $(this).data('ticker');
        if (this.checked) selectedTickers.add(ticker);
        else selectedTickers.delete(ticker);
        let row = table.row($(this).closest('tr'));
        if (this.checked) $(row.node()).addClass('row-selected');
        else $(row.node()).removeClass('row-selected');
        updateFAB();
    });

    // 전체 선택/해제
    $('#select-all-cb').on('change', function() {
        let checked = this.checked;
        table.rows({ filter: 'applied', page: 'current' }).every(function() {
            let d = this.data();
            if (checked) selectedTickers.add(d.ticker);
            else selectedTickers.delete(d.ticker);
            if (checked) $(this.node()).addClass('row-selected');
            else $(this.node()).removeClass('row-selected');
        });
        $('input.row-cb').prop('checked', checked);
        updateFAB();
    });

    // 페이지/정렬/필터 변경 후 전체선택 체크박스 상태 갱신
    table.on('draw', function() { updateFAB(); });

    // ── FAB 액션 ─────────────────────────────────────
    function applyLegacyAction(setLegacy) {
        if (!_isAdmin || selectedTickers.size === 0) return;
        let ov = getUserOverrides();
        selectedTickers.forEach(function(ticker) {
            // 섹터 오버라이드가 있으면 유지한 채 is_legacy만 업데이트
            if (!ov[ticker]) ov[ticker] = {};
            ov[ticker].is_legacy = setLegacy;
            const found = findETFAnywhere(ticker);
            if (found) {
                found.etf.is_legacy      = setLegacy;
                found.etf._user_override = true;
                found.etf.legacy_detail  = setLegacy ? ['사용자 직접 지정'] : [];
                found.etf.legacy_reasons = setLegacy ? ['user_override'] : [];
            }
        });
        saveUserOverrides(ov);
        recalcSectorMeta();
        renderSectorTabs();
        renderSummary();
        selectedTickers.clear();
        table.rows().invalidate('data').draw(false);
        $('#select-all-cb').prop('checked', false);
        updateFAB();
    }

    // ── 카테고리 이동 ──────────────────────────────────
    function buildSectorModal() {
        // 선택된 ETF들의 현재 섹터 수집 (단일이면 하이라이트)
        const curSectors = new Set();
        selectedTickers.forEach(function(tk) {
            const found = findETFAnywhere(tk);
            if (found) curSectors.add(found.sid);
        });
        $('#modal-sel-info').text(selectedTickers.size + '개 종목 → 이동할 카테고리를 선택하세요');
        const ordered = Object.entries(acDefs).sort((a,b) => a[1].order - b[1].order);
        let html = '';
        for (const [ac, acDef] of ordered) {
            const sids = (acSectors[ac] || []).sort();
            if (!sids.length) continue;
            html += '<div class="smg">' + acDef.icon + ' ' + acDef.name + '</div>';
            html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-bottom:4px">';
            for (const sid of sids) {
                const sd = sectorDefs[sid];
                if (!sd) continue;
                const isCur = curSectors.size === 1 && curSectors.has(sid);
                html += '<button class="smb' + (isCur ? ' cur' : '') + '" data-sid="' + sid + '">';
                html += '<span style="font-size:1rem">' + (sd.icon||'') + '</span>';
                html += '<div><div style="font-weight:600;font-size:0.8rem">' + sd.name + '</div>';
                html += '<div style="font-size:0.68rem;color:#475569">' + (sd.name_en||'') + '</div></div>';
                html += '</button>';
            }
            html += '</div>';
        }
        $('#sector-modal-body').html(html);
    }

    function applySectorMove(newSectorId) {
        if (!newSectorId || selectedTickers.size === 0) return;
        const tickersToRecompute = [];
        let ov = getUserOverrides();
        selectedTickers.forEach(function(ticker) {
            const found = findETFAnywhere(ticker);
            if (!found) return;
            const { etf, sid: oldSid } = found;
            if (!ov[ticker]) ov[ticker] = {};
            if (oldSid === newSectorId) {
                // 이미 이 섹터 → 섹터 오버라이드 해제
                delete ov[ticker].sector;
                delete ov[ticker].r_anchor;
                delete etf._user_sector;
                delete etf._original_sector;
                if (!Object.keys(ov[ticker]).length) delete ov[ticker];
                return;
            }
            tickersToRecompute.push(ticker);
            // allData에서 이동
            allData[oldSid] = allData[oldSid].filter(e => e.ticker !== ticker);
            etf._user_sector     = newSectorId;
            etf._original_sector = etf._build_sector; // Store the build-time original sector
            if (!allData[newSectorId]) allData[newSectorId] = [];
            allData[newSectorId].push(etf);
            // localStorage 저장 (기존 is_legacy 보존)
            ov[ticker].sector = newSectorId;
        });
        saveUserOverrides(ov);
        recalcSectorMeta();
        renderSectorTabs();
        renderSummary();
        selectedTickers.clear();
        $('#sector-modal').removeClass('show');
        loadSector(state.activeSector);
        updateFAB();
        if (tickersToRecompute.length) recomputeRanchorsAsync(tickersToRecompute, newSectorId);
    }

    // ── 브라우저-사이드 r_anchor 재계산 유틸 ─────────────────────────────
    function _sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

    function _pearson(xs, ys) {
        const n = xs.length;
        if (n < 2) return NaN;
        let mx = 0, my = 0;
        for (let i = 0; i < n; i++) { mx += xs[i]; my += ys[i]; }
        mx /= n; my /= n;
        let num = 0, dx2 = 0, dy2 = 0;
        for (let i = 0; i < n; i++) {
            const dx = xs[i] - mx, dy = ys[i] - my;
            num += dx * dy; dx2 += dx * dx; dy2 += dy * dy;
        }
        return (dx2 && dy2) ? num / Math.sqrt(dx2 * dy2) : NaN;
    }

    function _pairwiseReturns(pA, pB) {
        const dates = Object.keys(pA).filter(d => d in pB).sort();
        const rA = [], rB = [];
        for (let i = 1; i < dates.length; i++) {
            const a0 = pA[dates[i-1]], a1 = pA[dates[i]];
            const b0 = pB[dates[i-1]], b1 = pB[dates[i]];
            if (a0 && a1 && b0 && b1) {
                rA.push((a1 - a0) / a0);
                rB.push((b1 - b0) / b0);
            }
        }
        return [rA, rB];
    }

    function _calcCorr(pA, pB) {
        const [rA, rB] = _pairwiseReturns(pA, pB);
        if (rA.length < 24) return null;
        const c = _pearson(rA, rB);
        return isFinite(c) ? Math.round(c * 10000) / 10000 : null;
    }

    function _makeYfUrls(ticker) {
        const tk = encodeURIComponent(ticker);
        const yf1 = 'https://query1.finance.yahoo.com/v8/finance/chart/' + tk + '?range=max&interval=1mo&includeAdjustedClose=true';
        return [
            '/api/yf?ticker=' + tk + '&range=max&interval=1mo',
            yf1,
            'https://query2.finance.yahoo.com/v8/finance/chart/' + tk + '?range=max&interval=1mo&includeAdjustedClose=true',
            'https://corsproxy.io/?' + encodeURIComponent(yf1),
        ];
    }

    function _parseYfMonthly(data) {
        const result = data && data.chart && data.chart.result && data.chart.result[0];
        if (!result) return null;
        const ts  = result.timestamp;
        const adj = (result.indicators && result.indicators.adjclose && result.indicators.adjclose[0] && result.indicators.adjclose[0].adjclose)
                 || (result.indicators && result.indicators.quote && result.indicators.quote[0] && result.indicators.quote[0].close);
        if (!ts || !adj) return null;
        const prices = {};
        for (let i = 0; i < ts.length; i++) {
            if (adj[i] != null) {
                const d = new Date(ts[i] * 1000);
                prices[d.getUTCFullYear() + '-' + String(d.getUTCMonth() + 1).padStart(2, '0')] = adj[i];
            }
        }
        return Object.keys(prices).length >= 3 ? prices : null;
    }

    async function _fetchYfMonthly(ticker) {
        for (const url of _makeYfUrls(ticker)) {
            for (let attempt = 0; attempt < 2; attempt++) {
                try {
                    const r = await fetch(url);
                    if (r.status === 429) { await _sleep(3000 * (attempt + 1)); continue; }
                    if (!r.ok) break;
                    const prices = _parseYfMonthly(await r.json());
                    if (prices) return prices;
                    break;
                } catch(e) { await _sleep(500); }
            }
        }
        return null;
    }

    async function recomputeRanchorsAsync(tickers, newSectorId) {
        const anchor = (sectorDefs[newSectorId] || {}).anchor;
        if (!anchor || anchor === '—') return;
        const tickerList = Array.isArray(tickers) ? tickers : Array.from(tickers);
        if (!tickerList.length) return;
        showToast('r_anchor 재계산 중… 앵커: ' + anchor + ' / ' + tickerList.length + '종목', 60000);
        const anchorPrices = await _fetchYfMonthly(anchor);
        if (!anchorPrices) {
            showToast('앵커(' + anchor + ') 가격 조회 실패', 4000);
            return;
        }
        let ok = 0;
        const ov = getUserOverrides();
        for (const ticker of tickerList) {
            const found = findETFAnywhere(ticker);
            if (!found) continue;
            const prices = await _fetchYfMonthly(ticker);
            if (!prices) continue;
            const corr = _calcCorr(anchorPrices, prices);
            if (corr === null) continue;
            found.etf.r_anchor = corr;
            if (!ov[ticker]) ov[ticker] = {};
            ov[ticker].r_anchor = corr;
            ok++;
            await _sleep(150);
        }
        saveUserOverrides(ov);
        if (ok > 0 && typeof table !== 'undefined') table.rows().invalidate('data').draw(false);
        showToast('r_anchor 재계산 완료 (' + ok + '/' + tickerList.length + '종목)', 4000);
    }

    $('#fab-btn-legacy').on('click', function() { applyLegacyAction(true); });
    $('#fab-btn-unlegacy').on('click', function() { applyLegacyAction(false); });
    $('#fab-btn-move').on('click', function() {
        if (selectedTickers.size === 0) return;
        buildSectorModal();
        $('#sector-modal').addClass('show');
    });
    $('#sector-modal-close').on('click', function() { $('#sector-modal').removeClass('show'); });
    $('#sector-modal').on('click', function(e) { if (e.target === this) $(this).removeClass('show'); });
    $(document).on('click', '#sector-modal-body .smb', function() {
        applySectorMove($(this).data('sid'));
    });
    $('#fab-btn-clear').on('click', function() {
        selectedTickers.clear();
        $('input.row-cb').prop('checked', false);
        table.rows().every(function() { $(this.node()).removeClass('row-selected'); });
        updateFAB();
    });

    // ── 실행취소 / 초기화 ─────────────────────────────
}

$(document).ready(function() {
    fetch('/etf_data.json')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            sectorMeta = d.sectorMeta;
            allData = d.allData;
            // 빌드 기본값 스냅샷 저장
            for (var sid in allData) {
                if (!allData.hasOwnProperty(sid)) continue;
                for (var i=0; i<allData[sid].length; i++) {
                    allData[sid][i]._orig_legacy = allData[sid][i].is_legacy;
                }
            }

            // 1. 기본 상태(비로그인)로 데이터 즉시 준비
            stripLegacyForNonAdmin();
            try { applySmhCorr(); } catch(e) {}
            try { recalcSectorMeta(); } catch(e) {}

            // 2. 무조건 대시보드 먼저 렌더링!
            initDashboard();

            // 언어 전환기 리스너 (백그라운드에서 트리거됨)
            document.addEventListener('i18n:ready', function() {
                renderACTabs();
                renderSectorTabs();
                renderSummary();
                updateFAB();
                if (typeof table !== 'undefined') table.rows().invalidate('data').draw(false);
            });

            // 3. 백그라운드 비동기 작업 (Admin, i18n, 동기화)
            setTimeout(async function() {
                try {
                    await I18n.init();
                } catch(e) {}

                try {
                    const isAdmin = await detectAdmin();
                    applyAdminUI(isAdmin);

                    if (isAdmin) {
                        // 어드민인 경우 원래 레거시 상태 복구
                        for (var sid in allData) {
                            if (!allData.hasOwnProperty(sid)) continue;
                            for (var i=0; i<allData[sid].length; i++) {
                                allData[sid][i].is_legacy = allData[sid][i]._orig_legacy;
                            }
                        }

                        let ov = getUserOverrides();
                        if (Object.keys(ov).length) applyOverridesToData(ov);
                        recalcSectorMeta();
                        renderSectorTabs();
                        renderSummary();
                        table.rows().invalidate('data').draw(false);
                    }
                } catch(authErr) {
                    console.warn('[CORRYU] Background init failed:', authErr);
                }
            }, 50);
        })
        .catch(function(err) {
            console.error('[CORRYU] 데이터 파싱 실패:', err);
        });
});


// ═══════════════════════════════════════════════════════════════════════
// ❤️ 인기 종목 랭킹 (ticker_likes) — index.html only
// ═══════════════════════════════════════════════════════════════════════
(async function initTrending() {
  if (typeof CorryuAuth === 'undefined' || !CorryuAuth.isConfigured) return;

  const section = document.getElementById('trending-section');
  if (!section) return;
  section.style.display = 'block';

  const TOP_N = 5;

  function rankItemHTML(rank, ticker, count, barPct, period) {
    const medals = ['🥇','🥈','🥉'];
    const medal  = medals[rank - 1] || `<span style="font-size:.75rem;color:#475569;font-weight:800">${rank}</span>`;
    const barColor = period === 'weekly' ? 'rgba(251,191,36,0.6)' : 'rgba(168,85,247,0.6)';
    return `<a href="/etf-detail?ticker=${encodeURIComponent(ticker)}"
        style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:8px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04);text-decoration:none;transition:background .15s"
        onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='rgba(255,255,255,0.02)'">
      <span style="font-size:.9rem;flex-shrink:0;min-width:22px;text-align:center">${medal}</span>
      <span style="font-weight:800;font-size:.84rem;color:#e2e8f0;min-width:52px">${ticker}</span>
      <div style="flex:1;height:4px;background:rgba(255,255,255,0.05);border-radius:2px;overflow:hidden">
        <div style="height:100%;border-radius:2px;background:${barColor};width:${barPct}%"></div>
      </div>
      <span style="font-size:.75rem;font-weight:700;color:#64748b;flex-shrink:0">❤️ ${count}</span>
    </a>`;
  }

  function emptyHTML() {
    return `<div data-i18n="index.trending.empty" style="color:#334155;font-size:.78rem;text-align:center;padding:16px 0">아직 좋아요 데이터가 없습니다</div>`;
  }

  async function loadWeekly() {
    const el = document.getElementById('trending-weekly');
    const { data, error } = await _sb.from('ticker_likes_weekly')
      .select('ticker,weekly_likes')
      .order('weekly_likes', { ascending: false })
      .limit(TOP_N);
    if (error || !data || data.length === 0) { el.innerHTML = emptyHTML(); return; }
    const maxLikes = data[0].weekly_likes;
    el.innerHTML = data.map((row, i) => {
      const pct = maxLikes > 0 ? Math.round((row.weekly_likes / maxLikes) * 100) : 0;
      return rankItemHTML(i + 1, row.ticker, row.weekly_likes, pct, 'weekly');
    }).join('');
  }

  async function loadMonthly() {
    const el = document.getElementById('trending-monthly');
    const { data, error } = await _sb.from('ticker_likes_monthly')
      .select('ticker,monthly_likes')
      .order('monthly_likes', { ascending: false })
      .limit(TOP_N);
    if (error || !data || data.length === 0) { el.innerHTML = emptyHTML(); return; }
    const maxLikes = data[0].monthly_likes;
    el.innerHTML = data.map((row, i) => {
      const pct = maxLikes > 0 ? Math.round((row.monthly_likes / maxLikes) * 100) : 0;
      return rankItemHTML(i + 1, row.ticker, row.monthly_likes, pct, 'monthly');
    }).join('');
  }

  await Promise.all([loadWeekly(), loadMonthly()]);
  setInterval(() => { loadWeekly(); loadMonthly(); }, 30 * 60 * 1000);
})();

(function initLikes() {
    if (typeof CorryuAuth === 'undefined' || !CorryuAuth.isConfigured) return;

    CorryuAuth.onAuthChange(async function(event, session) {
        if (session && session.user) {
            _currentUserId = session.user.id;
            var res = await _sb.from('ticker_likes').select('ticker').eq('user_id', _currentUserId);
            likedTickers = new Set();
            if (res.data) res.data.forEach(function(r) { likedTickers.add(r.ticker); });
        } else {
            _currentUserId = null;
            likedTickers = new Set();
        }
        applyHearts();
    });
})();

$(document).on('click', '.star-btn[data-like]', async function(e) {
    e.stopPropagation();
    const ticker = this.dataset.like;
    if (!_currentUserId) {
        showToast('로그인이 필요한 기능이에요', 2500);
        setTimeout(function() { window.location.href = '/login'; }, 1200);
        return;
    }
    const isLiked = likedTickers.has(ticker);
    if (isLiked) {
        likedTickers.delete(ticker);
        await _sb.from('ticker_likes').delete().eq('ticker', ticker).eq('user_id', _currentUserId);
    } else {
        likedTickers.add(ticker);
        await _sb.from('ticker_likes').upsert({ ticker: ticker, user_id: _currentUserId });
    }
    $(this).toggleClass('starred', likedTickers.has(ticker));
    $(this).text(likedTickers.has(ticker) ? '♥' : '♡');
});
