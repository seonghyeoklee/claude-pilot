"""공통 HTML 리포트 테마 — 다크 테마 CSS + HTML 골격"""

CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"

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
