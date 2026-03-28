/**
 * CORRYU Dashboard — 메인 엔트리 포인트 (dashboard.js)
 * ──────────────────────────────────────────────────────────
 * 탭 렌더링, DataTable 초기화, 필터, 부트스트랩 시퀀스.
 *
 * 의존성 (로드 순서):
 *  1. dashboard-state.js    — 전역 상태 & 유틸리티
 *  2. dashboard-overrides.js — 오버라이드 & 동기화
 *  3. dashboard.js          — 이 파일 (entry point)
 *  4. dashboard-likes.js    — 좋아요 & 트렌딩 (독립 IIFE)
 */

// ── 탭 렌더링 ──────────────────────────────────────────────

function renderACTabs() {
    var html = '<button class="ac-tab' + (state.activeAC === 'ALL' ? ' active' : '') + '" data-ac="ALL">전체</button>';
    var ordered = Object.entries(acDefs).sort(function (a, b) { return a[1].order - b[1].order; });
    for (var i = 0; i < ordered.length; i++) {
        var ac = ordered[i][0], def = ordered[i][1];
        var isActive = state.activeAC === ac ? ' active' : '';
        html += '<button class="ac-tab' + isActive + '" data-ac="' + ac + '">' + def.icon + ' ' + def.name + '</button>';
    }
    $('#acTabs').html(html);
}

function renderSectorTabs() {
    var sectors = [];
    if (state.activeAC === 'ALL') {
        sectors = Object.keys(sectorDefs).sort();
    } else {
        sectors = (acSectors[state.activeAC] || []).sort();
    }
    var allActive = state.activeSector === 'ALL' ? ' active' : '';
    var totalCount = sectors.reduce(function (s, sid) { return s + ((sectorMeta[sid] || {}).count || 0); }, 0);
    var totalActiveN = sectors.reduce(function (s, sid) { return s + ((sectorMeta[sid] || {}).active || 0); }, 0);
    var html = '<button class="sec-tab' + allActive + '" data-sector="ALL">전체<span class="sec-count">' + totalActiveN + '/' + totalCount + '</span></button>';

    var renderedSS = new Set();
    for (var i = 0; i < sectors.length; i++) {
        var sid = sectors[i];
        var sd = sectorDefs[sid];
        var meta = sectorMeta[sid];
        if (!meta || meta.count === 0) continue;

        var ssId = sd.super_sector;
        if (ssId) {
            if (renderedSS.has(ssId)) continue;
            renderedSS.add(ssId);
            var ss = superSectorDefs[ssId];
            var ssMeta = getSuperSectorMeta(ssId);
            var ssIsActive = state.expandedSuperSector === ssId;
            var isActiveSS = (state.activeSector === 'SS_' + ssId) ? ' active' : '';
            var arrow = ssIsActive ? ' ▾' : ' ▸';
            html += '<button class="sec-tab super-sec-tab' + isActiveSS + '" data-supersec="' + ssId + '">';
            html += ss.icon + ' ' + ss.name;
            html += '<span class="sec-count">' + ssMeta.active + '/' + ssMeta.count + '</span>';
            html += '<span class="expand-arrow">' + arrow + '</span></button>';
        } else {
            var isActive2 = state.activeSector === sid ? ' active' : '';
            html += '<button class="sec-tab' + isActive2 + '" data-sector="' + sid + '">';
            html += sd.icon + ' ' + sd.name;
            html += '<span class="sec-count">' + (meta.active || 0) + '/' + meta.count + '</span></button>';
        }
    }
    $('#secTabs').html(html);
    renderSubSecTabs();
}

function renderSubSecTabs() {
    var ssId = state.expandedSuperSector;
    if (!ssId) { $('#subSecTabs').hide(); return; }
    var ss = superSectorDefs[ssId];
    var html = '';
    for (var i = 0; i < ss.sub_sectors.length; i++) {
        var sid = ss.sub_sectors[i];
        var sd = sectorDefs[sid];
        var meta = sectorMeta[sid];
        if (!meta || meta.count === 0) continue;
        var isActive = state.activeSector === sid ? ' active' : '';
        html += '<button class="sec-tab sub-sec-tab' + isActive + '" data-sector="' + sid + '">';
        html += sd.icon + ' ' + sd.name;
        html += '<span class="sec-count">' + (meta.active || 0) + '/' + meta.count + '</span></button>';
    }
    $('#subSecTabs').html(html).show();
}

// ── 요약 카드 ─────────────────────────────────────────────

