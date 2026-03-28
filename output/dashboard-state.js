/**
 * CORRYU Dashboard — 전역 상태 & 유틸리티 (dashboard-state.js)
 * ──────────────────────────────────────────────────────────
 * 모든 dashboard-*.js 모듈이 공유하는 상태 변수와 유틸리티 함수.
 * 반드시 다른 dashboard 모듈보다 먼저 로드해야 합니다.
 *
 * 의존성: window.CORRYU_CONFIG (render_html.py에서 주입)
 */

// ── 글로벌 데이터 (etf_data.json에서 fetch) ──────────────
var sectorMeta = {};
var allData = {};

// ── config 참조 ──────────────────────────────────────────
var acSectors = window.CORRYU_CONFIG.ac_sectors;
var acDefs = window.CORRYU_CONFIG.ac_defs;
var sectorDefs = window.CORRYU_CONFIG.sector_defs;
var superSectorDefs = window.CORRYU_CONFIG.super_sector_defs;
var myPortfolio = window.CORRYU_CONFIG.my_portfolio;

// 섹터ID → 슈퍼섹터ID 역방향 맵
var sectorToSuperSector = {};
(function () {
    for (var ssId in superSectorDefs) {
        if (!superSectorDefs.hasOwnProperty(ssId)) continue;
        var ss = superSectorDefs[ssId];
        for (var i = 0; i < ss.sub_sectors.length; i++) {
            sectorToSuperSector[ss.sub_sectors[i]] = ssId;
        }
    }
})();

// ── UI 상태 ──────────────────────────────────────────────
var state = {
    activeAC: 'ALL',
    activeSector: 'ALL',
    expandedSuperSector: null,
    hideLegacy: false,
    hideShort: false,
    minAum: 0,
    minSortino: -999
};

// ── 체크박스 선택 상태 ────────────────────────────────────
var selectedTickers = new Set();

// ── DataTable 참조 (initDashboard에서 할당) ──────────────
var table;

// ── 좋아요 상태 ──────────────────────────────────────────
var likedTickers = new Set();
var _currentUserId = null;

// ── Admin 권한 ───────────────────────────────────────────
var _adminEmails = new Set(window.CORRYU_CONFIG.admin_emails);
var _isAdmin = false;

function detectAdmin() {
    if (typeof CorryuAuth === 'undefined' || !CorryuAuth.isConfigured) return Promise.resolve(false);
    return CorryuAuth.getUser().then(function (user) {
        if (!user) return false;
        if (user.app_metadata && user.app_metadata.role === 'admin') return true;
        if (user.email && _adminEmails.has(user.email)) return true;
        return false;
    }).catch(function () { return false; });
}

function stripLegacyForNonAdmin() {
    for (var sid in allData) {
        if (!allData.hasOwnProperty(sid)) continue;
        for (var i = 0; i < allData[sid].length; i++) {
            var etf = allData[sid][i];
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

// ── sectorMeta 재계산 ────────────────────────────────────
function recalcSectorMeta() {
    for (var sid in allData) {
        if (!allData.hasOwnProperty(sid)) continue;
        var list = allData[sid];
        var total = list.length;
        var active = list.filter(function (e) { return !e.is_legacy; }).length;
        var legacy = total - active;
        var sumCAGR = list.reduce(function (s, e) { return s + (e.cagr || 0); }, 0);
        var sumVol = list.reduce(function (s, e) { return s + (e.vol || 0); }, 0);
        var sumSortino = list.reduce(function (s, e) { return s + (e.sortino || 0); }, 0);

        sectorMeta[sid] = {
            count: total,
            active: active,
            legacy: legacy,
            avg_cagr: total > 0 ? sumCAGR / total : 0,
            avg_vol: total > 0 ? sumVol / total : 0,
            avg_sortino: total > 0 ? sumSortino / total : 0
        };
    }
    var totalETFs = 0, totalActive = 0, totalLegacy = 0;
    for (var sid2 in sectorMeta) {
        totalETFs += sectorMeta[sid2].count;
        totalActive += sectorMeta[sid2].active;
        totalLegacy += sectorMeta[sid2].legacy;
    }
    $('#hdr-total').text(totalETFs.toLocaleString());
    $('#hdr-active').text(totalActive.toLocaleString());
    $('#hdr-legacy').text(totalLegacy.toLocaleString());
}

// ── 유틸리티 함수 ────────────────────────────────────────

function applyHearts() {
    document.querySelectorAll('.star-btn[data-like]').forEach(function (btn) {
        var t = btn.dataset.like;
        var liked = likedTickers.has(t);
        btn.classList.toggle('starred', liked);
        btn.textContent = liked ? '♥' : '♡';
    });
}

function formatMCap(val) {
    if (!val) return '-';
    var m = val / 1e6;
    if (m >= 1000) return '$' + (m / 1000).toFixed(1) + 'B';
    return '$' + Math.round(m) + 'M';
}

function getSuperSectorMeta(ssId) {
    var ss = superSectorDefs[ssId];
    if (!ss) return {};
    var metas = ss.sub_sectors.map(function (sid) { return sectorMeta[sid] || {}; });
    return {
        count: metas.reduce(function (s, m) { return s + (m.count || 0); }, 0),
        active: metas.reduce(function (s, m) { return s + (m.active || 0); }, 0)
    };
}

function findETFAnywhere(ticker) {
    for (var sid in allData) {
        if (!allData.hasOwnProperty(sid)) continue;
        var idx = allData[sid].findIndex(function (e) { return e.ticker === ticker; });
        if (idx !== -1) return { etf: allData[sid][idx], sid: sid, idx: idx };
    }
    return null;
}

// ── 토스트 알림 (전역) ────────────────────────────────────
var _toastTimer = null;
function showToast(msg, durationMs) {
    var el = document.getElementById('r-toast');
    if (!el) {
        el = document.createElement('div');
        el.id = 'r-toast';
        el.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#1e293b;color:#e2e8f0;padding:9px 18px;border-radius:10px;font-size:0.85rem;border:1px solid rgba(255,255,255,0.12);box-shadow:0 4px 20px rgba(0,0,0,0.5);z-index:9999;pointer-events:none;transition:opacity 0.3s;opacity:0;white-space:nowrap;';
        document.body.appendChild(el);
    }
    if (_toastTimer) clearTimeout(_toastTimer);
    el.textContent = msg;
    el.style.opacity = '1';
    _toastTimer = setTimeout(function () { el.style.opacity = '0'; }, durationMs || 3000);
}
