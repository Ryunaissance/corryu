/**
 * CORRYU Navigation & Auth Module (nav.js)
 * ──────────────────────────────────────────
 * 1. Nav HTML injection  — injectNav()
 * 2. Auth rendering      — renderAuth()
 * 3. Logout flow         — doLogout()
 * 4. Auth state listener — initAuthListener()
 * 5. Mobile hamburger    — initHamburger()
 * 6. Active link highlight — highlightNav()
 *
 * 각 서브페이지 사용법:
 *   <nav id="nav-root" data-nav-title="페이지명"></nav>
 *   <div id="nav-mob-drawer"></div>
 *   <div id="nav-mob-overlay"></div>
 *   <script src="/nav.js"></script>
 */
(function () {
  'use strict';

  // ── 0. SVG & Link 상수 ────────────────────────────────
  var S = {
    back:   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 12H5M12 5l-7 7 7 7"/></svg>',
    sun:    '<svg class="theme-icon-sun" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>',
    moon:   '<svg class="theme-icon-moon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
    burger: '<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="17" y2="6"/><line x1="3" y1="10" x2="17" y2="10"/><line x1="3" y1="14" x2="17" y2="14"/></svg>',
    screener:    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>',
    backtest:    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    correlation: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="8" cy="8" r="2"/><circle cx="16" cy="8" r="2"/><circle cx="12" cy="16" r="2"/><line x1="10" y1="8" x2="14" y2="8"/><line x1="9" y1="10" x2="11" y2="14"/><line x1="15" y1="10" x2="13" y2="14"/></svg>',
    compare:     '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    portfolio:   '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/></svg>',
    graph:       '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="5" cy="12" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><line x1="7" y1="11.5" x2="17" y2="6.5"/><line x1="7" y1="12.5" x2="17" y2="17.5"/></svg>',
    dashboard:   '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>'
  };

  // 데스크탑 nav + 모바일 drawer 링크 목록 (한 곳에서 관리)
  var allLinks = [
    { href: '/index',       icon: 'dashboard',   label: '대시보드',   i18n: 'nav.dashboard' },
    { href: '/screener',    icon: 'screener',    label: '스크리너',   i18n: 'nav.screener' },
    { href: '/backtest',    icon: 'backtest',    label: '백테스트',   i18n: 'nav.backtest' },
    { href: '/correlation', icon: 'correlation', label: '상관관계',   i18n: 'nav.correlation' },
    { href: '/compare',     icon: 'compare',     label: '비교',       i18n: 'nav.compare' },
    { href: '/portfolio',   icon: 'portfolio',   label: '포트폴리오', i18n: 'nav.portfolio' },
    { href: '/graph',       icon: 'graph',       label: '그래프',     i18n: 'nav.graph' }
  ];

  // ── 1. Nav HTML Injection ─────────────────────────────
  function injectNav() {
    var root = document.getElementById('nav-root');
    if (!root) return; // index.html 등 자체 nav 보유 페이지는 skip

    var title = root.dataset.navTitle || '';
    var crumb = title
      ? '<span style="font-size:.82rem;color:var(--t3,#7d90a4)">/ ' + title + '</span>'
      : '';

    // 데스크탑용: 대시보드/그래프 제외한 중간 링크들
    var desktopLinks = allLinks.filter(function(l) {
      return l.href !== '/index' && l.href !== '/graph';
    }).map(function (l) {
      return '<a href="' + l.href + '" class="nav-link" data-i18n="' + l.i18n + '">' + S[l.icon] + l.label + '</a>';
    }).join('');

    root.innerHTML =
      '<div class="nav-i">' +
        '<a href="/index" class="nav-back">' + S.back + '대시보드</a>' +
        '<span style="color:#1e293b">/</span>' +
        '<a href="/landing" style="font-size:.95rem;font-weight:900;text-decoration:none"><span class="tg">CORRYU</span></a>' +
        crumb +
        '<div class="nav-desktop-links" style="margin-left:auto;display:flex;align-items:center;gap:14px">' +
          desktopLinks +
        '</div>' +
        '<div id="nav-auth"></div>' +
        '<button class="theme-toggle" onclick="Theme.toggle()" aria-label="라이트 모드로 전환" title="라이트 모드">' + S.sun + S.moon + '</button>' +
        '<button id="nav-mob-btn" class="nav-mob-btn" aria-label="메뉴">' + S.burger + '</button>' +
      '</div>';
  }

  // ── 1b. Mobile Drawer Link Injection (모든 페이지 공통) ──
  // allLinks 배열이 단일 진실의 원천 — index.html 포함 모든 페이지에서 동적 생성
  function injectMobileDrawer() {
    var drawer = document.getElementById('nav-mob-drawer');
    if (!drawer) return;
    var mobileLinks = allLinks.map(function(l) {
      // 모바일은 아이콘 크기를 15로 강제 조정
      var iconHtml = S[l.icon].replace(/width="1[35]"/, 'width="15"').replace(/height="1[35]"/, 'height="15"');
      return '<a href="' + l.href + '" class="mob-link" data-i18n="' + l.i18n + '">' + iconHtml + l.label + '</a>';
    }).join('');
    drawer.innerHTML =
      mobileLinks +
      '<div class="mob-drawer-divider"></div>' +
      '<div class="mob-drawer-bottom">' +
        '<button class="mob-lang-btn" onclick="I18n.setLocale(I18n.locale()===\'ko\'?\'en\':\'ko\')">EN / 한</button>' +
        '<div id="nav-mob-auth"></div>' +
      '</div>';
  }

  // ── 2. Mobile Hamburger Menu ───────────────────────────
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

  // ── 3. Active Nav-Link Highlight ───────────────────────
  function highlightNav() {
    var path = window.location.pathname.replace(/\.html$/, '').replace(/\/$/, '') || '/index';
    document.querySelectorAll('.nav-link, .mob-link').forEach(function (a) {
      var href = (a.getAttribute('href') || '').replace(/\.html$/, '').replace(/\/$/, '') || '/index';
      if (href === path) a.classList.add('active');
      else a.classList.remove('active');
    });
  }

  // ── 4. Auth Rendering ─────────────────────────────────
  var _renderedNick = null;

  async function renderAuth() {
    var authDesktop = document.getElementById('nav-auth');
    var authMobile  = document.getElementById('nav-mob-auth');
    var I18n = window.I18n || { t: function (k) { return k; } };

    function renderLoggedOut() {
      var loginHTML = '<a href="/login" id="nav-login-btn"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path><polyline points="10 17 15 12 10 7"></polyline><line x1="15" y1="12" x2="3" y2="12"></line></svg><span data-i18n="nav.login">' + (I18n.t('nav.login') || '로그인') + '</span></a>';
      if (authDesktop) authDesktop.innerHTML = loginHTML;
      if (authMobile)  authMobile.innerHTML  = '<a href="/login" id="nav-mob-login-btn" style="display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:8px;background:rgba(59,130,246,0.12);color:#60a5fa;border:1px solid rgba(59,130,246,0.3);font-size:0.82rem;font-weight:700;text-decoration:none;transition:all 0.15s"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path><polyline points="10 17 15 12 10 7"></polyline><line x1="15" y1="12" x2="3" y2="12"></line></svg><span data-i18n="nav.login">' + (I18n.t('nav.login') || '로그인') + '</span></a>';
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
      if (mobOutBtn) mobOutBtn.onclick = function (e) { e.preventDefault(); doLogout(); };
    }
  }

  // ── 5. Logout ─────────────────────────────────────────
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

  // ── 6. Auth State Change Listener ─────────────────────
  function initAuthListener() {
    // CorryuAuth 없어도 로그인 버튼은 항상 표시
    if (typeof CorryuAuth === 'undefined' || !CorryuAuth.isConfigured) {
      renderAuth();
      return;
    }

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

  // ── 7. Init ────────────────────────────────────────────
  function init() {
    injectNav();           // HTML 주입 (서브페이지 전용)
    injectMobileDrawer();  // 모바일 드로어 링크 주입 (모든 페이지)
    initHamburger();       // 주입 후 DOM 참조 가능
    highlightNav();
    initAuthListener();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Global API
  window.CorryuNav = { init: init, renderAuth: renderAuth, doLogout: doLogout, highlightNav: highlightNav };
  window._navLogout = doLogout;
})();