function renderSummary() {
    var html = '';
    var sec = state.activeSector;
    if (sec === 'ALL') {
        var metas = Object.values(sectorMeta);
        var totalCount = metas.reduce(function (s, m) { return s + (m.count || 0); }, 0);
        var totalActive = metas.reduce(function (s, m) { return s + (m.active || 0); }, 0);
        var totalLegacy = metas.reduce(function (s, m) { return s + (m.legacy || 0); }, 0);
        html += '<div class="stat-card"><div class="stat-value text-white">' + totalCount + '</div><div class="stat-label">ETFs</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-green-400">' + totalActive + '</div><div class="stat-label">Active</div></div>';
        if (_isAdmin) html += '<div class="stat-card"><div class="stat-value text-red-400">' + totalLegacy + '</div><div class="stat-label">Legacy</div></div>';
    } else if (sec && sec.startsWith('SS_')) {
        var ssId = sec.slice(3);
        var ssMeta = getSuperSectorMeta(ssId);
        var ss = superSectorDefs[ssId] || {};
        html += '<div class="stat-card"><div class="stat-value text-white">' + ssMeta.count + '</div><div class="stat-label">ETFs</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-green-400">' + ssMeta.active + '</div><div class="stat-label">Active</div></div>';
        if (_isAdmin) html += '<div class="stat-card"><div class="stat-value text-red-400">' + (ssMeta.count - ssMeta.active) + '</div><div class="stat-label">Legacy</div></div>';
        html += '<div class="stat-card" style="min-width:120px"><div class="stat-value text-yellow-300 text-sm">' + (ss.anchor || '—') + '</div><div class="stat-label">Anchor</div></div>';
    } else {
        var meta = sectorMeta[sec] || {};
        var sd = sectorDefs[sec] || {};
        html += '<div class="stat-card"><div class="stat-value text-white">' + (meta.count || 0) + '</div><div class="stat-label">ETFs</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-green-400">' + (meta.active || 0) + '</div><div class="stat-label">Active</div></div>';
        if (_isAdmin) html += '<div class="stat-card"><div class="stat-value text-red-400">' + (meta.legacy || 0) + '</div><div class="stat-label">Legacy</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-blue-300">' + (meta.avg_cagr > 0 ? '+' : '') + (meta.avg_cagr || 0).toFixed(1) + '%</div><div class="stat-label">Avg CAGR</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-gray-300">' + (meta.avg_vol || 0).toFixed(1) + '%</div><div class="stat-label">Avg Vol</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-purple-400">' + (meta.avg_sortino || 0).toFixed(2) + '</div><div class="stat-label">Avg Sortino</div></div>';
        html += '<div class="stat-card" style="min-width:120px"><div class="stat-value text-yellow-300 text-sm">' + (sd.anchor || '—') + '</div><div class="stat-label">Anchor</div></div>';
    }
    $('#summaryCards').html(html);
}

// ── 섹터 로딩 ─────────────────────────────────────────────

