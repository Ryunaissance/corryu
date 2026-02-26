/**
 * corryu i18n — lightweight translation engine
 * Usage:
 *   HTML : <button data-i18n="btn.save">저장</button>
 *          <button data-i18n-title="btn.reset.title">…</button>
 *          <input  data-i18n-placeholder="search.placeholder">
 *   JS   : I18n.t('toast.sync.ok')
 *          I18n.t('fab.selected', { count: 3 })
 *          I18n.locale()  →  'ko' | 'en'
 */
window.I18n = (function () {
  let _locale = 'ko';
  let _msgs   = {};

  // ── 문자열 조회 ───────────────────────────────────
  function t(key, vars) {
    let s = Object.prototype.hasOwnProperty.call(_msgs, key) ? _msgs[key] : key;
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        s = s.split('{' + k + '}').join(v);
      }
    }
    return s;
  }

  // ── DOM 일괄 적용 ─────────────────────────────────
  function apply() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll('[data-i18n-html]').forEach(el => {
      el.innerHTML = t(el.dataset.i18nHtml);
    });
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      el.title = t(el.dataset.i18nTitle);
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      el.placeholder = t(el.dataset.i18nPlaceholder);
    });

    // 언어 스위처 버튼 텍스트 갱신
    const sw = document.getElementById('lang-switcher');
    if (sw) sw.textContent = _locale === 'ko' ? 'EN' : '한';

    document.documentElement.lang = _locale;
  }

  // ── 언어 전환 ─────────────────────────────────────
  async function setLocale(lang) {
    try {
      const r = await fetch('/locales/' + lang + '.json?v=' + (window._i18nVer || '1'));
      if (!r.ok) throw new Error('HTTP ' + r.status);
      _msgs   = await r.json();
      _locale = lang;
      localStorage.setItem('corryu_lang', lang);
      apply();
      document.dispatchEvent(new CustomEvent('i18n:ready', { detail: { locale: lang } }));
    } catch (e) {
      console.warn('[i18n] failed to load locale:', lang, e.message);
    }
  }

  // ── 초기화 (페이지 로드 시 1회) ───────────────────
  async function init() {
    const saved = localStorage.getItem('corryu_lang') || 'ko';
    await setLocale(saved);
  }

  function locale() { return _locale; }

  return { t, apply, init, setLocale, locale };
})();
