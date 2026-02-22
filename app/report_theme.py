"""공통 HTML 리포트 테마 — 다크 테마 CSS + HTML 골격"""

CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"

FAVICON_SVG = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'"
    " fill='none'%3E%3Crect x='1' y='1' width='38' height='38' rx='10' fill='%231a1b23'"
    " stroke='%2330363d' stroke-width='1'/%3E%3Cpath d='M15 14 L9 20 L15 26'"
    " stroke='%2358a6ff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'"
    " fill='none'/%3E%3Cpath d='M25 14 L31 20 L25 26' stroke='%2358a6ff' stroke-width='2'"
    " stroke-linecap='round' stroke-linejoin='round' fill='none'/%3E%3Cpath d='M20 12 L20 28'"
    " stroke='%23a78bfa' stroke-width='2' stroke-linecap='round'/%3E%3Cpath d='M16 16 L20 12"
    " L24 16' stroke='%23a78bfa' stroke-width='2' stroke-linecap='round'"
    " stroke-linejoin='round' fill='none'/%3E%3C/svg%3E"
)

# ── Mobile-first report CSS ──

MOBILE_REPORT_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:-apple-system,'Pretendard',sans-serif;
  background:#0f1117;color:#e2e8f0;
  -webkit-font-smoothing:antialiased;
  -webkit-text-size-adjust:100%;
}
.wrap{max-width:480px;margin:0 auto;padding:16px 16px 32px}