function loadSector(sectorId) {
    state.activeSector = sectorId;
    if (sectorId && !sectorId.startsWith('SS_') && sectorId !== 'ALL') {
        var sd = sectorDefs[sectorId];
        if (sd && sd.super_sector) {
            state.expandedSuperSector = sd.super_sector;
        } else {
            state.expandedSuperSector = null;
        }
    }
    renderSectorTabs();
    renderSummary();
    var data;
    if (sectorId === 'ALL') {
        data = Object.keys(allData).reduce(function (acc, k) { return acc.concat(allData[k]); }, []);
    } else if (sectorId && sectorId.startsWith('SS_')) {
        var ssId = sectorId.slice(3);
        var ss = superSectorDefs[ssId];
        data = ss ? ss.sub_sectors.reduce(function (acc, sid) { return acc.concat(allData[sid] || []); }, []) : [];
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
    var ss = superSectorDefs[ssId];
    var data = ss ? ss.sub_sectors.reduce(function (acc, sid) { return acc.concat(allData[sid] || []); }, []) : [];
    table.clear().rows.add(data).draw();
    if (typeof applyHearts === 'function') applyHearts();
}

// ── DataTable 초기화 + 이벤트 바인딩 ─────────────────────

function initDashboard() {
    renderACTabs();
    renderSectorTabs();
    renderSummary();

    table = $('#masterTable').DataTable({
        data: Object.keys(allData).reduce(function (acc, k) { return acc.concat(allData[k]); }, []),
        pageLength: 50,
        deferRender: true,
        lengthMenu: [[25, 50, 100, 200, -1], [25, 50, 100, 200, "All"]],
        order: [],
        columns: [
            {
                data: null, orderable: false, searchable: false,
                className: 'text-center',
                render: function (d, type, row) {
                    if (type !== 'display') return '';
                    var checked = selectedTickers.has(row.ticker) ? ' checked' : '';
                    return '<input type="checkbox" class="row-cb"' + checked + ' data-ticker="' + row.ticker + '">';
                }
            },
            {
                data: null, orderable: false, searchable: false,
                className: 'text-right text-gray-600',
                render: function (d, type, row, meta) {
                    if (type !== 'display') return meta.row + meta.settings._iDisplayStart;
                    return '<span style="font-size:0.75rem">' + (meta.row + meta.settings._iDisplayStart + 1) + '</span>';
                }
            },
            {
                data: 'ticker', className: 'text-left font-semibold',
                render: function (d, type, row) {
                    if (type !== 'display') return d;
                    var isMine = myPortfolio.includes(d);
                    var cls = isMine ? 'text-yellow-400 text-base' : 'text-blue-300';
                    var h = '<button class="star-btn" data-like="' + d + '" title="좋아요">♡</button>';
                    h += '<span class="' + cls + '">' + d + '</span>';
                    if (row.short_history) h += '<span class="badge-short" title="상장 3년 미만">짧은연혁</span>';
                    return h;
                }
            },
            {
                data: 'name', className: 'text-left text-xs text-gray-400',
                render: function (d, type, row) {
                    if (type !== 'display') return d;
                    var h = '<div class="leading-tight">' + d + '</div>';
                    if (myPortfolio.includes(row.ticker)) {
                        h += '<div class="mt-1"><span class="mine-badge">MY</span></div>';
                    }
                    return h;
                }
            },
            { data: 'rank', render: function (d, t) { return t === 'display' ? (d === 9999 ? '-' : d) : d; } },
            { data: 'aum', render: function (d, t) { return t === 'display' ? formatMCap(d) : d; } },
            { data: 'r_anchor', render: function (d, t) {
                if (t !== 'display') return d;
                var c = d >= 0.70 ? 'text-pink-400 font-bold' : (d <= -0.3 ? 'text-green-400 font-bold' : 'text-gray-400');
                return '<span class="' + c + '">' + d.toFixed(2) + '</span>';
            } },
            { data: 'smh_corr', defaultContent: null, render: function (d, t) {
                if (t !== 'display') return (d === null || d === undefined) ? -9999 : d;
                if (d === null || d === undefined) return '<span class="text-gray-700">–</span>';
                var c = d >= 0.70 ? 'text-violet-400 font-bold' : (d <= -0.3 ? 'text-green-400 font-bold' : 'text-gray-400');
                return '<span class="' + c + '">' + d.toFixed(2) + '</span>';
            } },
            { data: 'z_score', render: function (d, t, row) {
                if (row.short_history && t === 'display') return '<span class="text-gray-600">-</span>';
                if (t !== 'display') return row.short_history ? -999999 : d;
                var c = d <= -1.5 ? 'value-down font-bold' : (d >= 2.0 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="' + c + '">' + d.toFixed(2) + '</span>';
            } },
            { data: 'ma200_pct', render: function (d, t, row) {
                if (row.short_history && t === 'display') return '<span class="text-gray-600">-</span>';
                if (t !== 'display') return row.short_history ? -999999 : d;
                var c = d <= -10 ? 'value-down font-bold' : (d >= 15 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="' + c + '">' + (d > 0 ? '+' : '') + d.toFixed(1) + '%</span>';
            } },
            { data: 'rsi', defaultContent: null, render: function (d, t) {
                if (d === null || d === undefined) return t === 'display' ? '<span class="text-gray-600">-</span>' : -1;
                if (t !== 'display') return d;
                var c = d <= 30 ? 'value-down font-bold' : (d >= 70 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="' + c + '">' + d.toFixed(0) + '</span>';
            } },
            { data: 'range_52w', defaultContent: null, render: function (d, t) {
                if (d === null || d === undefined) return t === 'display' ? '<span class="text-gray-600">-</span>' : -1;
                if (t !== 'display') return d;
                var c = d <= 20 ? 'value-down font-bold' : (d >= 80 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="' + c + '">' + d.toFixed(0) + '%</span>';
            } },
            { data: 'mdd_52w', render: function (d, t, row) {
                if (row.short_history && t === 'display') return '<span class="text-gray-600">-</span>';
                if (t !== 'display') return row.short_history ? -999999 : d;
                var c = d <= -20 ? 'value-down font-bold' : 'text-gray-500';
                return '<span class="' + c + '">' + d.toFixed(1) + '%</span>';
            } },
            { data: 'cagr', render: function (d, t, row) {
                if (row.short_history && t === 'display') return '<span class="text-gray-600">-</span>';
                if (t !== 'display') return row.short_history ? -999999 : (d || 0);
                return '<span class="text-gray-300 font-semibold">' + (d > 0 ? '+' : '') + d.toFixed(1) + '%</span>';
            } },
            { data: 'vol', render: function (d, t, row) {
                if (row.short_history && t === 'display') return '<span class="text-gray-600">-</span>';
                if (t !== 'display') return row.short_history ? -999999 : (d || 0);
                return '<span class="text-gray-500">' + d.toFixed(1) + '%</span>';
            } },
            { data: 'sortino', render: function (d, t, row) {
                if (row.short_history && t === 'display') return '<span class="text-gray-600">-</span>';
                if (t !== 'display') return row.short_history ? -999999 : (d === null ? -999999 : d);
                var c = d > 1.2 ? 'text-purple-400 font-bold' : 'text-gray-500';
                return '<span class="' + c + '">' + d.toFixed(2) + '</span>';
            } },
            { data: 'div_yield', render: function (d, t) {
                if (t !== 'display') return d == null ? -1 : d;
                if (d == null) return '<span class="text-gray-600">—</span>';
                var c = d >= 3 ? 'text-green-400 font-bold' : d >= 1 ? 'text-green-300' : 'text-gray-500';
                return '<span class="' + c + '">' + d.toFixed(2) + '%</span>';
            } },
            { data: 'inception', className: 'text-xs text-gray-600', render: function (d, t) {
                if (t !== 'display') return d || '';
                if (!d || d === '1900-01-01') return '-';
                return d.substring(2);
            } },
            { data: 'is_legacy', render: function (d, t, row) {
                if (t !== 'display') return d ? 1 : 0;
                var out = '';
                if (!d) {
                    out = '<span class="badge-active">Active</span>';
                } else {
                    var detail = (row.legacy_detail || []).join(' / ');
                    var badge = row._user_override
                        ? '<span class="badge-user-legacy">User Legacy</span>'
                        : '<span class="badge-legacy">Legacy</span>';
                    out = badge + (detail ? '<div class="text-xs text-orange-400 mt-0.5 opacity-80">' + detail + '</div>' : '');
                }
                if (row._user_sector) {
                    var sd2 = sectorDefs[row._user_sector] || {};
                    out += '<div style="margin-top:2px"><span class="badge-user-sector">' + (sd2.icon || '') + '&nbsp;' + (sd2.name || row._user_sector) + '</span></div>';
                }
                return out;
            } }
        ],
        rowCallback: function (row, data) {
            if (data.is_legacy) $(row).addClass('row-legacy');
            else $(row).removeClass('row-legacy');
            if (selectedTickers.has(data.ticker)) $(row).addClass('row-selected');
            else $(row).removeClass('row-selected');
        },
        drawCallback: function () {
            if (typeof applyHearts === 'function') applyHearts();
        }
    });

    // Custom filter
    $.fn.dataTable.ext.search.push(function (settings, searchData, dataIndex) {
        var row = settings.aoData[dataIndex]._aData;
        if (state.hideLegacy && row.is_legacy) return false;
        if (state.hideShort && row.short_history) return false;
        if (state.minAum > 0 && row.aum < state.minAum * 1e6) return false;
        if (state.minSortino > -999 && !row.short_history) {
            if (row.sortino < state.minSortino) return false;
        }
        return true;
    });

    // Event: Asset Class tab click
    $(document).on('click', '.ac-tab', function () {
        state.activeAC = $(this).data('ac');
        state.expandedSuperSector = null;
        renderACTabs();
        if (state.activeAC === 'ALL') {
            loadSector('ALL');
        } else {
            var sectors = (acSectors[state.activeAC] || []).sort();
            var firstWithData = sectors.find(function (s) { return sectorMeta[s] && sectorMeta[s].count > 0; });
            if (firstWithData) loadSector(firstWithData);
            else renderSectorTabs();
        }
    });

    // Event: Super-sector tab click
    $(document).on('click', '.super-sec-tab', function () {
        var ssId = $(this).data('supersec');
        if (state.expandedSuperSector === ssId) {
            state.expandedSuperSector = null;
            loadSector('ALL');
        } else {
            loadSuperSector(ssId);
        }
    });

    // Event: Sector tab click
    $(document).on('click', '.sec-tab:not(.super-sec-tab)', function () {
        loadSector($(this).data('sector'));
    });

    // Event: Filters
    $('#filterLegacy').on('change', function () { state.hideLegacy = this.checked; table.draw(); });
    $('#filterShort').on('change', function () { state.hideShort = this.checked; table.draw(); });
    $('#filterAum').on('input', function () { state.minAum = parseFloat(this.value) || 0; table.draw(); });
    $('#filterSortino').on('input', function () {
        var v = parseFloat(this.value);
        state.minSortino = isNaN(v) ? -999 : v;
        table.draw();
    });

    // ── 체크박스 이벤트 ────────────────────────────────
    window.updateFAB = function updateFAB() {
        var n = selectedTickers.size;
        $('#fab-count').text(n);
        n > 0 ? $('#fab').show() : $('#fab').hide();
        var visibleTickers = [];
        table.rows({ filter: 'applied', page: 'current' }).every(function () {
            visibleTickers.push(this.data().ticker);
        });
        var allChecked = visibleTickers.length > 0 && visibleTickers.every(function (t) { return selectedTickers.has(t); });
        $('#select-all-cb').prop('checked', allChecked);
    };

    $('#masterTable').on('change', 'input.row-cb', function () {
        var ticker = $(this).data('ticker');
        if (this.checked) selectedTickers.add(ticker);
        else selectedTickers.delete(ticker);
        var row = table.row($(this).closest('tr'));
        if (this.checked) $(row.node()).addClass('row-selected');
        else $(row.node()).removeClass('row-selected');
        updateFAB();
    });

    $('#select-all-cb').on('change', function () {
        var checked = this.checked;
        table.rows({ filter: 'applied', page: 'current' }).every(function () {
            var d = this.data();
            if (checked) selectedTickers.add(d.ticker);
            else selectedTickers.delete(d.ticker);
            if (checked) $(this.node()).addClass('row-selected');
            else $(this.node()).removeClass('row-selected');
        });
        $('input.row-cb').prop('checked', checked);
        updateFAB();
    });

    table.on('draw', function () { updateFAB(); });

    // FAB 오버라이드 이벤트 바인딩 (dashboard-overrides.js)
    initOverrideEvents();
}

// ── 부트스트랩 시퀀스 ──────────────────────────────────────

$(document).ready(function () {
    fetch('/etf_data.json')
        .then(function (r) { return r.json(); })
        .then(function (d) {
            sectorMeta = d.sectorMeta;
            allData = d.allData;
            // 빌드 기본값 스냅샷 저장
            for (var sid in allData) {
                if (!allData.hasOwnProperty(sid)) continue;
                for (var i = 0; i < allData[sid].length; i++) {
                    allData[sid][i]._orig_legacy = allData[sid][i].is_legacy;
                }
            }

            // 1. 기본 상태(비로그인)로 데이터 즉시 준비
            stripLegacyForNonAdmin();
            try { applySmhCorr(); } catch (e) { }
            try { recalcSectorMeta(); } catch (e) { }

            // 2. 무조건 대시보드 먼저 렌더링!
            initDashboard();

            // 언어 전환기 리스너
            document.addEventListener('i18n:ready', function () {
                renderACTabs();
                renderSectorTabs();
                renderSummary();
                updateFAB();
                if (typeof table !== 'undefined') table.rows().invalidate('data').draw(false);
            });

            // 3. 백그라운드 비동기 작업 (Admin, i18n, 동기화)
            setTimeout(async function () {
                try {
                    await I18n.init();
                } catch (e) { }

                try {
                    var isAdmin = await detectAdmin();
                    applyAdminUI(isAdmin);

                    if (isAdmin) {
                        for (var sid2 in allData) {
                            if (!allData.hasOwnProperty(sid2)) continue;
                            for (var j = 0; j < allData[sid2].length; j++) {
                                allData[sid2][j].is_legacy = allData[sid2][j]._orig_legacy;
                            }
                        }

                        var ov = getUserOverrides();
                        if (Object.keys(ov).length) applyOverridesToData(ov);
                        recalcSectorMeta();
                        renderSectorTabs();
                        renderSummary();
                        table.rows().invalidate('data').draw(false);
                    }
                } catch (authErr) {
                    console.warn('[CORRYU] Background init failed:', authErr);
                }
            }, 50);
        })
        .catch(function (err) {
            console.error('[CORRYU] 데이터 파싱 실패:', err);
        });
});
