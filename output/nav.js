/**
 * CORRYU Navigation & Auth Module (nav.js)
 * ──────────────────────────────────────────
 * Centralized handler for:
 *   1. Navbar auth rendering (nickname / logout button)
 *   2. Logout flow (Supabase signOut + session cleanup)
 *   3. Auth state change listener (SIGNED_IN / SIGNED_OUT)
 *   4. Mobile hamburger menu (drawer open/close)
 *   5. Active nav-link highlighting
 *
 * Usage: <script src="/nav.js"></script> (after supabase-client.js & i18n.js)
 */
(function () {
  'use strict';

  // ── 1. Mobile Hamburger Menu ───────────────────────────
  function initHamburger() {
    var btn     = document.getElementById('nav-mob-btn');
    var drawer  = document.getElementById('nav-mob-drawer');
    var overlay = document.getElementById('nav-mob-overlay');
    if (!btn || !drawer) return;

    function openMenu() {
      drawer.classList.add('open');
      if (overlay) overlay.classList.add('open');
      document.body.classList.add('mob-menu-open');
      btn.setAttribute('aria-expanded', 'true');
    }
    function closeMenu() {
      drawer.classList.remove('open');
      if (overlay) overlay.classList.remove('open');
      document.body.classList.remove('mob-menu-open');
      btn.setAttribute('aria-expanded', 'false');
    }

    btn.addEventListener('click', function () {
      drawer.classList.contains('open') ? closeMenu() : openMenu();
    });
    if (overlay) overlay.addEventListener('click', closeMenu);
    drawer.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', closeMenu);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeMenu();
    });
  }

  // ── 2. Active Nav-Link Highlight ───────────────────────
  function highlightNav() {
    var path = window.location.pathname.replace(/\.html$/, '').replace(/\/$/, '') || '/index';
    document.querySelectorAll('.nav-link, .mob-link').forEach(function (a) {
      var href = (a.getAttribute('href') || '').replace(/\.html$/, '').replace(/\/$/, '') || '/index';
      if (href === path) a.classList.add('active');
      else a.classList.remove('active');
    });
  }

  // ── 3. Auth Rendering ─────────────────────────────────
  var _renderedNick = null;

  async function renderAuth() {
    var authDesktop = document.getElementById('nav-auth');
    var authMobile = document.getElementById('nav-mob-auth');
    var I18n = window.I18n || { t: function (k) { return k; } };

    function renderLoggedOut() {
      if (authDesktop) {
        authDesktop.innerHTML = '<a href="/login" id="nav-login-btn"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path><polyline points="10 17 15 12 10 7"></polyline><line x1="15" y1="12" x2="3" y2="12"></line></svg><span data-i18n="nav.login">' + (I18n.t('nav.login') || '로그인') + '</span></a>';
      }
      if (authMobile) {
        authMobile.innerHTML = '<a href="/login" id="nav-mob-login-btn" style="display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:8px;background:rgba(59,130,246,0.12);color:#60a5fa;border:1px solid rgba(59,130,246,0.3);font-size:0.82rem;font-weight:700;text-decoration:none;transition:all 0.15s"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path><polyline points="10 17 15 12 10 7"></polyline><line x1="15" y1="12" x2="3" y2="12"></line></svg><span data-i18n="nav.login">' + (I18n.t('nav.login') || '로그인') + '</span></a>';
      }
    }

    if (typeof CorryuAuth === 'undefined' || !CorryuAuth.isConfigured) {
        return renderLoggedOut();
    }

    var user;
    try { user = await CorryuAuth.getUser(); } catch (e) { return renderLoggedOut(); }
    if (!user) return renderLoggedOut();

    var profile;
    try { profile = await CorryuAuth.getProfile(user.id); } catch (e) {}
    var nick = (profile && profile.nickname) || (user.email ? user.email.split('@')[0] : 'User');
    
    if (_renderedNick === nick) return;
    _renderedNick = nick;

    if (authDesktop) {
      authDesktop.innerHTML =
        '<a id="nav-user-nick" href="/profile.html" title="' + nick + '">' + nick + '</a>' +
        '<button id="nav-logout-btn" data-i18n="nav.logout">' + (I18n.t('nav.logout') || '로그아웃') + '</button>';
    }

    if (authMobile) {
      authMobile.innerHTML =
        '<a href="/profile.html" class="mob-link" style="color:#93c5fd;font-weight:700;padding:6px 12px;display:flex;align-items:center;gap:6px"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>' + nick + '</a>' +
        '<a href="#" id="nav-mob-logout-btn" class="mob-link mob-logout-link" style="color:#f87171;cursor:pointer;display:flex;align-items:center;gap:6px;padding:6px 12px"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg><span data-i18n="nav.logout">' + (I18n.t('nav.logout') || '로그아웃') + '</span></a>';
      
      var mobOutBtn = document.getElementById('nav-mob-logout-btn');
      if (mobOutBtn) mobOutBtn.onclick = function(e) { e.preventDefault(); doLogout(); };
    }
  }

  // ── 4. Logout ─────────────────────────────────────────
  async function doLogout() {
    var btn = document.getElementById('nav-logout-btn');
    if (btn) { btn.disabled = true; btn.textContent = '로그아웃 중…'; }
    var mobBtn = document.getElementById('nav-mob-logout-btn');
    if (mobBtn) { mobBtn.style.pointerEvents = 'none'; mobBtn.style.opacity = '0.5'; }
    try {
      await Promise.race([
        CorryuAuth.signOut(),
        new Promise(function (r) { setTimeout(r, 2000); })
      ]);
    } catch (e) { console.warn('[CORRYU] logout error:', e); }
    window.location.reload();
  }

  // ── 5. Auth State Change Listener ─────────────────────
  function initAuthListener() {
    if (typeof CorryuAuth === 'undefined' || !CorryuAuth.isConfigured) return;

    // Delegated logout click handler on nav-auth
    var authEl = document.getElementById('nav-auth');
    if (authEl) {
      authEl.addEventListener('click', function (e) {
        if (e.target.closest('#nav-logout-btn')) {
          e.preventDefault();
          e.stopPropagation();
          doLogout();
        }
      });
    }

    CorryuAuth.onAuthChange(function (event, session) {
      if (event === 'SIGNED_OUT' && !session) {
        _renderedNick = null;
        window.location.reload();
      } else {
        renderAuth();
      }
    });

    renderAuth();
  }

  // ── 6. Init (auto-run on DOMContentLoaded) ────────────
  function init() {
    initHamburger();
    highlightNav();
    initAuthListener();
  }

  // Run immediately if DOM is already ready, otherwise wait
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Global API
  window.CorryuNav = {
    init: init,
    renderAuth: renderAuth,
    doLogout: doLogout,
    highlightNav: highlightNav
  };
  window._navLogout = doLogout;
})();
