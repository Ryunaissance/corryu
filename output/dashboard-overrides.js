/**
 * CORRYU Dashboard — 오버라이드 & 동기화 (dashboard-overrides.js)
 * ──────────────────────────────────────────────────────────
 * localStorage 레거시/섹터 오버라이드, YF API r_anchor 재계산,
 * FAB 액션 로직.
 *
 * 의존성: dashboard-state.js (전역 상태 & 유틸리티)
 */

// ── localStorage 레거시 오버라이드 ───────────────────────
var USER_OVERRIDES_KEY = 'corryu_user_overrides';

function getUserOverrides() {
    try { return JSON.parse(localStorage.getItem(USER_OVERRIDES_KEY) || '{}'); }
    catch (e) { return {}; }
}

function saveUserOverrides(ov) {
    localStorage.setItem(USER_OVERRIDES_KEY, JSON.stringify(ov));
    localStorage.setItem('corryu_overrides_ts', String(Date.now()));
}

function applyUserOverrides() {
    var ov = getUserOverrides();
    if (!Object.keys(ov).length) return;
    applyOverridesToData(ov);
}

// ── SMH 상관계수 오버레이 ────────────────────────────────
function applySmhCorr() {
    try {
        var smhData = JSON.parse(localStorage.getItem('corryu_smh_corr') || 'null');
        if (!smhData) return;
        for (var sid in allData) {
            if (!allData.hasOwnProperty(sid)) continue;
            for (var i = 0; i < allData[sid].length; i++) {
                var etf = allData[sid][i];
                if (etf.ticker in smhData) etf.smh_corr = smhData[etf.ticker];
            }
        }
    } catch (e) { }
}

