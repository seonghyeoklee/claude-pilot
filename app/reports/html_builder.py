"""4종 HTML 빌더 (daily/weekly/monthly/market)"""

from __future__ import annotations

import json

from app.report_theme import wrap_html
from app.reports.models import ReportSnapshot, ReportType


def build_report_html(snapshot: ReportSnapshot, context: dict | None = None) -> str:
    """Type-based dispatcher for report HTML generation."""
    ctx = context or {}
    if snapshot.report_type == ReportType.DAILY:
        return build_daily_html(snapshot, ctx.get("history", []))
    elif snapshot.report_type == ReportType.WEEKLY:
        return build_weekly_html(snapshot)
    elif snapshot.report_type == ReportType.MONTHLY:
        return build_monthly_html(snapshot)
    elif snapshot.report_type == ReportType.MARKET:
        return build_market_html(snapshot)
    return build_daily_html(snapshot, ctx.get("history", []))


# ── Helpers ──


def _sign(v: float) -> str:
    return "positive" if v >= 0 else "negative"


def _fmt(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:,.0f}"


def _pct(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"


def _summary_cards(snapshot: ReportSnapshot) -> str:
    return f"""
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap:12px; margin-bottom:24px;">
      <div class="summary-card">
        <h3>순자산</h3>
        <div style="font-size:24px; font-weight:700;">\u20a9{snapshot.net_asset:,.0f}</div>
      </div>
      <div class="summary-card">
        <h3>P&amp;L</h3>
        <div style="font-size:24px; font-weight:700;" class="{_sign(snapshot.daily_pnl)}">{_fmt(snapshot.daily_pnl)}원</div>
      </div>
      <div class="summary-card">
        <h3>수익률</h3>
        <div style="font-size:24px; font-weight:700;" class="{_sign(snapshot.daily_return_pct)}">{_pct(snapshot.daily_return_pct)}</div>
      </div>
      <div class="summary-card">
        <h3>승률</h3>
        <div style="font-size:24px; font-weight:700;">{snapshot.win_rate:.1f}%</div>
        <div style="font-size:12px; color:var(--text-secondary);">{snapshot.win_count}W / {snapshot.loss_count}L</div>
      </div>
      <div class="summary-card">
        <h3>시그널 / 주문</h3>
        <div style="font-size:24px; font-weight:700;">{snapshot.total_signals} / {snapshot.total_orders}</div>
        <div style="font-size:12px; color:var(--text-secondary);">매수 {snapshot.buy_count} / 매도 {snapshot.sell_count}</div>
      </div>
      <div class="summary-card">
        <h3>Best / Worst</h3>
        <div style="font-size:16px;"><span class="positive">{_fmt(snapshot.best_trade_pnl)}</span> / <span class="negative">{_fmt(snapshot.worst_trade_pnl)}</span></div>
      </div>
    </div>"""


# ── Daily ──


def build_daily_html(snapshot: ReportSnapshot, history: list[ReportSnapshot]) -> str:
    """Build daily HTML report (summary cards + cumulative return chart + symbol P&L)."""
    cards = _summary_cards(snapshot)

    # Cumulative return chart data (oldest first)
    chart_history = list(reversed(history)) if history else [snapshot]
    chart_labels = [s.period_key for s in chart_history]
    chart_returns = []
    cumulative = 0.0
    for s in chart_history:
        cumulative += s.daily_return_pct
        chart_returns.append(round(cumulative, 4))

    chart_labels_json = json.dumps(chart_labels)
    chart_data_json = json.dumps(chart_returns)

    chart_section = f"""
    <div class="section">
      <h2>누적 수익률 (최근 {len(chart_history)}일)</h2>
      <canvas id="cumReturnChart" style="max-height:280px;"></canvas>
    </div>"""

    chart_js = f"""
    const ctx = document.getElementById('cumReturnChart').getContext('2d');
    new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: {chart_labels_json},
        datasets: [{{
          label: '누적 수익률 (%)',
          data: {chart_data_json},
          borderColor: '#58a6ff',
          backgroundColor: 'rgba(88,166,255,0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
        }}]
      }},
      options: {{
        responsive: true,
        plugins: {{
          legend: {{ labels: {{ color: '#e5e7eb' }} }},
        }},
        scales: {{
          x: {{ ticks: {{ color: '#9ca3af' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
          y: {{
            ticks: {{ color: '#9ca3af', callback: v => v + '%' }},
            grid: {{ color: 'rgba(255,255,255,0.05)' }},
          }}
        }}
      }}
    }});"""

    # Symbol P&L table
    symbol_pnl = snapshot.raw_metrics.get("symbol_pnl", {})
    rows = ""
    for sym, pnl in sorted(symbol_pnl.items(), key=lambda x: x[1], reverse=True):
        rows += f'<tr><td>{sym}</td><td class="{_sign(pnl)}">{_fmt(pnl)}원</td></tr>\n'

    symbol_table = ""
    if symbol_pnl:
        symbol_table = f"""
    <div class="section">
      <h2>종목별 P&amp;L</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>종목</th><th>P&amp;L</th></tr></thead>
        <tbody>{rows}</tbody>
      </table></div>
    </div>"""

    # Analysis summary
    analysis_section = ""
    if snapshot.analysis_summary:
        analysis_section = f"""
    <div class="section">
      <h2>분석 요약</h2>
      <p style="color:var(--text-secondary); line-height:1.7;">{snapshot.analysis_summary}</p>
    </div>"""

    body = f"""
    <div class="container">
      <header>
        <h1>Daily Trading Report</h1>
        <p>{snapshot.period_key}</p>
      </header>
      {cards}
      {chart_section}
      {symbol_table}
      {analysis_section}
      <footer>Claude Pilot &mdash; Daily Trading Report</footer>
    </div>"""

    return wrap_html(
        f"Trading Report \u2014 {snapshot.period_key}",
        body,
        include_chartjs=True,
        extra_js=chart_js,
    )


# ── Weekly ──


def build_weekly_html(snapshot: ReportSnapshot) -> str:
    """Build weekly HTML report (summary + daily P&L bar chart + breakdown table)."""
    cards = _summary_cards(snapshot)

    daily_breakdown = snapshot.raw_metrics.get("daily_breakdown", [])

    # Daily P&L bar chart
    bar_labels = json.dumps([d["date"] for d in daily_breakdown])
    bar_data = json.dumps([d["pnl"] for d in daily_breakdown])
    bar_colors = json.dumps([
        "rgba(34,197,94,0.7)" if d["pnl"] >= 0 else "rgba(239,68,68,0.7)"
        for d in daily_breakdown
    ])

    chart_section = f"""
    <div class="section">
      <h2>일별 P&amp;L</h2>
      <canvas id="dailyPnlChart" style="max-height:280px;"></canvas>
    </div>"""

    chart_js = f"""
    const ctx = document.getElementById('dailyPnlChart').getContext('2d');
    new Chart(ctx, {{
      type: 'bar',
      data: {{
        labels: {bar_labels},
        datasets: [{{
          label: 'P&L (원)',
          data: {bar_data},
          backgroundColor: {bar_colors},
          borderRadius: 4,
        }}]
      }},
      options: {{
        responsive: true,
        plugins: {{
          legend: {{ labels: {{ color: '#e5e7eb' }} }},
        }},
        scales: {{
          x: {{ ticks: {{ color: '#9ca3af' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
          y: {{
            ticks: {{ color: '#9ca3af', callback: v => v.toLocaleString() + '원' }},
            grid: {{ color: 'rgba(255,255,255,0.05)' }},
          }}
        }}
      }}
    }});"""

    # Breakdown table
    breakdown_rows = ""
    for d in daily_breakdown:
        pnl = d.get("pnl", 0)
        ret = d.get("return_pct", 0)
        breakdown_rows += (
            f'<tr>'
            f'<td>{d["date"]}</td>'
            f'<td class="{_sign(pnl)}">{_fmt(pnl)}원</td>'
            f'<td class="{_sign(ret)}">{_pct(ret)}</td>'
            f'<td>{d.get("orders", 0)}</td>'
            f'<td>{d.get("win", 0)}W / {d.get("loss", 0)}L</td>'
            f'</tr>\n'
        )

    breakdown_table = f"""
    <div class="section">
      <h2>일별 상세</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>날짜</th><th>P&amp;L</th><th>수익률</th><th>주문</th><th>승/패</th></tr></thead>
        <tbody>{breakdown_rows if breakdown_rows else '<tr><td colspan="5" style="color:var(--text-secondary)">데이터 없음</td></tr>'}</tbody>
      </table></div>
    </div>"""

    period_label = f"{snapshot.period_start} ~ {snapshot.period_end}" if snapshot.period_start else snapshot.period_key

    body = f"""
    <div class="container">
      <header>
        <h1>Weekly Trading Report</h1>
        <p>{snapshot.period_key} ({period_label})</p>
        <p style="color:var(--text-tertiary); font-size:12px;">거래일 {snapshot.trading_days}일</p>
      </header>
      {cards}
      {chart_section}
      {breakdown_table}
      <footer>Claude Pilot &mdash; Weekly Trading Report</footer>
    </div>"""

    return wrap_html(
        f"Weekly Report \u2014 {snapshot.period_key}",
        body,
        include_chartjs=True,
        extra_js=chart_js,
    )


# ── Monthly ──


def build_monthly_html(snapshot: ReportSnapshot) -> str:
    """Build monthly HTML report (summary + daily P&L chart + calendar heatmap)."""
    cards = _summary_cards(snapshot)

    daily_breakdown = snapshot.raw_metrics.get("daily_breakdown", [])

    # Daily P&L line chart
    line_labels = json.dumps([d["date"] for d in daily_breakdown])
    line_data = json.dumps([d["pnl"] for d in daily_breakdown])

    # Cumulative return
    cum_data = []
    c = 0.0
    for d in daily_breakdown:
        c += d.get("return_pct", 0)
        cum_data.append(round(c, 4))
    cum_data_json = json.dumps(cum_data)

    chart_section = f"""
    <div class="section">
      <h2>일별 P&amp;L &amp; 누적 수익률</h2>
      <canvas id="monthlyChart" style="max-height:300px;"></canvas>
    </div>"""

    chart_js = f"""
    const ctx = document.getElementById('monthlyChart').getContext('2d');
    new Chart(ctx, {{
      type: 'bar',
      data: {{
        labels: {line_labels},
        datasets: [
          {{
            label: 'P&L (원)',
            data: {line_data},
            backgroundColor: {line_data}.map(v => v >= 0 ? 'rgba(34,197,94,0.6)' : 'rgba(239,68,68,0.6)'),
            borderRadius: 3,
            yAxisID: 'y',
          }},
          {{
            label: '누적 수익률 (%)',
            data: {cum_data_json},
            type: 'line',
            borderColor: '#58a6ff',
            backgroundColor: 'transparent',
            tension: 0.3,
            pointRadius: 2,
            yAxisID: 'y1',
          }}
        ]
      }},
      options: {{
        responsive: true,
        plugins: {{
          legend: {{ labels: {{ color: '#e5e7eb' }} }},
        }},
        scales: {{
          x: {{ ticks: {{ color: '#9ca3af', maxRotation: 45 }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
          y: {{
            position: 'left',
            ticks: {{ color: '#9ca3af', callback: v => v.toLocaleString() + '원' }},
            grid: {{ color: 'rgba(255,255,255,0.05)' }},
          }},
          y1: {{
            position: 'right',
            ticks: {{ color: '#58a6ff', callback: v => v + '%' }},
            grid: {{ display: false }},
          }}
        }}
      }}
    }});"""

    # Calendar heatmap (simple table)
    heatmap = _build_calendar_heatmap(daily_breakdown, snapshot.period_key)

    # Breakdown table
    breakdown_rows = ""
    for d in daily_breakdown:
        pnl = d.get("pnl", 0)
        ret = d.get("return_pct", 0)
        breakdown_rows += (
            f'<tr>'
            f'<td>{d["date"]}</td>'
            f'<td class="{_sign(pnl)}">{_fmt(pnl)}원</td>'
            f'<td class="{_sign(ret)}">{_pct(ret)}</td>'
            f'<td>\u20a9{d.get("net_asset", 0):,.0f}</td>'
            f'</tr>\n'
        )

    breakdown_table = f"""
    <div class="section">
      <h2>일별 상세</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>날짜</th><th>P&amp;L</th><th>수익률</th><th>순자산</th></tr></thead>
        <tbody>{breakdown_rows if breakdown_rows else '<tr><td colspan="4" style="color:var(--text-secondary)">데이터 없음</td></tr>'}</tbody>
      </table></div>
    </div>"""

    period_label = f"{snapshot.period_start} ~ {snapshot.period_end}" if snapshot.period_start else snapshot.period_key

    body = f"""
    <div class="container">
      <header>
        <h1>Monthly Trading Report</h1>
        <p>{snapshot.period_key} ({period_label})</p>
        <p style="color:var(--text-tertiary); font-size:12px;">거래일 {snapshot.trading_days}일</p>
      </header>
      {cards}
      {chart_section}
      {heatmap}
      {breakdown_table}
      <footer>Claude Pilot &mdash; Monthly Trading Report</footer>
    </div>"""

    return wrap_html(
        f"Monthly Report \u2014 {snapshot.period_key}",
        body,
        include_chartjs=True,
        extra_js=chart_js,
    )


def _build_calendar_heatmap(daily_breakdown: list[dict], period_key: str) -> str:
    """Build a simple calendar heatmap table for the month."""
    if not daily_breakdown:
        return ""

    # Map date -> pnl
    pnl_map = {d["date"]: d.get("pnl", 0) for d in daily_breakdown}

    # Parse period_key (YYYY-MM)
    try:
        year, month = int(period_key[:4]), int(period_key[5:7])
    except (ValueError, IndexError):
        return ""

    import calendar as cal

    first_weekday, num_days = cal.monthrange(year, month)
    # first_weekday: 0=Mon

    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    header = "".join(f"<th>{d}</th>" for d in weekdays)

    cells = ""
    # Pad first row
    cells += "<tr>"
    for i in range(first_weekday):
        cells += "<td></td>"

    day = 1
    col = first_weekday
    while day <= num_days:
        date_str = f"{year}-{month:02d}-{day:02d}"
        pnl = pnl_map.get(date_str)
        if pnl is not None:
            if pnl > 0:
                bg = "rgba(34,197,94,0.3)"
                color = "#22c55e"
            elif pnl < 0:
                bg = "rgba(239,68,68,0.3)"
                color = "#ef4444"
            else:
                bg = "rgba(255,255,255,0.05)"
                color = "var(--text-secondary)"
            cells += f'<td style="background:{bg}; text-align:center; cursor:default;" title="{date_str}: {_fmt(pnl)}원"><span style="color:var(--text-secondary); font-size:11px;">{day}</span><br><span style="color:{color}; font-size:10px;">{_fmt(pnl)}</span></td>'
        else:
            cells += f'<td style="text-align:center;"><span style="color:var(--text-tertiary); font-size:11px;">{day}</span></td>'

        col += 1
        if col == 7 and day < num_days:
            cells += "</tr><tr>"
            col = 0
        day += 1

    # Pad last row
    while col < 7:
        cells += "<td></td>"
        col += 1
    cells += "</tr>"

    return f"""
    <div class="section">
      <h2>캘린더 히트맵</h2>
      <div class="table-wrap"><table style="table-layout:fixed; min-width:320px;">
        <thead><tr>{header}</tr></thead>
        <tbody>{cells}</tbody>
      </table></div>
    </div>"""


# ── Market ──


def build_market_html(snapshot: ReportSnapshot) -> str:
    """Build market report HTML (portfolio vs market comparison)."""
    raw = snapshot.raw_metrics
    market_data = raw.get("market_data", {})

    cards = _summary_cards(snapshot)

    # Market indices
    indices_section = ""
    indices = market_data.get("indices", {})
    if indices:
        idx_rows = ""
        for name, data in indices.items():
            if isinstance(data, dict):
                val = data.get("close", data.get("value", 0))
                chg = data.get("change_pct", 0)
                idx_rows += f'<tr><td>{name}</td><td>{val:,.2f}</td><td class="{_sign(chg)}">{_pct(chg)}</td></tr>\n'
        if idx_rows:
            indices_section = f"""
    <div class="section">
      <h2>시장 지수</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>지수</th><th>종가</th><th>등락률</th></tr></thead>
        <tbody>{idx_rows}</tbody>
      </table></div>
    </div>"""

    # Sector analysis
    sector_section = ""
    sectors = market_data.get("sectors", {})
    if sectors:
        sec_rows = ""
        for name, data in sorted(sectors.items(), key=lambda x: x[1].get("change_pct", 0) if isinstance(x[1], dict) else 0, reverse=True):
            if isinstance(data, dict):
                chg = data.get("change_pct", 0)
                sec_rows += f'<tr><td>{name}</td><td class="{_sign(chg)}">{_pct(chg)}</td></tr>\n'
        if sec_rows:
            sector_section = f"""
    <div class="section">
      <h2>섹터별 등락률</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>섹터</th><th>등락률</th></tr></thead>
        <tbody>{sec_rows}</tbody>
      </table></div>
    </div>"""

    # Analysis summary
    analysis_section = ""
    if snapshot.analysis_summary:
        analysis_section = f"""
    <div class="section">
      <h2>시장 분석 요약</h2>
      <p style="color:var(--text-secondary); line-height:1.7;">{snapshot.analysis_summary}</p>
    </div>"""

    body = f"""
    <div class="container">
      <header>
        <h1>Market Report</h1>
        <p>{snapshot.period_key}</p>
      </header>
      {cards}
      {indices_section}
      {sector_section}
      {analysis_section}
      <footer>Claude Pilot &mdash; Market Report</footer>
    </div>"""

    return wrap_html(
        f"Market Report \u2014 {snapshot.period_key}",
        body,
        include_chartjs=False,
    )
