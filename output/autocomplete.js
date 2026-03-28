// ── autocomplete.js ──────────────────────────────────────────────────────────
// 티커 자동완성 드롭다운 — 모든 페이지 공용
// 사용법: TickerAC.init(inputEl, getItems, onSelect)
//   getItems(query)  → [{ticker, name}, ...]
//   onSelect(ticker, name, inputEl)
// ─────────────────────────────────────────────────────────────────────────────
(function () {
  // ── 스타일 주입 ───────────────────────────────────────────
  var s = document.createElement('style');
  s.textContent = [
    '.ac-drop{position:fixed;z-index:9999;',
      'background:rgba(12,16,26,0.97);',
      'backdrop-filter:blur(20px);',
      'border:1px solid rgba(255,255,255,0.1);',
      'border-radius:10px;overflow:hidden;',
      'box-shadow:0 8px 32px rgba(0,0,0,0.6);',
      'min-width:220px;}',
    '.ac-item{padding:9px 14px;cursor:pointer;',
      'display:flex;align-items:center;gap:10px;',
      'transition:background 0.1s;user-select:none;}',
    '.ac-item:hover,.ac-item.on{background:rgba(59,130,246,0.18);}',
    '.ac-tkr{font-size:.86rem;font-weight:800;color:#e2e8f0;',
      'letter-spacing:.04em;min-width:52px;flex-shrink:0;}',
    '.ac-name{font-size:.76rem;color:#64748b;',
      'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}',
  ].join('');
  document.head.appendChild(s);

  var _active = null; // 현재 열린 드롭다운

  function closeAll() {
    if (_active) { _active.remove(); _active = null; }
  }

  // 드롭다운 바깥 클릭 시 닫기
  document.addEventListener('mousedown', function (e) {
    if (_active && !_active.contains(e.target)) closeAll();
  });
  document.addEventListener('touchstart', function (e) {
    if (_active && !_active.contains(e.target)) closeAll();
  }, { passive: true });

  // ── 티커 필터 헬퍼 ────────────────────────────────────────
  // 1순위: 티커가 쿼리로 시작 (길이순 정렬)
  // 2순위: 티커에 쿼리 포함
  // 3순위: 이름에 쿼리 포함
  window.acFilter = function (query, allData, max) {
    max = max || 8;
    if (!query) return [];
    var q = query.toUpperCase();
    var starts = [], contains = [], names = [];
    var seen = {};
    var entries = Object.values(allData);
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i];
      if (!e || !e.ticker || seen[e.ticker]) continue;
      seen[e.ticker] = 1;
      var t = e.ticker;
      var n = e.name || '';
      if (t.indexOf(q) === 0)        starts.push({ ticker: t, name: n });
      else if (t.indexOf(q) >= 0)    contains.push({ ticker: t, name: n });
      else if (n.toUpperCase().indexOf(q) >= 0) names.push({ ticker: t, name: n });
    }
    starts.sort(function (a, b) { return a.ticker.length - b.ticker.length; });
    return starts.concat(contains).concat(names).slice(0, max);
  };

  // ── 핵심 init 함수 ────────────────────────────────────────
  window.TickerAC = {
    /**
     * @param {HTMLInputElement} input
     * @param {function(string): Array<{ticker,name}>} getItems
     * @param {function(string, string, HTMLInputElement)} onSelect
     * @param {object} [opts]
     *   opts.multiWord {boolean} — 스페이스 구분 다중 티커 입력 (compare)
     */
    init: function (input, getItems, onSelect, opts) {
      if (!input || input._acInited) return;
      input._acInited = true;
      opts = opts || {};

      var drop = null;
      var activeIdx = -1;

      function currentQuery() {
        var v = input.value;
        if (opts.multiWord) {
          var parts = v.split(/\s+/);
          return parts[parts.length - 1].toUpperCase();
        }
        return v.toUpperCase();
      }

      function show(items) {
        hide();
        if (!items.length) return;

        drop = document.createElement('div');
        drop.className = 'ac-drop';

        var rect = input.getBoundingClientRect();
        drop.style.top  = (rect.bottom + window.scrollY + 4) + 'px';
        drop.style.left = (rect.left   + window.scrollX)     + 'px';
        drop.style.width = Math.max(rect.width, 220) + 'px';
        // viewport 하단 넘치면 위로 올림
        drop.style.maxHeight = '280px';
        drop.style.overflowY = 'auto';

        items.forEach(function (item) {
          var el = document.createElement('div');
          el.className = 'ac-item';
          el.innerHTML =
            '<span class="ac-tkr">' + item.ticker + '</span>' +
            '<span class="ac-name">' + (item.name || '') + '</span>';

          function pick(e) {
            e.preventDefault();
            if (opts.multiWord) {
              // 마지막 단어를 선택한 티커로 교체
              var parts = input.value.split(/\s+/);
              parts[parts.length - 1] = item.ticker;
              input.value = parts.join(' ');
            }
            onSelect(item.ticker, item.name, input);
            hide();
            input.focus();
          }
          el.addEventListener('mousedown', pick);
          el.addEventListener('touchstart', pick, { passive: false });
          drop.appendChild(el);
        });

        document.body.appendChild(drop);
        _active = drop;
        activeIdx = -1;

        // 화면 아래 넘치는지 체크 후 위로 플립
        var dRect = drop.getBoundingClientRect();
        if (dRect.bottom > window.innerHeight - 8) {
          drop.style.top = (rect.top + window.scrollY - dRect.height - 4) + 'px';
        }
      }

      function hide() {
        if (drop) { drop.remove(); drop = null; }
        if (_active === drop) _active = null;
        activeIdx = -1;
      }

      function highlight(idx) {
        if (!drop) return;
        var items = drop.querySelectorAll('.ac-item');
        items.forEach(function (el, i) { el.classList.toggle('on', i === idx); });
        activeIdx = idx;
      }

      input.addEventListener('input', function () {
        var q = currentQuery();
        if (q.length < 1) { hide(); return; }
        show(getItems(q));
      });

      input.addEventListener('keydown', function (e) {
        if (!drop) return;
        var items = drop.querySelectorAll('.ac-item');
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          highlight(Math.min(activeIdx + 1, items.length - 1));
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          highlight(Math.max(activeIdx - 1, 0));
        } else if ((e.key === 'Enter' || e.key === 'Tab') && activeIdx >= 0) {
          e.preventDefault();
          items[activeIdx].dispatchEvent(
            new MouseEvent('mousedown', { bubbles: true })
          );
        } else if (e.key === 'Escape') {
          hide();
        }
      });

      input.addEventListener('blur', function () {
        setTimeout(hide, 200);
      });

      window.addEventListener('scroll', hide, { passive: true });
      window.addEventListener('resize', hide, { passive: true });
    },
  };
})();
