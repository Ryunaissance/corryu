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
    var authEl = document.getElementById('nav-auth');
    if (!authEl) return;
    
    function reveal() { document.body.classList.add('auth-loaded'); }

    if (typeof CorryuAuth === 'undefined' || !CorryuAuth.isConfigured) {
        reveal();
        return;
    }

    var user;
    try { user = await CorryuAuth.getUser(); } catch (e) {
        reveal();
        return; 
    }
    if (!user) {
        reveal();
        return;
    }

    var profile;
    try { profile = await CorryuAuth.getProfile(user.id); } catch (e) {}
    var nick = (profile && profile.nickname) || (user.email ? user.email.split('@')[0] : 'User');
    
    reveal();

    if (_renderedNick === nick) return;
    _renderedNick = nick;

    var I18n = window.I18n || { t: function (k) { return k; } };
    authEl.innerHTML =
      '<a id="nav-user-nick" href="/profile.html" title="' + nick + '">' + nick + '</a>' +
      '<button id="nav-logout-btn" data-i18n="nav.logout">' + I18n.t('nav.logout') + '</button>';
  }

  // ── 4. Logout ─────────────────────────────────────────
  async function doLogout() {
    var btn = document.getElementById('nav-logout-btn');
    if (btn) { btn.disabled = true; btn.textContent = '로그아웃 중…'; }
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

    CorryuAuth.onAuthChange(function (event) {
      var mobLoginBtn = document.getElementById('nav-mob-login-btn');
      if (event === 'SIGNED_IN' && mobLoginBtn) mobLoginBtn.style.display = 'none';
      if (event === 'SIGNED_OUT') {
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
