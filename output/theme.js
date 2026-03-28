/**
 * CORRYU Theme Manager
 * 다크/라이트 모드 전환 · localStorage 저장 · 시스템 설정 연동
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'corryu-theme';
  var root = document.documentElement;

  /** 현재 적용해야 할 테마 반환 ('dark' | 'light') */
  function getTheme() {
    var saved = null;
    try { saved = localStorage.getItem(STORAGE_KEY); } catch (_) {}
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  /** <html>에 data-theme 적용 + 토글 버튼 아이콘 갱신 */
  function applyTheme(theme) {
    if (theme === 'light') {
      root.setAttribute('data-theme', 'light');
    } else {
      root.removeAttribute('data-theme');
    }
    // 모든 토글 버튼 상태 갱신
    document.querySelectorAll('.theme-toggle').forEach(function (btn) {
      var toLight = (theme === 'dark');
      btn.setAttribute('aria-label', toLight ? '라이트 모드로 전환' : '다크 모드로 전환');
      btn.setAttribute('title',      toLight ? '라이트 모드'       : '다크 모드');
    });
  }

  /** 다크 ↔ 라이트 전환 */
  function toggle() {
    var next = getTheme() === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem(STORAGE_KEY, next); } catch (_) {}
    applyTheme(next);
  }

  // 즉시 적용 (스크립트 로드 시점)
  applyTheme(getTheme());

  // 시스템 설정 변경 감지 (사용자가 직접 설정하지 않은 경우에만)
  try {
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', function (e) {
      try {
        if (!localStorage.getItem(STORAGE_KEY)) applyTheme(e.matches ? 'light' : 'dark');
      } catch (_) {}
    });
  } catch (_) {}

  // 이벤트 위임: 동적 주입(nav.js) 포함 모든 .theme-toggle 버튼 처리
  // DOMContentLoaded 개별 바인딩 대신 document 레벨 단일 핸들러 사용
  document.addEventListener('click', function (e) {
    if (e.target.closest('.theme-toggle')) toggle();
  });

  document.addEventListener('DOMContentLoaded', function () {
    applyTheme(getTheme()); // 아이콘 상태 재적용
  });

  // 전역 노출
  window.Theme = { toggle: toggle, get: getTheme, apply: applyTheme };
})();

