"""공통 HTML 리포트 테마 — 다크 테마 CSS + HTML 골격"""

CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"

DARK_THEME_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, 'Pretendard', sans-serif; background: #0f1117; color: #e0e0e0; }
.container { max-width: 1400px; margin: 0 auto; padding: 24px; }
header { text-align: center; padding: 40px 0 24px; }
header h1 { font-size: 28px; font-weight: 700; color: #fff; }
header p { color: #888; margin-top: 8px; font-size: 14px; }

.positive { color: #22c55e; }
.negative { color: #ef4444; }

.section { background: #1a1d27; border-radius: 12px; padding: 24px; margin: 20px 0; }
.section h2 { font-size: 18px; color: #fff; margin-bottom: 16px; }
.summary-card { background: #1a1d27; border-radius: 12px; padding: 20px; }
.summary-card h3 { font-size: 14px; color: #aaa; margin-bottom: 8px; }

table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { background: #252830; color: #aaa; font-weight: 600; padding: 10px 12px; text-align: left; }
td { padding: 10px 12px; border-bottom: 1px solid #252830; }

.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }

footer { text-align: center; padding: 32px; color: #555; font-size: 12px; }
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