/* Color utilities */
.pos{color:#22c55e} .neg{color:#ef4444} .warn{color:#f59e0b}
.muted{color:#64748b} .blue{color:#3b82f6}

/* Header */
.hdr{text-align:center;padding:12px 0 16px}
.hdr-date{font-size:1.4rem;font-weight:800;color:#fff}
.hdr-sub{color:#64748b;font-size:0.78rem;margin-top:4px}
.hdr-badge{display:inline-block;background:#1e293b;color:#f59e0b;
  padding:4px 12px;border-radius:20px;font-size:0.72rem;font-weight:600;margin-top:10px}

/* Section */
.section{background:#1e293b;border-radius:16px;padding:18px;margin-bottom:12px}
.sec-title{font-size:0.92rem;font-weight:600;color:#f1f5f9;margin-bottom:10px;
  display:flex;align-items:center;gap:8px}
.sec-desc{color:#94a3b8;font-size:0.78rem;line-height:1.6;margin-bottom:12px}

/* Hero */
.hero{background:#1e293b;border-radius:16px;padding:20px;margin-bottom:12px;text-align:center}
.hero-label{color:#64748b;font-size:0.72rem}
.hero-pnl{font-size:2.6rem;font-weight:800;letter-spacing:-1px;line-height:1.1}
.hero-unit{font-size:1rem;font-weight:400;margin-left:2px}
.hero-row{display:flex;justify-content:center;gap:0;margin-top:14px}
.hero-item{flex:1;display:flex;flex-direction:column;align-items:center}
.hero-divider{width:1px;background:#334155;margin:0 4px}
.hi-label{color:#64748b;font-size:0.68rem;margin-bottom:2px}
.hi-val{font-size:0.92rem;font-weight:600}

/* Stat row (donut + nums) */
.stat-row{display:flex;gap:16px;align-items:center;background:#1e293b;
  border-radius:16px;padding:16px;margin-bottom:12px}
.stat-box{flex-shrink:0}
.stat-nums{flex:1}
.sn-main{font-size:1.8rem;font-weight:800;line-height:1}
.sn-label{font-size:0.75rem;color:#64748b;font-weight:400;margin-left:4px}
.sn-grid{display:flex;gap:12px;margin-top:6px}
.sn-item{font-size:0.78rem;color:#94a3b8;display:flex;align-items:center;gap:4px}
.sn-dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.sn-detail{display:flex;flex-direction:column;font-size:0.78rem}

/* Metric strip */
.metric-strip{display:flex;gap:8px;margin-bottom:12px}
.ms-card{flex:1;background:#1e293b;border-radius:12px;padding:12px;
  display:flex;flex-direction:column}
.ms-label{color:#64748b;font-size:0.68rem;margin-bottom:4px}
.ms-val{font-size:1.1rem;font-weight:700}
.ms-sub{color:#64748b;font-size:0.65rem;margin-top:2px}

/* Reason pills */
.pill-row{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.pill{display:flex;align-items:center;gap:6px;background:#1e293b;
  border-radius:20px;padding:6px 12px}
.pill-count{font-size:0.78rem;font-weight:600}
.pill-pnl{font-size:0.78rem;font-weight:600}
.reason-badge{color:#fff;padding:2px 7px;border-radius:4px;
  font-size:0.65rem;font-weight:600;white-space:nowrap}

/* Chart */
.chart-section{background:#1e293b;border-radius:12px;padding:16px;margin-bottom:12px}
.chart-wrap{height:180px;position:relative}
.chart-wrap-sm{height:140px;position:relative;margin-top:8px}

/* Symbol performance list */
.sym-list{margin-bottom:12px}
.sym-row{display:flex;align-items:center;padding:10px 12px;
  background:#1e293b;border-radius:10px;margin-bottom:6px}
.sym-name{flex:1;font-weight:600;font-size:0.85rem}
.sym-meta{color:#64748b;font-size:0.75rem;width:36px;text-align:center}
.sym-pnl{font-weight:700;font-size:0.88rem;width:80px;text-align:right}
.sym-rate{font-size:0.75rem;width:52px;text-align:right}
.tc-code{color:#64748b;font-size:0.68rem;font-weight:400;margin-left:6px}

/* Trade cards */
.trade-list{display:flex;flex-direction:column;gap:8px}
.trade-card{background:#1e293b;border-radius:12px;padding:14px 14px 10px;position:relative}
.tc-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.tc-name{font-weight:700;font-size:0.88rem}
.tc-pnl{font-size:1rem;font-weight:800}
.tc-bar-track{height:4px;background:#0f1117;border-radius:2px;margin-bottom:10px;overflow:hidden}
.tc-bar{height:100%;border-radius:2px;transition:width .3s}
.tc-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px 10px}
.tc-cell{display:flex;flex-direction:column}
.tc-label{color:#475569;font-size:0.62rem;text-transform:uppercase;letter-spacing:0.5px}
.tc-val{font-size:0.78rem;font-weight:500}

/* Data rows */
.data-row{display:flex;justify-content:space-between;align-items:center;
  padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04)}
.data-row:last-child{border:none}
.dr-left{display:flex;flex-direction:column}
.dr-name{font-size:0.82rem;font-weight:600}
.dr-sub{font-size:0.68rem;color:#64748b}
.dr-right{display:flex;align-items:center;gap:10px}
.dr-pnl{font-size:0.85rem;font-weight:700;min-width:70px;text-align:right}
.dr-rate{font-size:0.72rem;min-width:48px;text-align:right}

/* Comparison grid */
.cmp-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.cmp-card{background:#0f1117;border-radius:10px;padding:12px;display:flex;flex-direction:column}
.cmp-label{color:#64748b;font-size:0.65rem;margin-bottom:4px}
.cmp-val{font-size:1.05rem;font-weight:700}
.cmp-sub{color:#64748b;font-size:0.62rem;margin-top:2px}

/* Diagnostic cards */
.diag{border-left:3px solid;padding-left:14px;margin-bottom:14px}
.diag-warn{border-color:#f59e0b}
.diag-danger{border-color:#ef4444}
.diag-info{border-color:#3b82f6}
.diag-ok{border-color:#22c55e}
.diag-title{font-size:0.85rem;font-weight:700;margin-bottom:4px}
.diag-body{color:#94a3b8;font-size:0.75rem;line-height:1.55}
.diag-body strong{color:#e2e8f0}

/* Conclusion box */
.conclusion{background:linear-gradient(135deg,#1e293b 0%,#0f1117 100%);
  border:1px solid #334155;border-radius:16px;padding:20px;margin-top:4px}
.conclusion-title{font-size:1rem;font-weight:800;color:#fff;margin-bottom:10px}
.conclusion-body{color:#94a3b8;font-size:0.78rem;line-height:1.65}
.conclusion-body strong{color:#e2e8f0}

/* Watch tags */
.tag-row{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px}
.sym-tag{background:#252830;color:#94a3b8;padding:4px 10px;border-radius:6px;font-size:0.75rem}

/* Calendar heatmap */
.cal-table{width:100%;table-layout:fixed;border-collapse:collapse}
.cal-table th{color:#64748b;font-size:0.65rem;padding:4px 2px;text-align:center;font-weight:600}
.cal-table td{text-align:center;padding:6px 2px;border-radius:6px}
.cal-day{font-size:0.68rem;color:#94a3b8}
.cal-pnl{font-size:0.6rem;font-weight:600}

/* Footer */
.footer{text-align:center;padding:24px 0 8px;color:#334155;font-size:0.7rem}
""".strip()


def wrap_report_html(
    title: str,
    body: str,
    *,
    extra_css: str = "",
    extra_js: str = "",
    include_chartjs: bool = False,
) -> str:
    """Wrap body HTML in a mobile-first report shell."""
    chartjs_tag = f'<script src="{CHART_JS_CDN}"></script>' if include_chartjs else ""
    js_block = f"<script>\n{extra_js}\n</script>" if extra_js else ""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>{title}</title>
<link rel="icon" type="image/svg+xml" href="{FAVICON_SVG}">
{chartjs_tag}
<style>
{MOBILE_REPORT_CSS}
{extra_css}
</style>
</head>
<body>
{body}
{js_block}
</body>
</html>"""


# ── Legacy dashboard theme (keep for backward compat) ──

DARK_THEME_CSS = """
:root {
    --bg-page: #0f1117;
    --bg-card: #161b22;
    --bg-panel: #1c2128;
    --text-primary: #e5e7eb;
    --text-secondary: #9ca3af;
    --text-tertiary: #6b7280;
    --accent: #58a6ff;
    --border: rgba(255,255,255,0.08);
    --hover-overlay: rgba(255,255,255,0.04);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, 'Pretendard', sans-serif; background: var(--bg-page); color: var(--text-primary); }
.container { max-width: 1400px; margin: 0 auto; padding: 24px; }
header { text-align: center; padding: 40px 0 24px; }
header h1 { font-size: 28px; font-weight: 700; color: #fff; }
header p { color: var(--text-secondary); margin-top: 8px; font-size: 14px; }

.positive { color: #22c55e; }
.negative { color: #ef4444; }

.section { background: var(--bg-card); border-radius: 12px; padding: 24px; margin: 20px 0; border: 1px solid var(--border); }
.section h2 { font-size: 18px; color: #fff; margin-bottom: 16px; }
.summary-card { background: var(--bg-card); border-radius: 12px; padding: 20px; border: 1px solid var(--border); }
.summary-card h3 { font-size: 14px; color: var(--text-secondary); margin-bottom: 8px; }

table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { background: var(--bg-panel); color: var(--text-secondary); font-weight: 600; padding: 10px 12px; text-align: left; }
td { padding: 10px 12px; border-bottom: 1px solid var(--border); }

.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }

footer { text-align: center; padding: 32px; color: var(--text-tertiary); font-size: 12px; }

/* Focus-visible: keyboard only, not mouse */
*:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
*:focus:not(:focus-visible) { outline: none; }

/* ── Mobile ── */
@media (max-width: 768px) {
    .container { padding: 12px; }
    header { padding: 24px 0 16px; }
    header h1 { font-size: 22px; }
    .section { padding: 16px; margin: 12px 0; border-radius: 8px; }
    .section h2 { font-size: 16px; margin-bottom: 12px; }
    .summary-card { padding: 14px; border-radius: 8px; }
    .summary-card h3 { font-size: 12px; }
    table { font-size: 12px; }
    th, td { padding: 8px 6px; }
    footer { padding: 20px; font-size: 11px; }
    /* Horizontal scroll for wide tables */
    .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
}
@media (max-width: 480px) {
    .container { padding: 8px; }
    header h1 { font-size: 19px; }
    .section { padding: 12px; }
    th, td { padding: 6px 4px; white-space: nowrap; }
}
""".strip()


def wrap_html(
    title: str,
    body: str,
    *,
    extra_css: str = "",
    extra_js: str = "",
    include_chartjs: bool = False,
) -> str:
    chartjs_tag = f'<script src="{CHART_JS_CDN}"></script>' if include_chartjs else ""
    js_block = f"<script>\n{extra_js}\n</script>" if extra_js else ""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40' fill='none'%3E%3Crect x='1' y='1' width='38' height='38' rx='10' fill='%231a1b23' stroke='%2330363d' stroke-width='1'/%3E%3Cpath d='M15 14 L9 20 L15 26' stroke='%2358a6ff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' fill='none'/%3E%3Cpath d='M25 14 L31 20 L25 26' stroke='%2358a6ff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' fill='none'/%3E%3Cpath d='M20 12 L20 28' stroke='%23a78bfa' stroke-width='2' stroke-linecap='round'/%3E%3Cpath d='M16 16 L20 12 L24 16' stroke='%23a78bfa' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' fill='none'/%3E%3C/svg%3E">
{chartjs_tag}
<style>
{DARK_THEME_CSS}
{extra_css}
</style>
</head>
<body>
{body}
{js_block}
</body>
</html>"""
