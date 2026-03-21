"""render_html.py — HTML 대시보드 렌더러 (모듈형)

output/etf_data.json 을 읽어 output/index.html 을 생성합니다.
pandas 불필요 · 단독 실행 가능 · Vercel 빌드 커맨드 진입점
"""
import json
import os
import sys
from datetime import datetime

# src/ 모듈 접근
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from config import SECTOR_DEFS, SUPER_SECTOR_DEFS, ASSET_CLASSES, MY_PORTFOLIO, OUTPUT_DIR, ADMIN_EMAILS


def get_head():
    return """<head>
<script>try{if(localStorage.getItem('corryu-theme')==='light')document.documentElement.setAttribute('data-theme','light');}catch(e){}</script>
<script src="/theme.js"></script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="#0a0d14">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>CORRYU Master Valuation Dashboard</title>
<link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
<link href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<link href="/responsive.css" rel="stylesheet">
<link href="/dashboard.css" rel="stylesheet">
</head>"""


def get_navbar():
    return """<nav id="main-nav">
  <div class="nav-inner">
    <a href="/index" class="nav-brand">CORRYU</a>
    <div class="nav-links">
      <a href="/index"        class="nav-link active"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg><span data-i18n="nav.dashboard">대시보드</span></a>
      <a href="/screener"     class="nav-link"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg><span data-i18n="nav.screener">스크리너</span></a>
      <a href="/backtest"     class="nav-link"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg><span data-i18n="nav.backtest">백테스트</span></a>
      <a href="/correlation"  class="nav-link"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="8" cy="8" r="2"/><circle cx="16" cy="8" r="2"/><circle cx="12" cy="16" r="2"/><line x1="10" y1="8" x2="14" y2="8"/><line x1="9" y1="10" x2="11" y2="14"/><line x1="15" y1="10" x2="13" y2="14"/></svg><span data-i18n="nav.correlation">상관관계</span></a>
      <a href="/compare"      class="nav-link"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg><span data-i18n="nav.compare">비교</span></a>
      <a href="/portfolio"    class="nav-link"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/></svg><span data-i18n="nav.portfolio">포트폴리오</span></a>
      <a href="/graph"        class="nav-link"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="5" cy="12" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><line x1="7" y1="11.5" x2="17" y2="6.5"/><line x1="7" y1="12.5" x2="17" y2="17.5"/></svg><span data-i18n="btn.viewGraph">그래프</span></a>
    </div>
    <div class="nav-right">
      <button id="lang-switcher" onclick="I18n.setLocale(I18n.locale()==='ko'?'en':'ko')">EN</button>
      <div id="nav-auth"></div>
      <button class="theme-toggle" aria-label="라이트 모드로 전환" title="라이트 모드" onclick="Theme.toggle()"><svg class="theme-icon-sun" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg><svg class="theme-icon-moon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg></button>
      <button id="nav-mob-btn" class="nav-mob-btn" aria-label="메뉴"><svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="17" y2="6"/><line x1="3" y1="10" x2="17" y2="10"/><line x1="3" y1="14" x2="17" y2="14"/></svg></button>
    </div>
  </div>
</nav>
<div id="nav-mob-drawer" class="nav-mob-drawer">
  <a href="/index"        class="mob-link active"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg><span data-i18n="nav.dashboard">대시보드</span></a>
  <a href="/screener"     class="mob-link"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg><span data-i18n="nav.screener">스크리너</span></a>
  <a href="/backtest"     class="mob-link"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg><span data-i18n="nav.backtest">백테스트</span></a>
  <a href="/correlation"  class="mob-link"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="8" cy="8" r="2"/><circle cx="16" cy="8" r="2"/><circle cx="12" cy="16" r="2"/><line x1="10" y1="8" x2="14" y2="8"/><line x1="9" y1="10" x2="11" y2="14"/><line x1="15" y1="10" x2="13" y2="14"/></svg><span data-i18n="nav.correlation">상관관계</span></a>
  <a href="/compare"      class="mob-link"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg><span data-i18n="nav.compare">비교</span></a>
  <a href="/portfolio"    class="mob-link"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/></svg><span data-i18n="nav.portfolio">포트폴리오</span></a>
  <a href="/graph"        class="mob-link"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="5" cy="12" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><line x1="7" y1="11.5" x2="17" y2="6.5"/><line x1="7" y1="12.5" x2="17" y2="17.5"/></svg><span data-i18n="btn.viewGraph">그래프</span></a>
  <div class="mob-drawer-divider"></div>
  <div class="mob-drawer-bottom">
    <button class="mob-lang-btn" onclick="I18n.setLocale(I18n.locale()==='ko'?'en':'ko')">EN / 한</button>
    <div id="nav-mob-auth"></div>
  </div>
</div>
<div id="nav-mob-overlay" class="nav-mob-overlay"></div>"""


