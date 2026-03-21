"""render_html.py — HTML 대시보드 렌더러

output/etf_data.json 을 읽어 output/master_dashboard.html 을 생성합니다.
pandas 불필요 · 단독 실행 가능 · Vercel 빌드 커맨드 진입점

Usage:
    python3 render_html.py
"""
import json
import os
import sys
from datetime import datetime

# src/ 모듈 접근
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from config import SECTOR_DEFS, SUPER_SECTOR_DEFS, ASSET_CLASSES, MY_PORTFOLIO, OUTPUT_DIR, ADMIN_EMAILS


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
<head>
<script>try{{if(localStorage.getItem('corryu-theme')==='light')document.documentElement.setAttribute('data-theme','light');}}catch(e){{}}</script>
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
<style>
:root {{ --bg-primary: #0a0d14; --bg-card: rgba(20,24,38,0.85); --bg-hover: rgba(59,130,246,0.08); --border: rgba(255,255,255,0.07); --text-primary: #e2e8f0; --text-muted: #7d90a4; --accent: #3b82f6; --accent-glow: rgba(59,130,246,0.3); }}
* {{ box-sizing: border-box; }}
body {{ background-color: var(--bg-primary); color: var(--text-primary); font-family: 'Inter', -apple-system, sans-serif; margin: 0; padding: 16px; }}
.glass {{ background: var(--bg-card); backdrop-filter: blur(16px); border: 1px solid var(--border); border-radius: 14px; }}
.text-gradient {{ background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; }}

/* Asset Class Tabs */
.ac-tab {{ padding: 8px 18px; border-radius: 10px; background: transparent; color: var(--text-muted); border: 1px solid transparent; font-weight: 600; font-size: 0.9rem; cursor: pointer; transition: all 0.2s; white-space: nowrap; }}
.ac-tab:hover {{ color: var(--text-primary); background: var(--bg-hover); }}
.ac-tab.active {{ background: var(--accent); color: #fff; border-color: var(--accent); box-shadow: 0 0 20px var(--accent-glow); }}

/* Sector Tabs */
.sec-tab {{ padding: 6px 14px; border-radius: 8px; background: rgba(255,255,255,0.03); color: var(--text-muted); border: 1px solid rgba(255,255,255,0.06); font-weight: 500; font-size: 0.82rem; cursor: pointer; transition: all 0.15s; white-space: nowrap; margin: 3px; }}
.sec-tab:hover {{ color: var(--text-primary); border-color: rgba(255,255,255,0.15); }}
.sec-tab.active {{ background: rgba(59,130,246,0.15); color: #93c5fd; border-color: rgba(59,130,246,0.4); }}
.sec-tab .sec-count {{ font-size: 0.7rem; opacity: 0.6; margin-left: 4px; }}
/* Super-sector tab */
.super-sec-tab {{ background: rgba(59,130,246,0.07); border-color: rgba(59,130,246,0.2); color: #93c5fd; }}
.super-sec-tab:hover {{ background: rgba(59,130,246,0.15); border-color: rgba(59,130,246,0.4); }}
.super-sec-tab.active {{ background: rgba(59,130,246,0.22); color: #fff; border-color: rgba(59,130,246,0.6); box-shadow: 0 0 12px rgba(59,130,246,0.2); }}
/* Sub-sector tabs row */
#subSecTabs {{ display:none; padding: 6px 0 2px 0; border-top: 1px solid rgba(59,130,246,0.15); margin-top: 4px; }}
.sub-sec-tab {{ font-size: 0.77rem; padding: 4px 11px; }}
.expand-arrow {{ font-size: 0.65rem; margin-left: 4px; opacity: 0.7; }}

/* Summary Cards */
.stat-card {{ display: flex; flex-direction: column; align-items: center; padding: 12px 8px; background: rgba(10,13,20,0.5); border-radius: 10px; border: 1px solid var(--border); min-width: 90px; }}
.stat-card .stat-value {{ font-size: 1.3rem; font-weight: 700; }}
.stat-card .stat-label {{ font-size: 0.7rem; color: var(--text-muted); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}

/* DataTables Override */
table.dataTable {{ border-collapse: collapse; width: 100%; color: #cbd5e1; font-size: 0.88rem; }}
table.dataTable thead th {{ background: rgba(20,24,38,0.95); color: #64748b; border-bottom: 2px solid rgba(255,255,255,0.08); padding: 10px 8px; font-weight: 600; font-size: 0.78rem; text-align: right; text-transform: uppercase; letter-spacing: 0.3px; }}
table.dataTable tbody td {{ border-bottom: 1px solid rgba(255,255,255,0.04); padding: 10px 8px; text-align: right; }}
table.dataTable tbody tr:hover {{ background-color: var(--bg-hover) !important; }}
table.dataTable thead th.text-left, table.dataTable tbody td.text-left {{ text-align: left !important; }}
.dataTables_wrapper .dataTables_filter input {{ color: white; background: rgba(20,24,38,0.95); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 6px 14px; font-size: 0.85rem; }}
.dataTables_wrapper .dataTables_filter input:focus {{ outline: none; border-color: var(--accent); box-shadow: 0 0 8px var(--accent-glow); }}
.dataTables_wrapper .dataTables_length select {{ color: white; background: rgba(20,24,38,0.95); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 4px; }}
.dataTables_wrapper .dataTables_info, .dataTables_wrapper .dataTables_paginate {{ color: var(--text-muted); font-size: 0.8rem; padding-top: 12px; }}
.dataTables_wrapper .dataTables_paginate .paginate_button {{ color: var(--text-muted) !important; border: 1px solid rgba(255,255,255,0.06) !important; border-radius: 6px !important; background: transparent !important; margin: 0 2px; }}
.dataTables_wrapper .dataTables_paginate .paginate_button.current {{ background: var(--accent) !important; color: #fff !important; border-color: var(--accent) !important; }}

/* Legacy badge */
.badge-legacy {{ display: inline-flex; align-items: center; gap: 3px; padding: 2px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; background: rgba(239,68,68,0.12); color: #f87171; border: 1px solid rgba(239,68,68,0.2); }}
.badge-active {{ display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; background: rgba(34,197,94,0.1); color: #4ade80; border: 1px solid rgba(34,197,94,0.15); }}
.badge-short {{ display: inline-flex; align-items: center; padding: 2px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: 600; background: rgba(234,179,8,0.12); color: #facc15; border: 1px solid rgba(234,179,8,0.2); margin-left: 4px; }}
.tag {{ display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: 600; margin: 1px; }}
.value-up {{ color: #f87171; }} .value-down {{ color: #60a5fa; }}
.row-legacy td {{ opacity: 0.45; text-decoration: line-through; }}
.mine-badge {{ background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #000; padding: 2px 8px; border-radius: 4px; font-size: 0.68rem; font-weight: 800; box-shadow: 0 0 10px rgba(251,191,36,0.4); }}
.badge-user-legacy {{ display: inline-flex; align-items: center; gap: 3px; padding: 2px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; background: rgba(249,115,22,0.12); color: #fb923c; border: 1px solid rgba(249,115,22,0.3); }}
.badge-user-sector {{ display: inline-flex; align-items: center; gap: 3px; padding: 2px 7px; border-radius: 5px; font-size: 0.68rem; font-weight: 600; background: rgba(139,92,246,0.12); color: #a78bfa; border: 1px solid rgba(139,92,246,0.25); }}

/* Checkbox column */
input.row-cb {{ width: 15px; height: 15px; cursor: pointer; accent-color: #3b82f6; vertical-align: middle; }}
input#select-all-cb {{ width: 15px; height: 15px; cursor: pointer; accent-color: #3b82f6; }}
table.dataTable tbody tr.row-selected {{ background: rgba(59,130,246,0.08) !important; outline: 1px solid rgba(59,130,246,0.2); }}

/* FAB */
#fab {{ position: fixed; bottom: 28px; right: 28px; z-index: 9999; display: none; animation: fabIn 0.18s ease; }}
@keyframes fabIn {{ from {{ opacity:0; transform: translateY(10px); }} to {{ opacity:1; transform: translateY(0); }} }}
#fab-card {{ background: rgba(20,24,38,0.97); border: 1px solid rgba(59,130,246,0.4); border-radius: 14px; padding: 12px 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(59,130,246,0.1); backdrop-filter: blur(16px); min-width: 260px; }}
#fab-label {{ font-size: 0.78rem; color: #64748b; margin-bottom: 10px; }}
#fab-count {{ color: #93c5fd; font-weight: 700; }}
.fab-btn {{ display: inline-flex; align-items: center; gap: 5px; padding: 7px 14px; border-radius: 8px; font-size: 0.82rem; font-weight: 600; border: none; cursor: pointer; transition: all 0.15s; }}
#fab-btn-legacy {{ background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }}
#fab-btn-legacy:hover {{ background: rgba(239,68,68,0.28); }}
#fab-btn-unlegacy {{ background: rgba(34,197,94,0.12); color: #4ade80; border: 1px solid rgba(34,197,94,0.25); }}
#fab-btn-unlegacy:hover {{ background: rgba(34,197,94,0.22); }}
#fab-btn-move {{ background: rgba(139,92,246,0.15); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); }}
#fab-btn-move:hover {{ background: rgba(139,92,246,0.28); }}
#fab-btn-clear {{ background: rgba(255,255,255,0.05); color: #64748b; border: 1px solid rgba(255,255,255,0.08); padding: 7px 10px; }}
#fab-btn-clear:hover {{ background: rgba(255,255,255,0.1); color: #94a3b8; }}

/* Watchlist FAB */
#fab-btn-watch   {{ background: rgba(244,63,94,0.12); color: #fb7185; border: 1px solid rgba(244,63,94,0.3); }}
#fab-btn-watch:hover   {{ background: rgba(244,63,94,0.24); }}
#fab-btn-unwatch {{ background: rgba(100,116,139,0.1);  color: #94a3b8; border: 1px solid rgba(100,116,139,0.2); }}
#fab-btn-unwatch:hover {{ background: rgba(100,116,139,0.2); }}
/* 관심종목 탭 */
.watchlist-tab {{ color: #fb7185 !important; }}
.watchlist-tab.active {{ background: rgba(244,63,94,0.15) !important; color: #fb7185 !important; border-color: rgba(244,63,94,0.45) !important; box-shadow: 0 0 20px rgba(244,63,94,0.2) !important; }}
.watchlist-tab:hover:not(.active) {{ background: rgba(244,63,94,0.08) !important; }}
.wl-count {{ display: inline-flex; align-items: center; justify-content: center; min-width: 17px; height: 17px; border-radius: 9px; background: rgba(251,191,36,0.2); font-size: 0.68rem; font-weight: 800; padding: 0 4px; margin-left: 3px; vertical-align: middle; }}
/* Star 버튼 */
.star-btn {{ background: none; border: none; cursor: pointer; color: #374151; font-size: 0.95rem; line-height: 1; transition: color 0.12s, transform 0.12s; padding: 1px 3px; border-radius: 3px; vertical-align: middle; }}
.star-btn:hover   {{ color: #fb7185; transform: scale(1.25); }}
.star-btn.starred {{ color: #f43f5e; }}
/* 관심종목 행 강조 */
table.dataTable tbody tr.row-watchlist {{ background: rgba(244,63,94,0.04) !important; }}
table.dataTable tbody tr.row-watchlist.row-selected {{ background: rgba(59,130,246,0.1) !important; }}

/* 플로팅 저장 버튼 */
#save-float {{ position: fixed; bottom: 28px; left: 28px; z-index: 9998; display: none; animation: fabIn 0.18s ease; }}
#save-float.visible {{ display: block; }}
#save-float-btn {{ display: inline-flex; align-items: center; gap: 8px; padding: 11px 20px; border-radius: 12px; font-size: 0.85rem; font-weight: 700; cursor: pointer; transition: background 0.2s, color 0.2s, border-color 0.2s; backdrop-filter: blur(14px); box-shadow: 0 4px 24px rgba(0,0,0,0.45); border: 1px solid rgba(59,130,246,0.45); background: rgba(59,130,246,0.18); color: #93c5fd; }}
#save-float-btn:hover:not(:disabled) {{ background: rgba(59,130,246,0.32); }}
#save-float-btn:disabled {{ cursor: not-allowed; }}
#save-float-btn.state-saving {{ color: #fbbf24; border-color: rgba(251,191,36,0.4); background: rgba(251,191,36,0.1); }}
#save-float-btn.state-saved  {{ color: #4ade80; border-color: rgba(74,222,128,0.4);  background: rgba(74,222,128,0.1); }}
#save-float-btn.state-error  {{ color: #f87171; border-color: rgba(248,113,113,0.4); background: rgba(248,113,113,0.1); }}

/* 카테고리 이동 모달 */
#sector-modal {{ display:none; position:fixed; inset:0; z-index:10000; background:rgba(0,0,0,0.72); backdrop-filter:blur(4px); align-items:center; justify-content:center; }}
#sector-modal.show {{ display:flex; }}
#sector-modal-card {{ background:#0f1623; border:1px solid rgba(139,92,246,0.4); border-radius:16px; padding:24px; width:min(580px,95vw); max-height:82vh; overflow-y:auto; box-shadow:0 24px 64px rgba(0,0,0,0.7); }}
.smb {{ display:flex; align-items:center; gap:8px; padding:9px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.07); background:rgba(255,255,255,0.03); color:#cbd5e1; font-size:0.82rem; cursor:pointer; transition:all 0.15s; width:100%; text-align:left; }}
.smb:hover {{ background:rgba(139,92,246,0.15); border-color:rgba(139,92,246,0.4); color:#e2e8f0; }}
.smb.cur {{ border-color:rgba(59,130,246,0.5); background:rgba(59,130,246,0.1); color:#93c5fd; }}
.smg {{ font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:0.8px; color:#334155; padding:14px 0 5px 2px; }}

/* Filter controls */
.filter-input {{ background: rgba(20,24,38,0.95); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #e2e8f0; padding: 6px 10px; font-size: 0.82rem; width: 90px; }}
.filter-input:focus {{ outline: none; border-color: var(--accent); }}
.filter-check {{ accent-color: var(--accent); width: 16px; height: 16px; cursor: pointer; }}

/* Tooltip */
.tooltip-container {{ position: relative; cursor: help; }}
.tooltip-content {{ display: none; position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); background: #1e293b; color: #e2e8f0; padding: 8px 12px; border-radius: 8px; font-size: 0.75rem; white-space: nowrap; z-index: 999; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 4px 12px rgba(0,0,0,0.5); max-width: 350px; white-space: normal; }}
.tooltip-container:hover .tooltip-content {{ display: block; }}

/* ── Fixed Navbar ── */
.gradient-line {{ position:fixed; top:0; left:0; right:0; height:3px; z-index:1001; background:linear-gradient(90deg,#3b82f6,#8b5cf6,#ec4899,#f59e0b); }}
#main-nav {{ position:fixed; top:3px; left:0; right:0; z-index:1000; background:rgba(10,13,20,0.92); backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px); border-bottom:1px solid rgba(255,255,255,0.07); height:54px; display:flex; align-items:center; }}
.nav-inner {{ max-width:1536px; margin:0 auto; padding:0 20px; width:100%; display:flex; align-items:center; gap:0; }}
.nav-brand {{ font-size:1rem; font-weight:900; text-decoration:none; background:linear-gradient(135deg,#60a5fa,#a78bfa); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; white-space:nowrap; margin-right:24px; flex-shrink:0; }}
.nav-links {{ display:flex; align-items:center; gap:2px; overflow-x:auto; flex:1; min-width:0; }}
.nav-links::-webkit-scrollbar {{ display:none; }}
.nav-link {{ display:inline-flex; align-items:center; gap:5px; padding:5px 11px; border-radius:8px; font-size:0.78rem; font-weight:600; text-decoration:none; color:#64748b; transition:all 0.15s; white-space:nowrap; border:1px solid transparent; }}
.nav-link:hover {{ color:#e2e8f0; background:rgba(255,255,255,0.06); }}
.nav-link.active {{ color:#60a5fa; background:rgba(59,130,246,0.1); border-color:rgba(59,130,246,0.25); }}
.nav-right {{ display:flex; align-items:center; gap:8px; flex-shrink:0; margin-left:16px; position:relative; z-index:2; }}
#lang-switcher {{ padding:4px 10px; border-radius:7px; background:rgba(255,255,255,0.05); color:#94a3b8; border:1px solid rgba(255,255,255,0.1); font-size:0.76rem; font-weight:700; cursor:pointer; transition:all 0.15s; font-family:inherit; }}
#lang-switcher:hover {{ background:rgba(255,255,255,0.1); color:#e2e8f0; }}
#nav-auth {{ display:flex; align-items:center; gap:6px; }}
#nav-user-nick {{ font-size:0.78rem; font-weight:700; color:#93c5fd; max-width:110px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; text-decoration:none; border-radius:6px; padding:2px 6px; transition:background 0.15s; }}
#nav-user-nick:hover {{ background:rgba(59,130,246,0.12); }}
#nav-logout-btn {{ padding:4px 10px; border-radius:7px; background:rgba(248,113,113,0.08); color:#f87171; border:1px solid rgba(248,113,113,0.2); font-size:0.74rem; font-weight:700; cursor:pointer; transition:all 0.15s; font-family:inherit; pointer-events:auto; position:relative; z-index:10; }}
#nav-logout-btn:hover {{ background:rgba(248,113,113,0.18); }}
#nav-login-btn {{ padding:5px 14px; border-radius:8px; background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.35); font-size:0.78rem; font-weight:700; cursor:pointer; text-decoration:none; transition:all 0.15s; display:inline-flex; align-items:center; gap:5px; }}
#nav-login-btn:hover {{ background:rgba(59,130,246,0.28); }}
</style>
</head>
<body style="padding-top:57px">
<!-- 상단 그라데이션 라인 -->
<div class="gradient-line"></div>

<!-- ── Fixed Navbar ── -->
<nav id="main-nav">
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
      <div id="nav-auth">
        <a href="/login" id="nav-login-btn"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg><span data-i18n="nav.login">로그인</span></a>
      </div>
      <button class="theme-toggle" aria-label="라이트 모드로 전환" title="라이트 모드" onclick="Theme.toggle()"><svg class="theme-icon-sun" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg><svg class="theme-icon-moon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg></button>
      <button id="nav-mob-btn" class="nav-mob-btn" aria-label="메뉴"><svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="17" y2="6"/><line x1="3" y1="10" x2="17" y2="10"/><line x1="3" y1="14" x2="17" y2="14"/></svg></button>
    </div>
  </div>
</nav>

<!-- 모바일 드로어 네비게이션 -->
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
    <a href="/login" id="nav-mob-login-btn" style="display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:8px;background:rgba(59,130,246,0.12);color:#60a5fa;border:1px solid rgba(59,130,246,0.3);font-size:0.82rem;font-weight:700;text-decoration:none;transition:all 0.15s"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg><span data-i18n="nav.login">로그인</span></a>
  </div>
</div>
<div id="nav-mob-overlay" class="nav-mob-overlay"></div>

<!-- ── 대시보드 본문 ── -->
<div class="max-w-screen-2xl mx-auto" style="padding:16px">

    <!-- 대시보드 타이틀 카드 -->
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

    <!-- Asset Class Tabs (Level 1) -->
    <div class="glass p-4 mb-4">
        <div class="flex items-center gap-2 overflow-x-auto pb-1" id="acTabs">
            <button class="ac-tab active" data-ac="ALL" data-i18n="filter.all">전체</button>
        </div>
    </div>

    <!-- Sector Tabs (Level 2) + Sub-sector Tabs (Level 3) -->
    <div class="glass p-4 mb-4">
        <div class="flex flex-wrap" id="secTabs"></div>
        <div class="flex flex-wrap" id="subSecTabs"></div>
    </div>

    <!-- Sector Summary + Filters -->
    <div class="glass p-4 mb-4">
        <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <!-- Summary Cards -->
            <div class="flex items-center gap-3 overflow-x-auto" id="summaryCards">
            </div>
            <!-- Filters -->
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
    </div>

    <!-- Data Table -->
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

<!-- FAB: 레거시 처리/해제/카테고리 이동 -->
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

<!-- 카테고리 이동 모달 -->
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
<script>
// sectorMeta, allData는 etf_data.json에서 fetch로 로드됩니다
let sectorMeta = {{}};
let allData = {{}};
const acSectors = {json_ac_sectors};

// ── 체크박스 선택 상태 ─────────────────────────────────
const selectedTickers = new Set();

// ── Admin 권한 감지 ──────────────────────────────────
const _adminEmails = new Set({json_admin_emails});
let _isAdmin = false;

async function detectAdmin() {{
    if (typeof CorryuAuth === 'undefined' || !CorryuAuth.isConfigured) return false;
    try {{
        const user = await CorryuAuth.getUser();
        if (!user) return false;
        if (user.app_metadata && user.app_metadata.role === 'admin') return true;
        if (user.email && _adminEmails.has(user.email)) return true;
        return false;
    }} catch(e) {{ return false; }}
}}

function stripLegacyForNonAdmin() {{
    for (const sid of Object.keys(allData)) {{
        for (const etf of allData[sid]) {{
            etf.is_legacy = false;
            etf.legacy_reasons = [];
            etf.legacy_detail = [];
        }}
    }}
}}

function applyAdminUI(isAdmin) {{
    _isAdmin = isAdmin;
    if (!isAdmin) {{
        $('#filterLegacy').closest('label').hide();
        $('#fab-btn-legacy, #fab-btn-unlegacy').hide();
        var $ll = $('#hdr-legacy-label');
        if ($ll.length) $ll.hide();
    }}
}}

// ── localStorage 레거시 오버라이드 ───────────────────
const USER_OVERRIDES_KEY = 'corryu_user_overrides';

function getUserOverrides() {{
    try {{ return JSON.parse(localStorage.getItem(USER_OVERRIDES_KEY) || '{{}}'); }}
    catch(e) {{ return {{}}; }}
}}
function saveUserOverrides(ov) {{
    localStorage.setItem(USER_OVERRIDES_KEY, JSON.stringify(ov));
    localStorage.setItem('corryu_overrides_ts', String(Date.now()));
    pushRemoteOverrides(ov);  // async, non-blocking
}}

function applyUserOverrides() {{
    const ov = getUserOverrides();
    if (!Object.keys(ov).length) return;
    applyOverridesToData(ov);
}}
const acDefs = {json_ac_defs};
const sectorDefs = {json_sector_defs};
const superSectorDefs = {json_super_sector_defs};
const myPortfolio = {json_my_portfolio};

// 섹터ID → 슈퍼섹터ID 역방향 맵
const sectorToSuperSector = {{}};
for (const [ssId, ss] of Object.entries(superSectorDefs)) {{
    for (const sid of ss.sub_sectors) sectorToSuperSector[sid] = ssId;
}}

let state = {{
    activeAC: 'ALL',
    activeSector: 'ALL',       // 'ALL' | 섹터ID | 'SS_<ssId>' (슈퍼섹터 전체)
    expandedSuperSector: null, // null | 슈퍼섹터ID (서브탭 표시 여부)
    hideLegacy: false,
    hideShort: false,
    minAum: 0,
    minSortino: -999
}};

let table;
let likedTickers = new Set();
let _currentUserId = null;

function applyHearts() {{
    document.querySelectorAll('.star-btn[data-like]').forEach(function(btn) {{
        var t = btn.dataset.like;
        var liked = likedTickers.has(t);
        btn.classList.toggle('starred', liked);
        btn.textContent = liked ? '♥' : '♡';
    }});
}}

function formatMCap(val) {{
    if (!val) return '-';
    let m = val / 1e6;
    if (m >= 1000) return '$' + (m/1000).toFixed(1) + 'B';
    return '$' + Math.round(m) + 'M';
}}

function renderACTabs() {{
    let html = '<button class="ac-tab' + (state.activeAC === 'ALL' ? ' active' : '') + '" data-ac="ALL">전체</button>';
    let ordered = Object.entries(acDefs).sort((a,b) => a[1].order - b[1].order);
    for (let [ac, def] of ordered) {{
        let isActive = state.activeAC === ac ? ' active' : '';
        html += '<button class="ac-tab' + isActive + '" data-ac="' + ac + '">' + def.icon + ' ' + def.name + '</button>';
    }}
    $('#acTabs').html(html);
}}

function getSuperSectorMeta(ssId) {{
    let ss = superSectorDefs[ssId];
    if (!ss) return {{}};
    let metas = ss.sub_sectors.map(sid => sectorMeta[sid] || {{}});
    return {{
        count:  metas.reduce((s,m) => s+(m.count||0), 0),
        active: metas.reduce((s,m) => s+(m.active||0), 0)
    }};
}}

function applySmhCorr() {{
    try {{
        const smhData = JSON.parse(localStorage.getItem('corryu_smh_corr') || 'null');
        if (!smhData) return;
        for (const sid of Object.keys(allData)) {{
            for (const etf of allData[sid]) {{
                if (etf.ticker in smhData) etf.smh_corr = smhData[etf.ticker];
            }}
        }}
    }} catch(e) {{}}
}}

// 모든 섹터에서 ticker로 ETF 검색 → {{ etf, sid }} | null
function findETFAnywhere(ticker) {{
    for (const sid of Object.keys(allData)) {{
        const idx = allData[sid].findIndex(e => e.ticker === ticker);
        if (idx !== -1) return {{ etf: allData[sid][idx], sid, idx }};
    }}
    return null;
}}

function applyOverridesToData(ov) {{
    // ① 현재 모든 섹터에 있는 ETF 수집 (이동됐을 수도 있음)
    const etfMap = {{}};
    for (const sid of Object.keys(allData)) {{
        for (const etf of allData[sid]) etfMap[etf.ticker] = etf;
    }}
    // ② 모든 섹터 배열 초기화 후 원래 섹터에 재배치 + 레거시 상태 원복
    for (const sid of Object.keys(allData)) allData[sid] = [];
    for (const [ticker, etf] of Object.entries(etfMap)) {{
        const origSid = etf._original_sector || etf._build_sector;
        if (!origSid || allData[origSid] === undefined) continue;
        if (!etf._user_override) {{
            etf.is_legacy      = etf._orig_legacy;
            etf.legacy_detail  = etf._orig_legacy_detail ? etf._orig_legacy_detail.slice() : [];
            etf.legacy_reasons = etf._orig_legacy_reasons ? etf._orig_legacy_reasons.slice() : [];
        }}
        if (!etf._user_override_r_anchor) {{
            etf.r_anchor = etf._orig_r_anchor;
        }}
        delete etf._user_sector;
        delete etf._original_sector;
        allData[origSid].push(etf);
    }}
    // ③ 레거시 오버라이드 적용
    for (const [ticker, o] of Object.entries(ov)) {{
        if (!('is_legacy' in o)) continue;
        const found = findETFAnywhere(ticker);
        if (!found) continue;
        found.etf.is_legacy      = o.is_legacy;
        found.etf._user_override = true;
        found.etf.legacy_detail  = o.is_legacy ? ['사용자 직접 지정'] : [];
        found.etf.legacy_reasons = o.is_legacy ? ['user_override'] : [];
    }}
    // ④ 섹터 이동 오버라이드 적용
    for (const [ticker, o] of Object.entries(ov)) {{
        const buildSid = etfMap[ticker] ? etfMap[ticker]._build_sector : null;
        if (!o.sector || o.sector === buildSid) continue;
        const currentFound = findETFAnywhere(ticker);
        if (!currentFound) continue;
        const {{ etf, sid: oldSid, idx }} = currentFound;
        const newSid  = o.sector;
        if (allData[newSid] === undefined) continue;
        allData[oldSid].splice(idx, 1);
        etf._user_sector    = newSid;
        etf._original_sector = oldSid;
        allData[newSid].push(etf);
    }}
    // ⑤ r_anchor 오버라이드 적용
    for (const [ticker, o] of Object.entries(ov)) {{
        if (o.r_anchor === undefined) continue;
        const found = findETFAnywhere(ticker);
        if (!found) continue;
        found.etf.r_anchor = o.r_anchor;
        found.etf._user_override_r_anchor = true;
    }}
}}

function renderSectorTabs() {{
    let sectors = [];
    if (state.activeAC === 'ALL') {{
        sectors = Object.keys(sectorDefs).sort();
    }} else {{
        sectors = (acSectors[state.activeAC] || []).sort();
    }}
    let allActive = state.activeSector === 'ALL' ? ' active' : '';
    let totalCount  = sectors.reduce((s, sid) => s + ((sectorMeta[sid]||{{}}).count||0), 0);
    let totalActiveN = sectors.reduce((s, sid) => s + ((sectorMeta[sid]||{{}}).active||0), 0);
    let html = '<button class="sec-tab' + allActive + '" data-sector="ALL">전체<span class="sec-count">' + totalActiveN + '/' + totalCount + '</span></button>';

    let renderedSS = new Set();
    for (let sid of sectors) {{
        let sd = sectorDefs[sid];
        let meta = sectorMeta[sid];
        if (!meta || meta.count === 0) continue;

        let ssId = sd.super_sector;
        if (ssId) {{
            if (renderedSS.has(ssId)) continue;  // 이미 슈퍼섹터 탭 추가됨
            renderedSS.add(ssId);
            let ss = superSectorDefs[ssId];
            let ssMeta = getSuperSectorMeta(ssId);
            let ssIsActive = state.expandedSuperSector === ssId;
            let isActiveSS = (state.activeSector === 'SS_' + ssId) ? ' active' : '';
            let arrow = ssIsActive ? ' ▾' : ' ▸';
            html += '<button class="sec-tab super-sec-tab' + isActiveSS + '" data-supersec="' + ssId + '">';
            html += ss.icon + ' ' + ss.name;
            html += '<span class="sec-count">' + ssMeta.active + '/' + ssMeta.count + '</span>';
            html += '<span class="expand-arrow">' + arrow + '</span></button>';
        }} else {{
            let isActive = state.activeSector === sid ? ' active' : '';
            html += '<button class="sec-tab' + isActive + '" data-sector="' + sid + '">';
            html += sd.icon + ' ' + sd.name;
            html += '<span class="sec-count">' + (meta.active||0) + '/' + meta.count + '</span></button>';
        }}
    }}
    $('#secTabs').html(html);
    renderSubSecTabs();
}}

function renderSubSecTabs() {{
    let ssId = state.expandedSuperSector;
    if (!ssId) {{ $('#subSecTabs').hide(); return; }}
    let ss = superSectorDefs[ssId];
    let html = '';
    for (let sid of ss.sub_sectors) {{
        let sd = sectorDefs[sid];
        let meta = sectorMeta[sid];
        if (!meta || meta.count === 0) continue;
        let isActive = state.activeSector === sid ? ' active' : '';
        html += '<button class="sec-tab sub-sec-tab' + isActive + '" data-sector="' + sid + '">';
        html += sd.icon + ' ' + sd.name;
        html += '<span class="sec-count">' + (meta.active||0) + '/' + meta.count + '</span></button>';
    }}
    $('#subSecTabs').html(html).show();
}}

function renderSummary() {{
    let html = '';
    let sec = state.activeSector;
    if (sec === 'ALL') {{
        let metas = Object.values(sectorMeta);
        let totalCount  = metas.reduce((s,m) => s+(m.count||0), 0);
        let totalActive = metas.reduce((s,m) => s+(m.active||0), 0);
        let totalLegacy = metas.reduce((s,m) => s+(m.legacy||0), 0);
        html += '<div class="stat-card"><div class="stat-value text-white">' + totalCount + '</div><div class="stat-label">ETFs</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-green-400">' + totalActive + '</div><div class="stat-label">Active</div></div>';
        if (_isAdmin) html += '<div class="stat-card"><div class="stat-value text-red-400">' + totalLegacy + '</div><div class="stat-label">Legacy</div></div>';
    }} else if (sec && sec.startsWith('SS_')) {{
        let ssId = sec.slice(3);
        let ssMeta = getSuperSectorMeta(ssId);
        let ss = superSectorDefs[ssId] || {{}};
        html += '<div class="stat-card"><div class="stat-value text-white">' + ssMeta.count + '</div><div class="stat-label">ETFs</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-green-400">' + ssMeta.active + '</div><div class="stat-label">Active</div></div>';
        if (_isAdmin) html += '<div class="stat-card"><div class="stat-value text-red-400">' + ssMeta.legacy + '</div><div class="stat-label">Legacy</div></div>';
        html += '<div class="stat-card" style="min-width:120px"><div class="stat-value text-yellow-300 text-sm">' + (ss.anchor||'—') + '</div><div class="stat-label">Anchor</div></div>';
    }} else {{
        let meta = sectorMeta[sec] || {{}};
        let sd = sectorDefs[sec] || {{}};
        html += '<div class="stat-card"><div class="stat-value text-white">' + (meta.count||0) + '</div><div class="stat-label">ETFs</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-green-400">' + (meta.active||0) + '</div><div class="stat-label">Active</div></div>';
        if (_isAdmin) html += '<div class="stat-card"><div class="stat-value text-red-400">' + (meta.legacy||0) + '</div><div class="stat-label">Legacy</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-blue-300">' + (meta.avg_cagr > 0 ? '+' : '') + (meta.avg_cagr||0).toFixed(1) + '%</div><div class="stat-label">Avg CAGR</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-gray-300">' + (meta.avg_vol||0).toFixed(1) + '%</div><div class="stat-label">Avg Vol</div></div>';
        html += '<div class="stat-card"><div class="stat-value text-purple-400">' + (meta.avg_sortino||0).toFixed(2) + '</div><div class="stat-label">Avg Sortino</div></div>';
        html += '<div class="stat-card" style="min-width:120px"><div class="stat-value text-yellow-300 text-sm">' + (sd.anchor||'—') + '</div><div class="stat-label">Anchor</div></div>';
    }}
    $('#summaryCards').html(html);
}}

function loadSector(sectorId) {{
    state.activeSector = sectorId;
    // 슈퍼섹터 소속 섹터를 직접 클릭하면 해당 슈퍼섹터를 자동 확장
    if (sectorId && !sectorId.startsWith('SS_') && sectorId !== 'ALL') {{
        let sd = sectorDefs[sectorId];
        if (sd && sd.super_sector) {{
            state.expandedSuperSector = sd.super_sector;
        }} else {{
            state.expandedSuperSector = null;
        }}
    }}
    renderSectorTabs();
    renderSummary();
    let data;
    if (sectorId === 'ALL') {{
        data = Object.keys(allData).reduce(function(acc, k) {{ return acc.concat(allData[k]); }}, []);
    }} else if (sectorId && sectorId.startsWith('SS_')) {{
        let ssId = sectorId.slice(3);
        let ss = superSectorDefs[ssId];
        data = ss ? ss.sub_sectors.reduce(function(acc, sid) {{ return acc.concat(allData[sid] || []); }}, []) : [];
    }} else {{
        data = allData[sectorId] || [];
    }}
    table.clear().rows.add(data).draw();
    if (typeof applyHearts === 'function') applyHearts();
}}

function loadSuperSector(ssId) {{
    state.activeSector = 'SS_' + ssId;
    state.expandedSuperSector = ssId;
    renderSectorTabs();
    renderSummary();
    let ss = superSectorDefs[ssId];
    let data = ss ? ss.sub_sectors.flatMap(sid => allData[sid] || []) : [];
    table.clear().rows.add(data).draw();
    if (typeof applyHearts === 'function') applyHearts();
}}

// ── 토스트 알림 (전역) ────────────────────────────────────
let _toastTimer = null;
function showToast(msg, durationMs) {{
    let el = document.getElementById('r-toast');
    if (!el) {{
        el = document.createElement('div');
        el.id = 'r-toast';
        el.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#1e293b;color:#e2e8f0;padding:9px 18px;border-radius:10px;font-size:0.85rem;border:1px solid rgba(255,255,255,0.12);box-shadow:0 4px 20px rgba(0,0,0,0.5);z-index:9999;pointer-events:none;transition:opacity 0.3s;opacity:0;white-space:nowrap;';
        document.body.appendChild(el);
    }}
    if (_toastTimer) clearTimeout(_toastTimer);
    el.textContent = msg;
    el.style.opacity = '1';
    _toastTimer = setTimeout(function() {{ el.style.opacity = '0'; }}, durationMs || 3000);
}}

function initDashboard() {{
    renderACTabs();
    renderSectorTabs();
    renderSummary();

    table = $('#masterTable').DataTable({{
        data: Object.keys(allData).reduce(function(acc, k) {{ return acc.concat(allData[k]); }}, []),
        pageLength: 50,
        deferRender: true,
        lengthMenu: [[25, 50, 100, 200, -1], [25, 50, 100, 200, "All"]],
        order: [],
        columns: [
            {{
                data: null, orderable: false, searchable: false,
                className: 'text-center',
                render: function(d, type, row) {{
                    if (type !== 'display') return '';
                    let checked = selectedTickers.has(row.ticker) ? ' checked' : '';
                    return '<input type="checkbox" class="row-cb"' + checked + ' data-ticker="' + row.ticker + '">';
                }}
            }},
            {{
                data: null, orderable: false, searchable: false,
                className: 'text-right text-gray-600',
                render: function(d, type, row, meta) {{
                    if (type !== 'display') return meta.row + meta.settings._iDisplayStart;
                    return '<span style="font-size:0.75rem">' + (meta.row + meta.settings._iDisplayStart + 1) + '</span>';
                }}
            }},
            {{
                data: 'ticker', className: 'text-left font-semibold',
                render: function(d, type, row) {{
                    if (type !== 'display') return d;
                    let isMine = myPortfolio.includes(d);
                    let cls = isMine ? 'text-yellow-400 text-base' : 'text-blue-300';
                    let h = '<button class="star-btn" data-like="' + d + '" title="좋아요">♡</button>';
                    h += '<span class="'+cls+'">'+d+'</span>';
                    if (row.short_history) h += '<span class="badge-short" title="상장 3년 미만">짧은연혁</span>';
                    return h;
                }}
            }},
            {{
                data: 'name', className: 'text-left text-xs text-gray-400',
                render: function(d, type, row) {{
                    if (type !== 'display') return d;
                    let h = '<div class="leading-tight">'+d+'</div>';
                    if (myPortfolio.includes(row.ticker)) {{
                        h += '<div class="mt-1"><span class="mine-badge">MY</span></div>';
                    }}
                    return h;
                }}
            }},
            {{ data: 'rank', render: function(d,t){{ return t==='display'?(d===9999?'-':d):d; }} }},
            {{ data: 'aum', render: function(d,t){{ return t==='display'?formatMCap(d):d; }} }},
            {{ data: 'r_anchor', render: function(d,t) {{
                if(t!=='display') return d;
                let c = d >= 0.70 ? 'text-pink-400 font-bold' : (d <= -0.3 ? 'text-green-400 font-bold' : 'text-gray-400');
                return '<span class="'+c+'">'+d.toFixed(2)+'</span>';
            }} }},
            {{ data: 'smh_corr', defaultContent: null, render: function(d,t) {{
                if(t!=='display') return (d===null||d===undefined) ? -9999 : d;
                if(d===null||d===undefined) return '<span class="text-gray-700">–</span>';
                let c = d >= 0.70 ? 'text-violet-400 font-bold' : (d <= -0.3 ? 'text-green-400 font-bold' : 'text-gray-400');
                return '<span class="'+c+'">'+d.toFixed(2)+'</span>';
            }} }},
            {{ data: 'z_score', render: function(d,t,row) {{
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : d;
                let c = d <= -1.5 ? 'value-down font-bold' : (d >= 2.0 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="'+c+'">'+d.toFixed(2)+'</span>';
            }} }},
            {{ data: 'ma200_pct', render: function(d,t,row) {{
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : d;
                let c = d <= -10 ? 'value-down font-bold' : (d >= 15 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="'+c+'">'+(d>0?'+':'')+d.toFixed(1)+'%</span>';
            }} }},
            {{ data: 'rsi', defaultContent: null, render: function(d,t,row) {{
                if(d === null || d === undefined) return t==='display' ? '<span class="text-gray-600">-</span>' : -1;
                if(t!=='display') return d;
                let c = d <= 30 ? 'value-down font-bold' : (d >= 70 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="'+c+'">'+d.toFixed(0)+'</span>';
            }} }},
            {{ data: 'range_52w', defaultContent: null, render: function(d,t,row) {{
                if(d === null || d === undefined) return t==='display' ? '<span class="text-gray-600">-</span>' : -1;
                if(t!=='display') return d;
                let c = d <= 20 ? 'value-down font-bold' : (d >= 80 ? 'value-up font-bold' : 'text-gray-500');
                return '<span class="'+c+'">'+d.toFixed(0)+'%</span>';
            }} }},
            {{ data: 'mdd_52w', render: function(d,t,row) {{
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : d;
                let c = d <= -20 ? 'value-down font-bold' : 'text-gray-500';
                return '<span class="'+c+'">'+d.toFixed(1)+'%</span>';
            }} }},
            {{ data: 'cagr', render: function(d,t,row) {{
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : (d||0);
                return '<span class="text-gray-300 font-semibold">'+(d>0?'+':'')+d.toFixed(1)+'%</span>';
            }} }},
            {{ data: 'vol', render: function(d,t,row) {{
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : (d||0);
                return '<span class="text-gray-500">'+d.toFixed(1)+'%</span>';
            }} }},
            {{ data: 'sortino', render: function(d,t,row) {{
                if(row.short_history && t==='display') return '<span class="text-gray-600">-</span>';
                if(t!=='display') return row.short_history ? -999999 : (d===null?-999999:d);
                let c = d > 1.2 ? 'text-purple-400 font-bold' : 'text-gray-500';
                return '<span class="'+c+'">'+d.toFixed(2)+'</span>';
            }} }},
            {{ data: 'div_yield', render: function(d,t) {{
                if(t!=='display') return d==null ? -1 : d;
                if(d==null) return '<span class="text-gray-600">—</span>';
                let c = d >= 3 ? 'text-green-400 font-bold' : d >= 1 ? 'text-green-300' : 'text-gray-500';
                return '<span class="'+c+'">'+d.toFixed(2)+'%</span>';
            }} }},
            {{ data: 'inception', className: 'text-xs text-gray-600', render: function(d, t) {{
                if(t !== 'display') return d || '';
                if(!d || d==='1900-01-01') return '-';
                return d.substring(2);
            }} }},
            {{ data: 'is_legacy', render: function(d,t,row) {{
                if(t!=='display') return d ? 1 : 0;
                let out = '';
                if(!d) {{
                    out = '<span class="badge-active">Active</span>';
                }} else {{
                    let detail = (row.legacy_detail||[]).join(' / ');
                    let badge = row._user_override
                        ? '<span class="badge-user-legacy">User Legacy</span>'
                        : '<span class="badge-legacy">Legacy</span>';
                    out = badge + (detail ? '<div class="text-xs text-orange-400 mt-0.5 opacity-80">'+detail+'</div>' : '');
                }}
                if(row._user_sector) {{
                    let sd = sectorDefs[row._user_sector] || {{}};
                    out += '<div style="margin-top:2px"><span class="badge-user-sector">'+(sd.icon||'')+'&nbsp;'+(sd.name||row._user_sector)+'</span></div>';
                }}
                return out;
            }} }}
        ],
        rowCallback: function(row, data) {{
            if (data.is_legacy) $(row).addClass('row-legacy');
            else $(row).removeClass('row-legacy');
            if (selectedTickers.has(data.ticker)) $(row).addClass('row-selected');
            else $(row).removeClass('row-selected');
        }},
        drawCallback: function() {{
            if (typeof applyHearts === 'function') applyHearts();
        }}
    }});

    // Custom filter
    $.fn.dataTable.ext.search.push(function(settings, searchData, dataIndex) {{
        let row = settings.aoData[dataIndex]._aData;
        if (state.hideLegacy && row.is_legacy) return false;
        if (state.hideShort && row.short_history) return false;
        if (state.minAum > 0 && row.aum < state.minAum * 1e6) return false;
        if (state.minSortino > -999 && !row.short_history) {{
            if (row.sortino < state.minSortino) return false;
        }}
        return true;
    }});

    // Event: Asset Class tab click
    $(document).on('click', '.ac-tab', function() {{
        state.activeAC = $(this).data('ac');
        state.expandedSuperSector = null;
        renderACTabs();
        if (state.activeAC === 'ALL') {{
            loadSector('ALL');
        }} else {{
            let sectors = (acSectors[state.activeAC] || []).sort();
            let firstWithData = sectors.find(s => sectorMeta[s] && sectorMeta[s].count > 0);
            if (firstWithData) loadSector(firstWithData);
            else renderSectorTabs();
        }}
    }});

    // Event: Super-sector tab click (슈퍼섹터 탭 → 서브탭 토글)
    $(document).on('click', '.super-sec-tab', function() {{
        let ssId = $(this).data('supersec');
        if (state.expandedSuperSector === ssId) {{
            // 이미 열려 있으면 닫고 전체 보기
            state.expandedSuperSector = null;
            loadSector('ALL');
        }} else {{
            loadSuperSector(ssId);
        }}
    }});

    // Event: Sector tab click (서브섹터 탭 포함)
    $(document).on('click', '.sec-tab:not(.super-sec-tab)', function() {{
        loadSector($(this).data('sector'));
    }});

    // Event: Filters
    $('#filterLegacy').on('change', function() {{ state.hideLegacy = this.checked; table.draw(); }});
    $('#filterShort').on('change', function() {{ state.hideShort = this.checked; table.draw(); }});
    $('#filterAum').on('input', function() {{ state.minAum = parseFloat(this.value) || 0; table.draw(); }});
    $('#filterSortino').on('input', function() {{
        let v = parseFloat(this.value);
        state.minSortino = isNaN(v) ? -999 : v;
        table.draw();
    }});

    // ── 체크박스 이벤트 ───────────────────────────────
    window.updateFAB = function updateFAB() {{
        let n = selectedTickers.size;
        $('#fab-count').text(n);
        n > 0 ? $('#fab').show() : $('#fab').hide();
        // 전체선택 체크박스 상태 동기화
        let visibleTickers = [];
        table.rows({{ filter: 'applied', page: 'current' }}).every(function() {{
            visibleTickers.push(this.data().ticker);
        }});
        let allChecked = visibleTickers.length > 0 && visibleTickers.every(t => selectedTickers.has(t));
        $('#select-all-cb').prop('checked', allChecked);
    }}

    // 개별 체크박스
    $('#masterTable').on('change', 'input.row-cb', function() {{
        let ticker = $(this).data('ticker');
        if (this.checked) selectedTickers.add(ticker);
        else selectedTickers.delete(ticker);
        let row = table.row($(this).closest('tr'));
        if (this.checked) $(row.node()).addClass('row-selected');
        else $(row.node()).removeClass('row-selected');
        updateFAB();
    }});

    // 전체 선택/해제
    $('#select-all-cb').on('change', function() {{
        let checked = this.checked;
        table.rows({{ filter: 'applied', page: 'current' }}).every(function() {{
            let d = this.data();
            if (checked) selectedTickers.add(d.ticker);
            else selectedTickers.delete(d.ticker);
            if (checked) $(this.node()).addClass('row-selected');
            else $(this.node()).removeClass('row-selected');
        }});
        $('input.row-cb').prop('checked', checked);
        updateFAB();
    }});

    // 페이지/정렬/필터 변경 후 전체선택 체크박스 상태 갱신
    table.on('draw', function() {{ updateFAB(); }});

    // ── FAB 액션 ─────────────────────────────────────
    function applyLegacyAction(setLegacy) {{
        if (!_isAdmin || selectedTickers.size === 0) return;
        let ov = getUserOverrides();
        selectedTickers.forEach(function(ticker) {{
            // 섹터 오버라이드가 있으면 유지한 채 is_legacy만 업데이트
            if (!ov[ticker]) ov[ticker] = {{}};
            ov[ticker].is_legacy = setLegacy;
            const found = findETFAnywhere(ticker);
            if (found) {{
                found.etf.is_legacy      = setLegacy;
                found.etf._user_override = true;
                found.etf.legacy_detail  = setLegacy ? ['사용자 직접 지정'] : [];
                found.etf.legacy_reasons = setLegacy ? ['user_override'] : [];
            }}
        }});
        saveUserOverrides(ov);
        recalcSectorMeta();
        renderSectorTabs();
        renderSummary();
        selectedTickers.clear();
        table.rows().invalidate('data').draw(false);
        $('#select-all-cb').prop('checked', false);
        updateFAB();
    }}

    // ── 카테고리 이동 ──────────────────────────────────
    function buildSectorModal() {{
        // 선택된 ETF들의 현재 섹터 수집 (단일이면 하이라이트)
        const curSectors = new Set();
        selectedTickers.forEach(function(tk) {{
            const found = findETFAnywhere(tk);
            if (found) curSectors.add(found.sid);
        }});
        $('#modal-sel-info').text(selectedTickers.size + '개 종목 → 이동할 카테고리를 선택하세요');
        const ordered = Object.entries(acDefs).sort((a,b) => a[1].order - b[1].order);
        let html = '';
        for (const [ac, acDef] of ordered) {{
            const sids = (acSectors[ac] || []).sort();
            if (!sids.length) continue;
            html += '<div class="smg">' + acDef.icon + ' ' + acDef.name + '</div>';
            html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-bottom:4px">';
            for (const sid of sids) {{
                const sd = sectorDefs[sid];
                if (!sd) continue;
                const isCur = curSectors.size === 1 && curSectors.has(sid);
                html += '<button class="smb' + (isCur ? ' cur' : '') + '" data-sid="' + sid + '">';
                html += '<span style="font-size:1rem">' + (sd.icon||'') + '</span>';
                html += '<div><div style="font-weight:600;font-size:0.8rem">' + sd.name + '</div>';
                html += '<div style="font-size:0.68rem;color:#475569">' + (sd.name_en||'') + '</div></div>';
                html += '</button>';
            }}
            html += '</div>';
        }}
        $('#sector-modal-body').html(html);
    }}

    function applySectorMove(newSectorId) {{
        if (!newSectorId || selectedTickers.size === 0) return;
        const tickersToRecompute = [];
        let ov = getUserOverrides();
        selectedTickers.forEach(function(ticker) {{
            const found = findETFAnywhere(ticker);
            if (!found) return;
            const {{ etf, sid: oldSid }} = found;
            if (!ov[ticker]) ov[ticker] = {{}};
            if (oldSid === newSectorId) {{
                // 이미 이 섹터 → 섹터 오버라이드 해제
                delete ov[ticker].sector;
                delete ov[ticker].r_anchor;
                delete etf._user_sector;
                delete etf._original_sector;
                if (!Object.keys(ov[ticker]).length) delete ov[ticker];
                return;
            }}
            tickersToRecompute.push(ticker);
            // allData에서 이동
            allData[oldSid] = allData[oldSid].filter(e => e.ticker !== ticker);
            etf._user_sector     = newSectorId;
            etf._original_sector = etf._build_sector; // Store the build-time original sector
            if (!allData[newSectorId]) allData[newSectorId] = [];
            allData[newSectorId].push(etf);
            // localStorage 저장 (기존 is_legacy 보존)
            ov[ticker].sector = newSectorId;
        }});
        saveUserOverrides(ov);
        recalcSectorMeta();
        renderSectorTabs();
        renderSummary();
        selectedTickers.clear();
        $('#sector-modal').removeClass('show');
        loadSector(state.activeSector);
        updateFAB();
        if (tickersToRecompute.length) recomputeRanchorsAsync(tickersToRecompute, newSectorId);
    }}

    // ── 브라우저-사이드 r_anchor 재계산 유틸 ─────────────────────────────
    function _sleep(ms) {{ return new Promise(r => setTimeout(r, ms)); }}

    function _pearson(xs, ys) {{
        const n = xs.length;
        if (n < 2) return NaN;
        let mx = 0, my = 0;
        for (let i = 0; i < n; i++) {{ mx += xs[i]; my += ys[i]; }}
        mx /= n; my /= n;
        let num = 0, dx2 = 0, dy2 = 0;
        for (let i = 0; i < n; i++) {{
            const dx = xs[i] - mx, dy = ys[i] - my;
            num += dx * dy; dx2 += dx * dx; dy2 += dy * dy;
        }}
        return (dx2 && dy2) ? num / Math.sqrt(dx2 * dy2) : NaN;
    }}

    function _pairwiseReturns(pA, pB) {{
        const dates = Object.keys(pA).filter(d => d in pB).sort();
        const rA = [], rB = [];
        for (let i = 1; i < dates.length; i++) {{
            const a0 = pA[dates[i-1]], a1 = pA[dates[i]];
            const b0 = pB[dates[i-1]], b1 = pB[dates[i]];
            if (a0 && a1 && b0 && b1) {{
                rA.push((a1 - a0) / a0);
                rB.push((b1 - b0) / b0);
            }}
        }}
        return [rA, rB];
    }}

    function _calcCorr(pA, pB) {{
        const [rA, rB] = _pairwiseReturns(pA, pB);
        if (rA.length < 24) return null;
        const c = _pearson(rA, rB);
        return isFinite(c) ? Math.round(c * 10000) / 10000 : null;
    }}

    function _makeYfUrls(ticker) {{
        const tk = encodeURIComponent(ticker);
        const yf1 = 'https://query1.finance.yahoo.com/v8/finance/chart/' + tk + '?range=max&interval=1mo&includeAdjustedClose=true';
        return [
            '/api/yf?ticker=' + tk + '&range=max&interval=1mo',
            yf1,
            'https://query2.finance.yahoo.com/v8/finance/chart/' + tk + '?range=max&interval=1mo&includeAdjustedClose=true',
            'https://corsproxy.io/?' + encodeURIComponent(yf1),
        ];
    }}

    function _parseYfMonthly(data) {{
        const result = data && data.chart && data.chart.result && data.chart.result[0];
        if (!result) return null;
        const ts  = result.timestamp;
        const adj = (result.indicators && result.indicators.adjclose && result.indicators.adjclose[0] && result.indicators.adjclose[0].adjclose)
                 || (result.indicators && result.indicators.quote && result.indicators.quote[0] && result.indicators.quote[0].close);
        if (!ts || !adj) return null;
        const prices = {{}};
        for (let i = 0; i < ts.length; i++) {{
            if (adj[i] != null) {{
                const d = new Date(ts[i] * 1000);
                prices[d.getUTCFullYear() + '-' + String(d.getUTCMonth() + 1).padStart(2, '0')] = adj[i];
            }}
        }}
        return Object.keys(prices).length >= 3 ? prices : null;
    }}

    async function _fetchYfMonthly(ticker) {{
        for (const url of _makeYfUrls(ticker)) {{
            for (let attempt = 0; attempt < 2; attempt++) {{
                try {{
                    const r = await fetch(url);
                    if (r.status === 429) {{ await _sleep(3000 * (attempt + 1)); continue; }}
                    if (!r.ok) break;
                    const prices = _parseYfMonthly(await r.json());
                    if (prices) return prices;
                    break;
                }} catch(e) {{ await _sleep(500); }}
            }}
        }}
        return null;
    }}

    async function recomputeRanchorsAsync(tickers, newSectorId) {{
        const anchor = (sectorDefs[newSectorId] || {{}}).anchor;
        if (!anchor || anchor === '—') return;
        const tickerList = Array.isArray(tickers) ? tickers : Array.from(tickers);
        if (!tickerList.length) return;
        showToast('r_anchor 재계산 중… 앵커: ' + anchor + ' / ' + tickerList.length + '종목', 60000);
        const anchorPrices = await _fetchYfMonthly(anchor);
        if (!anchorPrices) {{
            showToast('앵커(' + anchor + ') 가격 조회 실패', 4000);
            return;
        }}
        let ok = 0;
        const ov = getUserOverrides();
        for (const ticker of tickerList) {{
            const found = findETFAnywhere(ticker);
            if (!found) continue;
            const prices = await _fetchYfMonthly(ticker);
            if (!prices) continue;
            const corr = _calcCorr(anchorPrices, prices);
            if (corr === null) continue;
            found.etf.r_anchor = corr;
            if (!ov[ticker]) ov[ticker] = {{}};
            ov[ticker].r_anchor = corr;
            ok++;
            await _sleep(150);
        }}
        saveUserOverrides(ov);
        if (ok > 0 && typeof table !== 'undefined') table.rows().invalidate('data').draw(false);
        showToast('r_anchor 재계산 완료 (' + ok + '/' + tickerList.length + '종목)', 4000);
    }}

    $('#fab-btn-legacy').on('click', function() {{ applyLegacyAction(true); }});
    $('#fab-btn-unlegacy').on('click', function() {{ applyLegacyAction(false); }});
    $('#fab-btn-move').on('click', function() {{
        if (selectedTickers.size === 0) return;
        buildSectorModal();
        $('#sector-modal').addClass('show');
    }});
    $('#sector-modal-close').on('click', function() {{ $('#sector-modal').removeClass('show'); }});
    $('#sector-modal').on('click', function(e) {{ if (e.target === this) $(this).removeClass('show'); }});
    $(document).on('click', '#sector-modal-body .smb', function() {{
        applySectorMove($(this).data('sid'));
    }});
    $('#fab-btn-clear').on('click', function() {{
        selectedTickers.clear();
        $('input.row-cb').prop('checked', false);
        table.rows().every(function() {{ $(this.node()).removeClass('row-selected'); }});
        updateFAB();
    }});

    // ── 실행취소 / 초기화 ─────────────────────────────
}}

$(document).ready(function() {{
    fetch('/etf_data.json')
        .then(function(r) {{ return r.json(); }})
        .then(function(d) {{
            sectorMeta = d.sectorMeta;
            allData = d.allData;
            // 빌드 기본값 스냅샷 저장
            for (var sid in allData) {{
                if (!allData.hasOwnProperty(sid)) continue;
                for (var i=0; i<allData[sid].length; i++) {{
                    allData[sid][i]._orig_legacy = allData[sid][i].is_legacy;
                }}
            }}

            // 1. 기본 상태(비로그인)로 데이터 즉시 준비
            stripLegacyForNonAdmin();
            try {{ applySmhCorr(); }} catch(e) {{}}
            try {{ recalcSectorMeta(); }} catch(e) {{}}

            // 2. 무조건 대시보드 먼저 렌더링!
            initDashboard();

            // 언어 전환기 리스너 (백그라운드에서 트리거됨)
            document.addEventListener('i18n:ready', function() {{
                renderACTabs();
                renderSectorTabs();
                renderSummary();
                updateFAB();
                if (typeof table !== 'undefined') table.rows().invalidate('data').draw(false);
            }});

            // 3. 백그라운드 비동기 작업 (Admin, i18n, 동기화)
            setTimeout(async function() {{
                try {{
                    await I18n.init();
                }} catch(e) {{}}

                try {{
                    const isAdmin = await detectAdmin();
                    applyAdminUI(isAdmin);

                    if (isAdmin) {{
                        // 어드민인 경우 원래 레거시 상태 복구
                        for (var sid in allData) {{
                            if (!allData.hasOwnProperty(sid)) continue;
                            for (var i=0; i<allData[sid].length; i++) {{
                                allData[sid][i].is_legacy = allData[sid][i]._orig_legacy;
                            }}
                        }}

                        let ov = getUserOverrides();
                        if (Object.keys(ov).length) applyOverridesToData(ov);
                        recalcSectorMeta();
                        renderSectorTabs();
                        renderSummary();
                        table.rows().invalidate('data').draw(false);
                    }}
                }} catch(authErr) {{
                    console.warn('[CORRYU] Background init failed:', authErr);
                }}
            }}, 50);
        }})
        .catch(function(err) {{
            console.error('[CORRYU] 데이터 파싱 실패:', err);
        }});
}});
</script>

<script src="/nav.js"></script>

<script>
// ═══════════════════════════════════════════════════════════════════════
// ❤️ 인기 종목 랭킹 (ticker_likes) — index.html only
// ═══════════════════════════════════════════════════════════════════════
(async function initTrending() {{
  if (typeof CorryuAuth === 'undefined' || !CorryuAuth.isConfigured) return;

  const section = document.getElementById('trending-section');
  if (!section) return;
  section.style.display = 'block';

  const TOP_N = 5;

  function rankItemHTML(rank, ticker, count, barPct, period) {{
    const medals = ['🥇','🥈','🥉'];
    const medal  = medals[rank - 1] || `<span style="font-size:.75rem;color:#475569;font-weight:800">${{rank}}</span>`;
    const barColor = period === 'weekly' ? 'rgba(251,191,36,0.6)' : 'rgba(168,85,247,0.6)';
    return `<a href="/etf-detail?ticker=${{encodeURIComponent(ticker)}}"
        style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:8px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04);text-decoration:none;transition:background .15s"
        onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='rgba(255,255,255,0.02)'">
      <span style="font-size:.9rem;flex-shrink:0;min-width:22px;text-align:center">${{medal}}</span>
      <span style="font-weight:800;font-size:.84rem;color:#e2e8f0;min-width:52px">${{ticker}}</span>
      <div style="flex:1;height:4px;background:rgba(255,255,255,0.05);border-radius:2px;overflow:hidden">
        <div style="height:100%;border-radius:2px;background:${{barColor}};width:${{barPct}}%"></div>
      </div>
      <span style="font-size:.75rem;font-weight:700;color:#64748b;flex-shrink:0">❤️ ${{count}}</span>
    </a>`;
  }}

  function emptyHTML() {{
    return `<div data-i18n="index.trending.empty" style="color:#334155;font-size:.78rem;text-align:center;padding:16px 0">아직 좋아요 데이터가 없습니다</div>`;
  }}

  async function loadWeekly() {{
    const el = document.getElementById('trending-weekly');
    const {{ data, error }} = await _sb.from('ticker_likes_weekly')
      .select('ticker,weekly_likes')
      .order('weekly_likes', {{ ascending: false }})
      .limit(TOP_N);
    if (error || !data || data.length === 0) {{ el.innerHTML = emptyHTML(); return; }}
    const maxLikes = data[0].weekly_likes;
    el.innerHTML = data.map((row, i) => {{
      const pct = maxLikes > 0 ? Math.round((row.weekly_likes / maxLikes) * 100) : 0;
      return rankItemHTML(i + 1, row.ticker, row.weekly_likes, pct, 'weekly');
    }}).join('');
  }}

  async function loadMonthly() {{
    const el = document.getElementById('trending-monthly');
    const {{ data, error }} = await _sb.from('ticker_likes_monthly')
      .select('ticker,monthly_likes')
      .order('monthly_likes', {{ ascending: false }})
      .limit(TOP_N);
    if (error || !data || data.length === 0) {{ el.innerHTML = emptyHTML(); return; }}
    const maxLikes = data[0].monthly_likes;
    el.innerHTML = data.map((row, i) => {{
      const pct = maxLikes > 0 ? Math.round((row.monthly_likes / maxLikes) * 100) : 0;
      return rankItemHTML(i + 1, row.ticker, row.monthly_likes, pct, 'monthly');
    }}).join('');
  }}

  await Promise.all([loadWeekly(), loadMonthly()]);
  setInterval(() => {{ loadWeekly(); loadMonthly(); }}, 30 * 60 * 1000);
}})();
</script>


<script>
// ═══════════════════════════════════════════════════════════════════════
// ❤️ 좋아요 기능 — onAuthChange 기반으로 nav 인증 상태와 동기화
// ═══════════════════════════════════════════════════════════════════════
(function initLikes() {{
    if (typeof CorryuAuth === 'undefined' || !CorryuAuth.isConfigured) return;

    CorryuAuth.onAuthChange(async function(event, session) {{
        if (session && session.user) {{
            _currentUserId = session.user.id;
            var res = await _sb.from('ticker_likes').select('ticker').eq('user_id', _currentUserId);
            likedTickers = new Set();
            if (res.data) res.data.forEach(function(r) {{ likedTickers.add(r.ticker); }});
        }} else {{
            _currentUserId = null;
            likedTickers = new Set();
        }}
        applyHearts();
    }});
}})();

$(document).on('click', '.star-btn[data-like]', async function(e) {{
    e.stopPropagation();
    const ticker = this.dataset.like;
    if (!_currentUserId) {{
        showToast('로그인이 필요한 기능이에요', 2500);
        setTimeout(function() {{ window.location.href = '/login'; }}, 1200);
        return;
    }}
    const isLiked = likedTickers.has(ticker);
    if (isLiked) {{
        likedTickers.delete(ticker);
        await _sb.from('ticker_likes').delete().eq('ticker', ticker).eq('user_id', _currentUserId);
    }} else {{
        likedTickers.add(ticker);
        await _sb.from('ticker_likes').upsert({{ ticker: ticker, user_id: _currentUserId }});
    }}
    $(this).toggleClass('starred', likedTickers.has(ticker));
    $(this).text(likedTickers.has(ticker) ? '♥' : '♡');
}});
</script>
</body>
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