// ── 오버라이드 데이터 적용 ───────────────────────────────
function applyOverridesToData(ov) {
    // ① 현재 모든 섹터에 있는 ETF 수집
    var etfMap = {};
    for (var sid in allData) {
        if (!allData.hasOwnProperty(sid)) continue;
        for (var i = 0; i < allData[sid].length; i++) {
            etfMap[allData[sid][i].ticker] = allData[sid][i];
        }
    }
    // ② 모든 섹터 배열 초기화 후 원래 섹터에 재배치 + 레거시 상태 원복
    for (var sid2 in allData) {
        if (!allData.hasOwnProperty(sid2)) continue;
        allData[sid2] = [];
    }
    for (var ticker in etfMap) {
        if (!etfMap.hasOwnProperty(ticker)) continue;
        var etf = etfMap[ticker];
        var origSid = etf._original_sector || etf._build_sector;
        if (!origSid || allData[origSid] === undefined) continue;
        if (!etf._user_override) {
            etf.is_legacy = etf._orig_legacy;
            etf.legacy_detail = etf._orig_legacy_detail ? etf._orig_legacy_detail.slice() : [];
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
    for (var ticker2 in ov) {
        if (!ov.hasOwnProperty(ticker2)) continue;
        var o = ov[ticker2];
        if (!('is_legacy' in o)) continue;
        var found = findETFAnywhere(ticker2);
        if (!found) continue;
        found.etf.is_legacy = o.is_legacy;
        found.etf._user_override = true;
        found.etf.legacy_detail = o.is_legacy ? ['사용자 직접 지정'] : [];
        found.etf.legacy_reasons = o.is_legacy ? ['user_override'] : [];
    }
    // ④ 섹터 이동 오버라이드 적용
    for (var ticker3 in ov) {
        if (!ov.hasOwnProperty(ticker3)) continue;
        var o2 = ov[ticker3];
        var buildSid = etfMap[ticker3] ? etfMap[ticker3]._build_sector : null;
        if (!o2.sector || o2.sector === buildSid) continue;
        var currentFound = findETFAnywhere(ticker3);
        if (!currentFound) continue;
        var etf2 = currentFound.etf, oldSid = currentFound.sid, idx = currentFound.idx;
        var newSid = o2.sector;
        if (allData[newSid] === undefined) continue;
        allData[oldSid].splice(idx, 1);
        etf2._user_sector = newSid;
        etf2._original_sector = oldSid;
        allData[newSid].push(etf2);
    }
    // ⑤ r_anchor 오버라이드 적용
    for (var ticker4 in ov) {
        if (!ov.hasOwnProperty(ticker4)) continue;
        var o3 = ov[ticker4];
        if (o3.r_anchor === undefined) continue;
        var found2 = findETFAnywhere(ticker4);
        if (!found2) continue;
        found2.etf.r_anchor = o3.r_anchor;
        found2.etf._user_override_r_anchor = true;
    }
}

// ── FAB 액션: 레거시 처리/해제 ──────────────────────────
function applyLegacyAction(setLegacy) {
    if (!_isAdmin || selectedTickers.size === 0) return;
    var ov = getUserOverrides();
    selectedTickers.forEach(function (ticker) {
        if (!ov[ticker]) ov[ticker] = {};
        ov[ticker].is_legacy = setLegacy;
        var found = findETFAnywhere(ticker);
        if (found) {
            found.etf.is_legacy = setLegacy;
            found.etf._user_override = true;
            found.etf.legacy_detail = setLegacy ? ['사용자 직접 지정'] : [];
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

// ── FAB 액션: 카테고리 이동 모달 ─────────────────────────
function buildSectorModal() {
    var curSectors = new Set();
    selectedTickers.forEach(function (tk) {
        var found = findETFAnywhere(tk);
        if (found) curSectors.add(found.sid);
    });
    $('#modal-sel-info').text(selectedTickers.size + '개 종목 → 이동할 카테고리를 선택하세요');
    var ordered = Object.entries(acDefs).sort(function (a, b) { return a[1].order - b[1].order; });
    var html = '';
    for (var i = 0; i < ordered.length; i++) {
        var ac = ordered[i][0], acDef = ordered[i][1];
        var sids = (acSectors[ac] || []).sort();
        if (!sids.length) continue;
        html += '<div class="smg">' + acDef.icon + ' ' + acDef.name + '</div>';
        html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-bottom:4px">';
        for (var j = 0; j < sids.length; j++) {
            var sid = sids[j];
            var sd = sectorDefs[sid];
            if (!sd) continue;
            var isCur = curSectors.size === 1 && curSectors.has(sid);
            html += '<button class="smb' + (isCur ? ' cur' : '') + '" data-sid="' + sid + '">';
            html += '<span style="font-size:1rem">' + (sd.icon || '') + '</span>';
            html += '<div><div style="font-weight:600;font-size:0.8rem">' + sd.name + '</div>';
            html += '<div style="font-size:0.68rem;color:#475569">' + (sd.name_en || '') + '</div></div>';
            html += '</button>';
        }
        html += '</div>';
    }
    $('#sector-modal-body').html(html);
}

function applySectorMove(newSectorId) {
    if (!newSectorId || selectedTickers.size === 0) return;
    var tickersToRecompute = [];
    var ov = getUserOverrides();
    selectedTickers.forEach(function (ticker) {
        var found = findETFAnywhere(ticker);
        if (!found) return;
        var etf = found.etf, oldSid = found.sid;
        if (!ov[ticker]) ov[ticker] = {};
        if (oldSid === newSectorId) {
            delete ov[ticker].sector;
            delete ov[ticker].r_anchor;
            delete etf._user_sector;
            delete etf._original_sector;
            if (!Object.keys(ov[ticker]).length) delete ov[ticker];
            return;
        }
        tickersToRecompute.push(ticker);
        allData[oldSid] = allData[oldSid].filter(function (e) { return e.ticker !== ticker; });
        etf._user_sector = newSectorId;
        etf._original_sector = etf._build_sector;
        if (!allData[newSectorId]) allData[newSectorId] = [];
        allData[newSectorId].push(etf);
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

// ── 브라우저-사이드 r_anchor 재계산 유틸 ─────────────────
function _sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

function _pearson(xs, ys) {
    var n = xs.length;
    if (n < 2) return NaN;
    var mx = 0, my = 0;
    for (var i = 0; i < n; i++) { mx += xs[i]; my += ys[i]; }
    mx /= n; my /= n;
    var num = 0, dx2 = 0, dy2 = 0;
    for (var i2 = 0; i2 < n; i2++) {
        var dx = xs[i2] - mx, dy = ys[i2] - my;
        num += dx * dy; dx2 += dx * dx; dy2 += dy * dy;
    }
    return (dx2 && dy2) ? num / Math.sqrt(dx2 * dy2) : NaN;
}

function _pairwiseReturns(pA, pB) {
    var dates = Object.keys(pA).filter(function (d) { return d in pB; }).sort();
    var rA = [], rB = [];
    for (var i = 1; i < dates.length; i++) {
        var a0 = pA[dates[i - 1]], a1 = pA[dates[i]];
        var b0 = pB[dates[i - 1]], b1 = pB[dates[i]];
        if (a0 && a1 && b0 && b1) {
            rA.push((a1 - a0) / a0);
            rB.push((b1 - b0) / b0);
        }
    }
    return [rA, rB];
}

function _calcCorr(pA, pB) {
    var pair = _pairwiseReturns(pA, pB);
    if (pair[0].length < 24) return null;
    var c = _pearson(pair[0], pair[1]);
    return isFinite(c) ? Math.round(c * 10000) / 10000 : null;
}

function _makeYfUrls(ticker) {
    var tk = encodeURIComponent(ticker);
    var yf1 = 'https://query1.finance.yahoo.com/v8/finance/chart/' + tk + '?range=max&interval=1mo&includeAdjustedClose=true';
    return [
        '/api/yf?ticker=' + tk + '&range=max&interval=1mo',
        yf1,
        'https://query2.finance.yahoo.com/v8/finance/chart/' + tk + '?range=max&interval=1mo&includeAdjustedClose=true',
        'https://corsproxy.io/?' + encodeURIComponent(yf1),
    ];
}

function _parseYfMonthly(data) {
    var result = data && data.chart && data.chart.result && data.chart.result[0];
    if (!result) return null;
    var ts = result.timestamp;
    var adj = (result.indicators && result.indicators.adjclose && result.indicators.adjclose[0] && result.indicators.adjclose[0].adjclose)
        || (result.indicators && result.indicators.quote && result.indicators.quote[0] && result.indicators.quote[0].close);
    if (!ts || !adj) return null;
    var prices = {};
    for (var i = 0; i < ts.length; i++) {
        if (adj[i] != null) {
            var d = new Date(ts[i] * 1000);
            prices[d.getUTCFullYear() + '-' + String(d.getUTCMonth() + 1).padStart(2, '0')] = adj[i];
        }
    }
    return Object.keys(prices).length >= 3 ? prices : null;
}

function _fetchYfMonthly(ticker) {
    var urls = _makeYfUrls(ticker);
    var idx = 0;
    function tryNext() {
        if (idx >= urls.length) return Promise.resolve(null);
        var url = urls[idx];
        var attempt = 0;
        function tryAttempt() {
            if (attempt >= 2) { idx++; return tryNext(); }
            return fetch(url).then(function (r) {
                if (r.status === 429) {
                    attempt++;
                    return _sleep(3000 * attempt).then(tryAttempt);
                }
                if (!r.ok) { idx++; return tryNext(); }
                return r.json().then(function (json) {
                    var prices = _parseYfMonthly(json);
                    if (prices) return prices;
                    idx++; return tryNext();
                });
            }).catch(function () {
                return _sleep(500).then(function () { attempt++; return tryAttempt(); });
            });
        }
        return tryAttempt();
    }
    return tryNext();
}

function recomputeRanchorsAsync(tickers, newSectorId) {
    var anchor = (sectorDefs[newSectorId] || {}).anchor;
    if (!anchor || anchor === '—') return Promise.resolve();
    var tickerList = Array.isArray(tickers) ? tickers : Array.from(tickers);
    if (!tickerList.length) return Promise.resolve();
    showToast('r_anchor 재계산 중… 앵커: ' + anchor + ' / ' + tickerList.length + '종목', 60000);
    return _fetchYfMonthly(anchor).then(function (anchorPrices) {
        if (!anchorPrices) {
            showToast('앵커(' + anchor + ') 가격 조회 실패', 4000);
            return;
        }
        var ok = 0;
        var ov = getUserOverrides();
        var idx = 0;
        function processNext() {
            if (idx >= tickerList.length) {
                saveUserOverrides(ov);
                if (ok > 0 && typeof table !== 'undefined') table.rows().invalidate('data').draw(false);
                showToast('r_anchor 재계산 완료 (' + ok + '/' + tickerList.length + '종목)', 4000);
                return Promise.resolve();
            }
            var ticker = tickerList[idx];
            idx++;
            var found = findETFAnywhere(ticker);
            if (!found) return processNext();
            return _fetchYfMonthly(ticker).then(function (prices) {
                if (!prices) return processNext();
                var corr = _calcCorr(anchorPrices, prices);
                if (corr === null) return processNext();
                found.etf.r_anchor = corr;
                if (!ov[ticker]) ov[ticker] = {};
                ov[ticker].r_anchor = corr;
                ok++;
                return _sleep(150).then(processNext);
            });
        }
        return processNext();
    });
}

// ── FAB 이벤트 바인딩 (initDashboard에서 호출) ───────────
function initOverrideEvents() {
    $('#fab-btn-legacy').on('click', function () { applyLegacyAction(true); });
    $('#fab-btn-unlegacy').on('click', function () { applyLegacyAction(false); });
    $('#fab-btn-move').on('click', function () {
        if (selectedTickers.size === 0) return;
        buildSectorModal();
        $('#sector-modal').addClass('show');
    });
    $('#sector-modal-close').on('click', function () { $('#sector-modal').removeClass('show'); });
    $('#sector-modal').on('click', function (e) { if (e.target === this) $(this).removeClass('show'); });
    $(document).on('click', '#sector-modal-body .smb', function () {
        applySectorMove($(this).data('sid'));
    });
    $('#fab-btn-clear').on('click', function () {
        selectedTickers.clear();
        $('input.row-cb').prop('checked', false);
        table.rows().every(function () { $(this.node()).removeClass('row-selected'); });
        updateFAB();
    });
}