def get_body(total_etfs, total_legacy, total_active, total_sectors, today):
    return f"""<body style="padding-top:57px">
<div class="gradient-line"></div>
{get_navbar()}
<div class="max-w-screen-2xl mx-auto" style="padding:16px">
    <div class="glass p-4 mb-4" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
      <div>
        <h1 style="font-size:1.25rem;font-weight:900;letter-spacing:-.02em;margin:0">
          <span class="text-gradient">Master Valuation</span> Dashboard
        </h1>
        <p style="font-size:0.8rem;color:var(--text-muted);margin:4px 0 0">
          Total <strong style="color:var(--text-primary)" id="hdr-total">{total_etfs:,}</strong> ETFs
          <span id="hdr-legacy-label"> · <span id="hdr-legacy">{total_legacy:,}</span> legacy · <strong style="color:#4ade80" id="hdr-active">{total_active:,}</strong> active</span>
          &nbsp;·&nbsp; <strong style="color:var(--text-primary)">{total_sectors}</strong> Sectors
          &nbsp;·&nbsp; Updated <span style="color:#94a3b8">{today}</span>
        </p>
      </div>
    </div>
    <div class="glass p-4 mb-4">
        <div class="flex items-center gap-2 overflow-x-auto pb-1" id="acTabs">
            <button class="ac-tab active" data-ac="ALL" data-i18n="filter.all">전체</button>
        </div>
    </div>
    <div class="glass p-4 mb-4">
        <div class="flex flex-wrap" id="secTabs"></div>
        <div class="flex flex-wrap" id="subSecTabs"></div>
    </div>
    <div class="glass p-4 mb-4">
        <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div class="flex items-center gap-3 overflow-x-auto" id="summaryCards"></div>
            <div class="flex flex-wrap items-center gap-3 text-sm">
                <label class="flex items-center gap-1.5 text-gray-400 cursor-pointer">
                    <input type="checkbox" id="filterLegacy" class="filter-check">
                    <span data-i18n="filter.hideLegacy">Legacy 숨기기</span>
                </label>
                <label class="flex items-center gap-1.5 text-gray-400 cursor-pointer">
                    <input type="checkbox" id="filterShort" class="filter-check">
                    <span data-i18n="filter.hideShortHistory">짧은연혁 숨기기</span>
                </label>
                <div class="flex items-center gap-1.5 text-gray-400">
                    <span>Min AUM</span>
                    <input type="number" id="filterAum" class="filter-input" placeholder="$M" value="0">
                    <span>M$</span>
                </div>
                <div class="flex items-center gap-1.5 text-gray-400">
                    <span>Min Sortino</span>
                    <input type="number" id="filterSortino" class="filter-input" placeholder="0" value="" step="0.1">
                </div>
            </div>
        </div>
    </div>
    <div class="glass p-4" style="position:relative;overflow-x:auto">
        <table id="masterTable" class="display nowrap" style="width:100%">
            <thead>
                <tr>
                    <th style="width:28px;min-width:28px;text-align:center !important"><input type="checkbox" id="select-all-cb"></th>
                    <th data-i18n-title="col.no.tip" style="width:36px;min-width:36px">#</th>
                    <th class="text-left">Ticker</th>
                    <th class="text-left" style="min-width:220px" data-i18n="col.name">ETF 명칭</th>
                    <th>Rank</th>
                    <th>AUM</th>
                    <th data-i18n-title="col.rAnchor.tip">r_Anchor</th>
                    <th data-i18n-title="col.rSmh.tip">SMH Corr</th>
                    <th data-i18n-title="col.zScore.tip">Z-Score</th>
                    <th data-i18n-title="col.ma200.tip">200MA</th>
                    <th data-i18n-title="col.rsi.tip">RSI</th>
                    <th data-i18n-title="col.range52w.tip">52W Rng</th>
                    <th data-i18n-title="col.mdd52w.tip">52W MDD</th>
                    <th data-i18n-title="col.cagr.tip">CAGR</th>
                    <th data-i18n-title="col.vol.tip">Vol</th>
                    <th data-i18n-title="col.sortino.tip">Sortino</th>
                    <th data-i18n-title="col.divYield.tip">Div%</th>
                    <th data-i18n-title="col.inception.tip">Inception</th>
                    <th data-i18n-title="col.status.tip" style="min-width:80px">Status</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>
    </div>
</div>
<div id="fab">
    <div id="fab-card">
        <div id="fab-label"></div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <button class="fab-btn" id="fab-btn-legacy" data-i18n="btn.legacy.mark">레거시 처리</button>
            <button class="fab-btn" id="fab-btn-unlegacy" data-i18n="btn.legacy.unmark">레거시 해제</button>
            <button class="fab-btn" id="fab-btn-move" data-i18n="btn.move">↪ 카테고리 이동</button>
            <button class="fab-btn" id="fab-btn-clear" data-i18n="btn.clear">×</button>
        </div>
    </div>
</div>
<div id="sector-modal">
    <div id="sector-modal-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:18px">
            <div>
                <div style="font-weight:700;font-size:1rem;color:#e2e8f0" data-i18n="fab.move.title">↪ 카테고리 이동</div>
                <div style="font-size:0.78rem;color:#64748b;margin-top:3px" id="modal-sel-info"></div>
            </div>
            <button id="sector-modal-close" style="background:transparent;border:none;color:#475569;font-size:1.3rem;cursor:pointer;line-height:1;padding:2px 6px" title="닫기">×</button>
        </div>
        <div id="sector-modal-body"></div>
    </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js"></script>
<script src="/supabase-client.js"></script>
<script src="/i18n.js"></script>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
</body>"""


