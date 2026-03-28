/**
 * CORRYU Dashboard — 좋아요 & 트렌딩 (dashboard-likes.js)
 * ──────────────────────────────────────────────────────────
 * 좋아요 버튼, Auth 기반 좋아요 상태 관리, 인기 종목 랭킹.
 * dashboard.js 이후에 로드되어야 합니다.
 *
 * 의존성: dashboard-state.js (전역 상태)
 */

// ═══════════════════════════════════════════════════════════
// ❤️ 인기 종목 랭킹 (ticker_likes) — index.html only
// ═══════════════════════════════════════════════════════════
(async function initTrending() {
  if (typeof CorryuAuth === 'undefined' || !CorryuAuth.isConfigured) return;

  var section = document.getElementById('trending-section');
  if (!section) return;
  section.style.display = 'block';

  var TOP_N = 5;

  function rankItemHTML(rank, ticker, count, barPct, period) {
    var medals = ['🥇','🥈','🥉'];
    var medal  = medals[rank - 1] || '<span style="font-size:.75rem;color:#475569;font-weight:800">' + rank + '</span>';
    var barColor = period === 'weekly' ? 'rgba(251,191,36,0.6)' : 'rgba(168,85,247,0.6)';
    return '<a href="/etf-detail?ticker=' + encodeURIComponent(ticker) + '"' +
        ' style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:8px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04);text-decoration:none;transition:background .15s"' +
        ' onmouseover="this.style.background=\'rgba(255,255,255,0.05)\'" onmouseout="this.style.background=\'rgba(255,255,255,0.02)\'">' +
      '<span style="font-size:.9rem;flex-shrink:0;min-width:22px;text-align:center">' + medal + '</span>' +
      '<span style="font-weight:800;font-size:.84rem;color:#e2e8f0;min-width:52px">' + ticker + '</span>' +
      '<div style="flex:1;height:4px;background:rgba(255,255,255,0.05);border-radius:2px;overflow:hidden">' +
        '<div style="height:100%;border-radius:2px;background:' + barColor + ';width:' + barPct + '%"></div>' +
      '</div>' +
      '<span style="font-size:.75rem;font-weight:700;color:#64748b;flex-shrink:0">❤️ ' + count + '</span>' +
    '</a>';
  }

  function emptyHTML() {
    return '<div data-i18n="index.trending.empty" style="color:#334155;font-size:.78rem;text-align:center;padding:16px 0">아직 좋아요 데이터가 없습니다</div>';
  }

  async function loadWeekly() {
    var el = document.getElementById('trending-weekly');
    var res = await _sb.from('ticker_likes_weekly')
      .select('ticker,weekly_likes')
      .order('weekly_likes', { ascending: false })
      .limit(TOP_N);
    if (res.error || !res.data || res.data.length === 0) { el.innerHTML = emptyHTML(); return; }
    var maxLikes = res.data[0].weekly_likes;
    el.innerHTML = res.data.map(function (row, i) {
      var pct = maxLikes > 0 ? Math.round((row.weekly_likes / maxLikes) * 100) : 0;
      return rankItemHTML(i + 1, row.ticker, row.weekly_likes, pct, 'weekly');
    }).join('');
  }

  async function loadMonthly() {
    var el = document.getElementById('trending-monthly');
    var res = await _sb.from('ticker_likes_monthly')
      .select('ticker,monthly_likes')
      .order('monthly_likes', { ascending: false })
      .limit(TOP_N);
    if (res.error || !res.data || res.data.length === 0) { el.innerHTML = emptyHTML(); return; }
    var maxLikes = res.data[0].monthly_likes;
    el.innerHTML = res.data.map(function (row, i) {
      var pct = maxLikes > 0 ? Math.round((row.monthly_likes / maxLikes) * 100) : 0;
      return rankItemHTML(i + 1, row.ticker, row.monthly_likes, pct, 'monthly');
    }).join('');
  }

  await Promise.all([loadWeekly(), loadMonthly()]);
  setInterval(function () { loadWeekly(); loadMonthly(); }, 30 * 60 * 1000);
})();

// ═══════════════════════════════════════════════════════════
// ❤️ Auth 기반 좋아요 상태 관리
// ═══════════════════════════════════════════════════════════
(function initLikes() {
    if (typeof CorryuAuth === 'undefined' || !CorryuAuth.isConfigured) return;

    CorryuAuth.onAuthChange(async function (event, session) {
        if (session && session.user) {
            _currentUserId = session.user.id;
            var res = await _sb.from('ticker_likes').select('ticker').eq('user_id', _currentUserId);
            likedTickers = new Set();
            if (res.data) res.data.forEach(function (r) { likedTickers.add(r.ticker); });
        } else {
            _currentUserId = null;
            likedTickers = new Set();
        }
        applyHearts();
    });
})();

// ═══════════════════════════════════════════════════════════
// ❤️ 좋아요 버튼 클릭 핸들러
// ═══════════════════════════════════════════════════════════
$(document).on('click', '.star-btn[data-like]', async function (e) {
    e.stopPropagation();
    var ticker = this.dataset.like;
    if (!_currentUserId) {
        showToast('로그인이 필요한 기능이에요', 2500);
        setTimeout(function () { window.location.href = '/login'; }, 1200);
        return;
    }
    var isLiked = likedTickers.has(ticker);
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