def generate_html(sector_meta):
    """HTML 대시보드 생성 (데이터는 etf_data.json 에서 fetch, pandas 불필요)"""
    today = datetime.now().strftime('%Y-%m-%d')
    total_etfs    = sum(m['count']  for m in sector_meta.values())
    total_active  = sum(m['active'] for m in sector_meta.values())
    total_legacy  = sum(m['legacy'] for m in sector_meta.values())
    total_sectors = len([s for s in sector_meta.values() if s['count'] > 0])

    # 자산군별 섹터 그룹핑
    ac_sectors = {}
    for sid, sdef in SECTOR_DEFS.items():
        ac = sdef['asset_class']
        ac_sectors.setdefault(ac, []).append(sid)

    json_ac_sectors  = json.dumps(ac_sectors, ensure_ascii=False)
    json_ac_defs     = json.dumps({k: v for k, v in ASSET_CLASSES.items()}, ensure_ascii=False)
    json_sector_defs = json.dumps(
        {k: {'name': v['name'], 'name_en': v['name_en'],
             'icon': v['icon'], 'anchor': v['anchor'] or '—',
             'asset_class': v['asset_class'],
             'super_sector': v.get('super_sector')}
         for k, v in SECTOR_DEFS.items()}, ensure_ascii=False)
    json_super_sector_defs = json.dumps(
        {k: {'name': v['name'], 'name_en': v['name_en'],
             'anchor': v['anchor'], 'icon': v['icon'],
             'color': v['color'], 'sub_sectors': v['sub_sectors']}
         for k, v in SUPER_SECTOR_DEFS.items()}, ensure_ascii=False)
    json_my_portfolio = json.dumps(MY_PORTFOLIO)
    json_admin_emails = json.dumps(list(ADMIN_EMAILS))

    html = f"""<!DOCTYPE html>
<html lang="ko">
{get_head()}
{get_body(total_etfs, total_legacy, total_active, total_sectors, today)}
<script>
window.CORRYU_CONFIG = {{
    "ac_sectors": {json_ac_sectors},
    "ac_defs": {json_ac_defs},
    "sector_defs": {json_sector_defs},
    "super_sector_defs": {json_super_sector_defs},
    "my_portfolio": {json_my_portfolio},
    "admin_emails": {json_admin_emails}
}};
</script>
<script src="/dashboard.js"></script>
<script src="/nav.js"></script>
</html>"""

    return html


def main():
    etf_data_path = os.path.join(OUTPUT_DIR, 'etf_data.json')
    if not os.path.exists(etf_data_path):
        print(f"ERROR: {etf_data_path} 없음. dashboard_builder.py 를 먼저 실행하세요.")
        sys.exit(1)

    with open(etf_data_path, 'r', encoding='utf-8') as f:
        etf_data = json.load(f)

    sector_meta = etf_data['sectorMeta']
    html = generate_html(sector_meta)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    total = sum(m['count']  for m in sector_meta.values())
    active = sum(m['active'] for m in sector_meta.values())
    legacy = sum(m['legacy'] for m in sector_meta.values())
    print(f"HTML 생성 완료: {out_path}")
    print(f"  전체 {total:,}개 | Active {active:,}개 | Legacy {legacy:,}개")


if __name__ == '__main__':
    main()
