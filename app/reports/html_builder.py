"""4종 HTML 빌더 (daily/weekly/monthly/market) — 모바일 퍼스트 프리미엄 디자인"""

from __future__ import annotations

import json

from app.report_theme import wrap_report_html
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
    if v > 0:
        return "pos"
    elif v < 0:
        return "neg"
    return "muted"


def _fmt(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:,.0f}"


def _pct(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"


def _fmt_invested(v: float) -> str:
    """Format invested amount in 만원 units."""
    man = v / 10000
    if man >= 1:
        return f"{man:,.0f}만원"
    return f"{v:,.0f}원"


def _weekday_ko(date_str: str) -> str:
    """Return Korean weekday from YYYY-MM-DD string."""
    days = ["월", "화", "수", "목", "금", "토", "일"]
    try:
        from datetime import date
        d = date.fromisoformat(date_str)
        return days[d.weekday()]
    except (ValueError, TypeError):
        return ""


# ── Daily ──


def build_daily_html(snapshot: ReportSnapshot, history: list[ReportSnapshot]) -> str:
    """Build premium daily report with hero, donut, charts, trade cards."""
    raw = snapshot.raw_metrics
    trades = raw.get("trades", [])
    symbol_pnl = raw.get("symbol_pnl", {})
    symbol_stats = raw.get("symbol_stats", {})
    reason_breakdown = raw.get("reason_breakdown", {})
    cum_timeline = raw.get("cum_pnl_timeline", [])
    total_invested = raw.get("total_invested", 0)
    avg_hold = raw.get("avg_hold_minutes", 0)
    avg_win = raw.get("avg_win", 0)
    avg_loss = raw.get("avg_loss", 0)
    draw_count = raw.get("draw_count", 0)

    weekday = _weekday_ko(snapshot.period_key)
    date_display = snapshot.period_key.replace("-", ".")
    if weekday:
        date_display += f" ({weekday})"
    num_symbols = len(snapshot.symbols_traded)

    # ── Header ──
    header = f"""
<div class="hdr">
  <div class="hdr-date">{date_display}</div>
  <div class="hdr-sub">{num_symbols}종목 · {snapshot.total_orders}건 매매</div>
</div>"""

    # ── Hero P&L ──
    pnl_cls = _sign(snapshot.daily_pnl)
    hero = f"""
<div class="hero">
  <div class="hero-label">오늘의 실현손익</div>
  <div class="hero-pnl {pnl_cls}">{_fmt(snapshot.daily_pnl)}<span class="hero-unit">원</span></div>
  <div class="hero-row">
    <div class="hero-item"><span class="hi-label">수익률</span><span class="hi-val {pnl_cls}">{_pct(snapshot.daily_return_pct)}</span></div>
    <div class="hero-divider"></div>
    <div class="hero-item"><span class="hi-label">투자금액</span><span class="hi-val">{_fmt_invested(total_invested)}</span></div>
    <div class="hero-divider"></div>
    <div class="hero-item"><span class="hi-label">매매</span><span class="hi-val">{snapshot.total_orders}건</span></div>
  </div>
</div>"""

    # ── Stat Row (donut + numbers) ──
    stat_row = f"""
<div class="stat-row">
  <div class="stat-box">
    <canvas id="donutChart" width="100" height="100"></canvas>
  </div>
  <div class="stat-nums">
    <div class="sn-main" style="color:#3b82f6">{snapshot.win_rate:.0f}%<span class="sn-label">승률</span></div>
    <div class="sn-grid">
      <div class="sn-item"><span class="sn-dot" style="background:#22c55e"></span>승 {snapshot.win_count}</div>
      <div class="sn-item"><span class="sn-dot" style="background:#ef4444"></span>패 {snapshot.loss_count}</div>
      <div class="sn-item"><span class="sn-dot" style="background:#475569"></span>무 {draw_count}</div>
    </div>
    <div class="sn-grid" style="margin-top:8px">
      <div class="sn-detail"><span class="hi-label">평균 수익</span><span class="pos">{_fmt(avg_win)}</span></div>
      <div class="sn-detail"><span class="hi-label">평균 손실</span><span class="neg">{_fmt(avg_loss)}</span></div>
    </div>
  </div>
</div>"""

    # ── Metric Strip ──
    # Find best/worst trade symbols
    best_sym = ""
    worst_sym = ""
    if trades:
        best_t = max(trades, key=lambda t: t["pnl"])
        worst_t = min(trades, key=lambda t: t["pnl"])
        best_sym = best_t["symbol"]
        worst_sym = worst_t["symbol"]
        best_ret = best_t.get("return_pct", 0)
        worst_ret = worst_t.get("return_pct", 0)

    metric_strip = f"""
<div class="metric-strip">
  <div class="ms-card">
    <span class="ms-label">최대 수익</span>
    <span class="ms-val pos">{_fmt(snapshot.best_trade_pnl)}</span>
    <span class="ms-sub">{best_sym} {_pct(best_ret) if trades else ''}</span>
  </div>
  <div class="ms-card">
    <span class="ms-label">최대 손실</span>
    <span class="ms-val neg">{_fmt(snapshot.worst_trade_pnl)}</span>
    <span class="ms-sub">{worst_sym} {_pct(worst_ret) if trades else ''}</span>
  </div>
  <div class="ms-card">
    <span class="ms-label">평균 보유</span>
    <span class="ms-val">{avg_hold}분</span>
  </div>
</div>"""

    # ── Reason Pills ──
    pills_html = ""
    sig = reason_breakdown.get("signal", {})
    fc = reason_breakdown.get("force_close", {})
    pills = []
    if sig.get("count", 0) > 0:
        sig_pnl_cls = _sign(sig["pnl"])
        pills.append(
            f'<div class="pill">'
            f'<span class="reason-badge" style="background:#3b82f6">시그널</span>'
            f'<span class="pill-count">{sig["count"]}건</span>'
            f'<span class="pill-pnl {sig_pnl_cls}">{_fmt(sig["pnl"])}</span>'
            f'</div>'
        )
    if fc.get("count", 0) > 0:
        fc_pnl_cls = _sign(fc["pnl"])
        pills.append(
            f'<div class="pill">'
            f'<span class="reason-badge" style="background:#6b7280">장마감</span>'
            f'<span class="pill-count">{fc["count"]}건</span>'
            f'<span class="pill-pnl {fc_pnl_cls}">{_fmt(fc["pnl"])}</span>'
            f'</div>'
        )
    if pills:
        pills_html = f'<div class="pill-row">{"".join(pills)}</div>'

    # ── Cumulative P&L Chart ──
    cum_chart = ""
    cum_js = ""
    if cum_timeline:
        cum_labels = json.dumps([c["time"] for c in cum_timeline])
        cum_data = json.dumps([c["cum_pnl"] for c in cum_timeline])
        final_pnl = cum_timeline[-1]["cum_pnl"]
        line_color = "#22c55e" if final_pnl >= 0 else "#ef4444"
        fill_color = "rgba(34,197,94,0.08)" if final_pnl >= 0 else "rgba(239,68,68,0.08)"
        cum_chart = """
<div class="chart-section">
  <div class="sec-title">누적 손익 추이</div>
  <div class="chart-wrap"><canvas id="cumChart"></canvas></div>
</div>"""
        cum_js = f"""
const cumCtx = document.getElementById('cumChart').getContext('2d');
const cumData = {cum_data};
new Chart(cumCtx, {{
  type: 'line',
  data: {{
    labels: {cum_labels},
    datasets: [{{
      data: cumData,
      borderColor: '{line_color}',
      backgroundColor: '{fill_color}',
      fill: true, tension: 0.35, pointRadius: 3, borderWidth: 2,
      pointBackgroundColor: cumData.map(v => v >= 0 ? '#22c55e' : '#ef4444'),
    }}],
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: '#64748b', font: {{ size: 10 }} }}, grid: {{ color: '#1e293b' }} }},
      y: {{ ticks: {{ color: '#64748b', font: {{ size: 10 }}, callback: v => (v/1000).toFixed(0)+'K' }}, grid: {{ color: '#1e293b' }} }},
    }},
  }},
}});"""

    # ── Symbol P&L Chart ──
    sym_chart = ""
    sym_chart_js = ""
    sorted_syms = sorted(symbol_pnl.items(), key=lambda x: x[1], reverse=True)
    if sorted_syms:
        sym_labels = json.dumps([s[0] for s in sorted_syms])
        sym_data = json.dumps([s[1] for s in sorted_syms])
        sym_colors = json.dumps([
            "#22c55e" if v >= 0 else "#ef4444" for _, v in sorted_syms
        ])
        sym_chart = """
<div class="chart-section">
  <div class="sec-title">종목별 손익</div>
  <div class="chart-wrap"><canvas id="symChart"></canvas></div>
</div>"""
        sym_chart_js = f"""
const symCtx = document.getElementById('symChart').getContext('2d');
new Chart(symCtx, {{
  type: 'bar',
  data: {{
    labels: {sym_labels},
    datasets: [{{ data: {sym_data}, backgroundColor: {sym_colors}, borderRadius: 4 }}],
  }},
  options: {{
    responsive: true, maintainAspectRatio: false, indexAxis: 'y',
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: '#64748b', font: {{ size: 10 }}, callback: v => (v/1000).toFixed(0)+'K' }}, grid: {{ color: '#1e293b' }} }},
      y: {{ ticks: {{ color: '#e0e0e0', font: {{ size: 11 }} }}, grid: {{ display: false }} }},
    }},
  }},
}});"""

    # ── Symbol Performance List ──
    sym_list_html = ""
    if sorted_syms:
        rows = []
        for sym, pnl in sorted_syms:
            stats = symbol_stats.get(sym, {})
            count = stats.get("count", 0)
            ret = stats.get("return_pct", 0)
            cls = _sign(pnl)
            rows.append(
                f'<div class="sym-row">'
                f'<div class="sym-name">{sym}</div>'
                f'<div class="sym-meta">{count}건</div>'
                f'<div class="sym-pnl {cls}">{_fmt(pnl)}</div>'
                f'<div class="sym-rate {cls}">{_pct(ret)}</div>'
                f'</div>'
            )
        sym_list_html = f"""
<div class="sec-title">종목별 성과</div>
<div class="sym-list">{"".join(rows)}</div>"""

    # ── Trade Cards ──
    trade_cards_html = ""
    if trades:
        max_abs_pnl = max(abs(t["pnl"]) for t in trades) or 1
        cards = []
        for t in trades:
            pnl = t["pnl"]
            cls = _sign(pnl)
            bar_pct = int(abs(pnl) / max_abs_pnl * 100) if max_abs_pnl else 0
            bar_color = "#22c55e" if pnl >= 0 else "#ef4444"
            reason_bg = "#3b82f6" if t.get("reason") == "signal" else "#6b7280"
            reason_label = "시그널" if t.get("reason") == "signal" else "장마감"

            cards.append(f"""
<div class="trade-card">
  <div class="tc-head">
    <div class="tc-name">{t['symbol']}</div>
    <span class="tc-pnl {cls}">{_fmt(pnl)}원</span>
  </div>
  <div class="tc-bar-track"><div class="tc-bar" style="width:{bar_pct}%;background:{bar_color}"></div></div>
  <div class="tc-grid">
    <div class="tc-cell"><span class="tc-label">매수</span><span class="tc-val">{t.get('buy_time','')} · {t['buy_price']:,.0f}</span></div>
    <div class="tc-cell"><span class="tc-label">매도</span><span class="tc-val">{t.get('sell_time','')} · {t['sell_price']:,.0f}</span></div>
    <div class="tc-cell"><span class="tc-label">수량</span><span class="tc-val">{t['quantity']:.0f}주</span></div>
    <div class="tc-cell"><span class="tc-label">수익률</span><span class="tc-val {cls}">{_pct(t.get('return_pct', 0))}</span></div>
    <div class="tc-cell"><span class="tc-label">보유</span><span class="tc-val">{t.get('hold_minutes', 0)}분</span></div>
    <div class="tc-cell"><span class="tc-label">사유</span><span class="reason-badge" style="background:{reason_bg}">{reason_label}</span></div>
  </div>
</div>""")
        trade_cards_html = f"""
<div class="sec-title" style="margin-top:20px">매매 내역 <span style="color:#64748b;font-weight:400">{len(trades)}건</span></div>
<div class="trade-list">{"".join(cards)}</div>"""

    # ── Watch List ──
    watch_html = ""
    if snapshot.symbols_traded:
        tags = "".join(f'<span class="sym-tag">{s}</span>' for s in snapshot.symbols_traded)
        watch_html = f"""
<div class="sec-title" style="margin-top:20px">거래 종목</div>
<div class="tag-row">{tags}</div>"""

    # ── Analysis Summary ──
    analysis_html = ""
    if snapshot.analysis_summary:
        analysis_html = f"""
<div class="conclusion">
  <div class="conclusion-title">분석 요약</div>
  <div class="conclusion-body">{snapshot.analysis_summary}</div>
</div>"""

    # ── Donut Chart JS ──
    donut_js = f"""
const donutCtx = document.getElementById('donutChart').getContext('2d');
new Chart(donutCtx, {{
  type: 'doughnut',
  data: {{
    labels: ['승', '패', '무'],
    datasets: [{{ data: [{snapshot.win_count}, {snapshot.loss_count}, {draw_count}], backgroundColor: ['#22c55e','#ef4444','#475569'], borderWidth: 0 }}],
  }},
  options: {{
    cutout: '65%',
    responsive: false,
    plugins: {{ legend: {{ display: false }}, tooltip: {{ enabled: true }} }},
  }},
}});"""

    all_js = donut_js
    if cum_js:
        all_js += "\n" + cum_js
    if sym_chart_js:
        all_js += "\n" + sym_chart_js

    body = f"""
<div class="wrap">
  {header}
  {hero}
  {stat_row}
  {metric_strip}
  {pills_html}
  {cum_chart}
  {sym_chart}
  {sym_list_html}
  {trade_cards_html}
  {watch_html}
  {analysis_html}
  <div class="footer">Claude Pilot · Daily Trading Report</div>
</div>"""

    return wrap_report_html(
        f"매매 종합 — {snapshot.period_key}",
        body,
        include_chartjs=True,
        extra_js=all_js,
    )


# ── Weekly ──


def build_weekly_html(snapshot: ReportSnapshot) -> str:
    """Build premium weekly report with hero, daily breakdown chart, and table."""
    daily_breakdown = snapshot.raw_metrics.get("daily_breakdown", [])

    period_label = f"{snapshot.period_start} ~ {snapshot.period_end}" if snapshot.period_start else snapshot.period_key
    trading_days = snapshot.trading_days or len(daily_breakdown)

    # ── Header ──
    header = f"""
<div class="hdr">
  <div class="hdr-date">주간 리포트</div>
  <div class="hdr-sub">{snapshot.period_key} · {period_label} · {trading_days}거래일</div>
</div>"""

    # ── Hero ──
    pnl_cls = _sign(snapshot.daily_pnl)
    hero = f"""
<div class="hero">
  <div class="hero-label">주간 실현손익</div>
  <div class="hero-pnl {pnl_cls}">{_fmt(snapshot.daily_pnl)}<span class="hero-unit">원</span></div>
  <div class="hero-row">
    <div class="hero-item"><span class="hi-label">수익률</span><span class="hi-val {pnl_cls}">{_pct(snapshot.daily_return_pct)}</span></div>
    <div class="hero-divider"></div>
    <div class="hero-item"><span class="hi-label">매매</span><span class="hi-val">{snapshot.total_orders}건</span></div>
    <div class="hero-divider"></div>
    <div class="hero-item"><span class="hi-label">승률</span><span class="hi-val blue">{snapshot.win_rate:.0f}%</span></div>
  </div>
</div>"""

    # ── Metric Strip ──
    metric_strip = f"""
<div class="metric-strip">
  <div class="ms-card">
    <span class="ms-label">최대 수익</span>
    <span class="ms-val pos">{_fmt(snapshot.best_trade_pnl)}</span>
  </div>
  <div class="ms-card">
    <span class="ms-label">최대 손실</span>
    <span class="ms-val neg">{_fmt(snapshot.worst_trade_pnl)}</span>
  </div>
  <div class="ms-card">
    <span class="ms-label">순자산</span>
    <span class="ms-val">{snapshot.net_asset:,.0f}</span>
  </div>
</div>"""

    # ── Daily P&L Bar Chart ──
    chart_section = ""
    chart_js = ""
    if daily_breakdown:
        bar_labels = json.dumps([d["date"] for d in daily_breakdown])
        bar_data = json.dumps([d["pnl"] for d in daily_breakdown])
        bar_colors = json.dumps([
            "#22c55e" if d["pnl"] >= 0 else "#ef4444"
            for d in daily_breakdown
        ])
        chart_section = """
<div class="chart-section">
  <div class="sec-title">일별 P&L</div>
  <div class="chart-wrap"><canvas id="dailyPnlChart"></canvas></div>
</div>"""
        chart_js = f"""
const barCtx = document.getElementById('dailyPnlChart').getContext('2d');
new Chart(barCtx, {{
  type: 'bar',
  data: {{
    labels: {bar_labels},
    datasets: [{{
      data: {bar_data},
      backgroundColor: {bar_colors},
      borderRadius: 6, barThickness: 28,
    }}],
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: '#64748b', font: {{ size: 10 }} }}, grid: {{ display: false }} }},
      y: {{ ticks: {{ color: '#64748b', font: {{ size: 10 }}, callback: v => (v/1000).toFixed(0)+'K' }}, grid: {{ color: '#1e293b' }} }},
    }},
  }},
}});"""

    # ── Cumulative Return Line ──
    cum_chart = ""
    cum_js = ""
    if daily_breakdown:
        cum_labels = json.dumps([d["date"] for d in daily_breakdown])
        cum_data = []
        c = 0.0
        for d in daily_breakdown:
            c += d.get("return_pct", 0)
            cum_data.append(round(c, 4))
        cum_data_json = json.dumps(cum_data)
        final = cum_data[-1] if cum_data else 0
        line_color = "#22c55e" if final >= 0 else "#ef4444"
        cum_chart = """
<div class="chart-section">
  <div class="sec-title">누적 수익률</div>
  <div class="chart-wrap-sm"><canvas id="cumRetChart"></canvas></div>
</div>"""
        cum_js = f"""
const cumCtx = document.getElementById('cumRetChart').getContext('2d');
new Chart(cumCtx, {{
  type: 'line',
  data: {{
    labels: {cum_labels},
    datasets: [{{
      data: {cum_data_json},
      borderColor: '{line_color}',
      backgroundColor: 'rgba(88,166,255,0.08)',
      fill: true, tension: 0.3, pointRadius: 4, borderWidth: 2,
    }}],
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: '#64748b', font: {{ size: 10 }} }}, grid: {{ color: '#1e293b' }} }},
      y: {{ ticks: {{ color: '#64748b', font: {{ size: 10 }}, callback: v => v+'%' }}, grid: {{ color: '#1e293b' }} }},
    }},
  }},
}});"""

    # ── Daily Breakdown List ──
    breakdown_html = ""
    if daily_breakdown:
        rows = []
        for d in daily_breakdown:
            pnl = d.get("pnl", 0)
            ret = d.get("return_pct", 0)
            cls = _sign(pnl)
            weekday = _weekday_ko(d["date"])
            rows.append(
                f'<div class="data-row">'
                f'<div class="dr-left"><span class="dr-name">{d["date"]}</span>'
                f'<span class="dr-sub">{weekday} · {d.get("orders", 0)}건 · {d.get("win", 0)}W/{d.get("loss", 0)}L</span></div>'
                f'<div class="dr-right"><span class="dr-rate {cls}">{_pct(ret)}</span>'
                f'<span class="dr-pnl {cls}">{_fmt(pnl)}</span></div>'
                f'</div>'
            )
        breakdown_html = f"""
<div class="section">
  <div class="sec-title">일별 상세</div>
  {"".join(rows)}
</div>"""

    all_js = ""
    if chart_js:
        all_js += chart_js
    if cum_js:
        all_js += "\n" + cum_js

    body = f"""
<div class="wrap">
  {header}
  {hero}
  {metric_strip}
  {chart_section}
  {cum_chart}
  {breakdown_html}
  <div class="footer">Claude Pilot · Weekly Trading Report</div>
</div>"""

    return wrap_report_html(
        f"주간 리포트 — {snapshot.period_key}",
        body,
        include_chartjs=bool(all_js),
        extra_js=all_js,
    )


# ── Monthly ──


def build_monthly_html(snapshot: ReportSnapshot) -> str:
    """Build premium monthly report with hero, charts, calendar heatmap."""
    daily_breakdown = snapshot.raw_metrics.get("daily_breakdown", [])

    period_label = f"{snapshot.period_start} ~ {snapshot.period_end}" if snapshot.period_start else snapshot.period_key
    trading_days = snapshot.trading_days or len(daily_breakdown)

    # ── Header ──
    header = f"""
<div class="hdr">
  <div class="hdr-date">월간 리포트</div>
  <div class="hdr-sub">{snapshot.period_key} · {trading_days}거래일</div>
</div>"""

    # ── Hero ──
    pnl_cls = _sign(snapshot.daily_pnl)
    hero = f"""
<div class="hero">
  <div class="hero-label">월간 실현손익</div>
  <div class="hero-pnl {pnl_cls}">{_fmt(snapshot.daily_pnl)}<span class="hero-unit">원</span></div>
  <div class="hero-row">
    <div class="hero-item"><span class="hi-label">수익률</span><span class="hi-val {pnl_cls}">{_pct(snapshot.daily_return_pct)}</span></div>
    <div class="hero-divider"></div>
    <div class="hero-item"><span class="hi-label">매매</span><span class="hi-val">{snapshot.total_orders}건</span></div>
    <div class="hero-divider"></div>
    <div class="hero-item"><span class="hi-label">승률</span><span class="hi-val blue">{snapshot.win_rate:.0f}%</span></div>
    <div class="hero-divider"></div>
    <div class="hero-item"><span class="hi-label">순자산</span><span class="hi-val">{_fmt_invested(snapshot.net_asset)}</span></div>
  </div>
</div>"""

    # ── Comparison Grid ──
    cmp_grid = f"""
<div class="cmp-grid" style="margin-bottom:12px">
  <div class="cmp-card">
    <span class="cmp-label">최대 수익</span>
    <span class="cmp-val pos">{_fmt(snapshot.best_trade_pnl)}</span>
  </div>
  <div class="cmp-card">
    <span class="cmp-label">최대 손실</span>
    <span class="cmp-val neg">{_fmt(snapshot.worst_trade_pnl)}</span>
  </div>
  <div class="cmp-card">
    <span class="cmp-label">매수</span>
    <span class="cmp-val">{snapshot.buy_count}건</span>
  </div>
  <div class="cmp-card">
    <span class="cmp-label">매도</span>
    <span class="cmp-val">{snapshot.sell_count}건</span>
  </div>
</div>"""

    # ── P&L + Cumulative Chart (mixed) ──
    chart_section = ""
    chart_js = ""
    if daily_breakdown:
        labels = json.dumps([d["date"][-5:] for d in daily_breakdown])  # MM-DD
        pnl_data = json.dumps([d["pnl"] for d in daily_breakdown])
        pnl_colors = json.dumps([
            "#22c55e" if d["pnl"] >= 0 else "#ef4444" for d in daily_breakdown
        ])
        cum_data = []
        c = 0.0
        for d in daily_breakdown:
            c += d.get("return_pct", 0)
            cum_data.append(round(c, 4))
        cum_json = json.dumps(cum_data)

        chart_section = """
<div class="chart-section">
  <div class="sec-title">일별 P&L / 누적 수익률</div>
  <div class="chart-wrap"><canvas id="monthlyChart"></canvas></div>
</div>"""
        chart_js = f"""
const mCtx = document.getElementById('monthlyChart').getContext('2d');
new Chart(mCtx, {{
  type: 'bar',
  data: {{
    labels: {labels},
    datasets: [
      {{
        label: 'P&L',
        data: {pnl_data},
        backgroundColor: {pnl_colors},
        borderRadius: 3, yAxisID: 'y',
      }},
      {{
        label: '누적 수익률',
        data: {cum_json},
        type: 'line',
        borderColor: '#58a6ff',
        backgroundColor: 'transparent',
        tension: 0.3, pointRadius: 2, borderWidth: 2,
        yAxisID: 'y1',
      }}
    ]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ labels: {{ color: '#94a3b8', font: {{ size: 10 }} }} }} }},
    scales: {{
      x: {{ ticks: {{ color: '#64748b', font: {{ size: 9 }}, maxRotation: 45 }}, grid: {{ display: false }} }},
      y: {{ position: 'left', ticks: {{ color: '#64748b', font: {{ size: 9 }}, callback: v => (v/1000).toFixed(0)+'K' }}, grid: {{ color: '#1e293b' }} }},
      y1: {{ position: 'right', ticks: {{ color: '#58a6ff', font: {{ size: 9 }}, callback: v => v+'%' }}, grid: {{ display: false }} }},
    }},
  }},
}});"""

    # ── Calendar Heatmap ──
    heatmap = _build_calendar_heatmap(daily_breakdown, snapshot.period_key)

    # ── Daily Breakdown ──
    breakdown_html = ""
    if daily_breakdown:
        rows = []
        for d in daily_breakdown:
            pnl = d.get("pnl", 0)
            ret = d.get("return_pct", 0)
            cls = _sign(pnl)
            weekday = _weekday_ko(d["date"])
            rows.append(
                f'<div class="data-row">'
                f'<div class="dr-left"><span class="dr-name">{d["date"][-5:]}</span>'
                f'<span class="dr-sub">{weekday} · {d.get("orders", 0)}건</span></div>'
                f'<div class="dr-right"><span class="dr-rate {cls}">{_pct(ret)}</span>'
                f'<span class="dr-pnl {cls}">{_fmt(pnl)}</span></div>'
                f'</div>'
            )
        breakdown_html = f"""
<div class="section">
  <div class="sec-title">일별 상세</div>
  {"".join(rows)}
</div>"""

    body = f"""
<div class="wrap">
  {header}
  {hero}
  {cmp_grid}
  {chart_section}
  {heatmap}
  {breakdown_html}
  <div class="footer">Claude Pilot · Monthly Trading Report</div>
</div>"""

    return wrap_report_html(
        f"월간 리포트 — {snapshot.period_key}",
        body,
        include_chartjs=bool(chart_js),
        extra_js=chart_js,
    )


def _build_calendar_heatmap(daily_breakdown: list[dict], period_key: str) -> str:
    """Build mobile-friendly calendar heatmap."""
    if not daily_breakdown:
        return ""

    pnl_map = {d["date"]: d.get("pnl", 0) for d in daily_breakdown}

    try:
        year, month = int(period_key[:4]), int(period_key[5:7])
    except (ValueError, IndexError):
        return ""

    import calendar as cal
    first_weekday, num_days = cal.monthrange(year, month)

    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    header = "".join(f"<th>{d}</th>" for d in weekdays)

    cells = "<tr>"
    for i in range(first_weekday):
        cells += "<td></td>"

    day = 1
    col = first_weekday
    while day <= num_days:
        date_str = f"{year}-{month:02d}-{day:02d}"
        pnl = pnl_map.get(date_str)
        if pnl is not None:
            if pnl > 0:
                bg, color = "rgba(34,197,94,0.25)", "#22c55e"
            elif pnl < 0:
                bg, color = "rgba(239,68,68,0.25)", "#ef4444"
            else:
                bg, color = "rgba(255,255,255,0.05)", "#64748b"
            cells += (
                f'<td style="background:{bg};border-radius:6px" title="{_fmt(pnl)}">'
                f'<div class="cal-day">{day}</div>'
                f'<div class="cal-pnl" style="color:{color}">{_fmt(pnl)}</div></td>'
            )
        else:
            cells += f'<td><div class="cal-day" style="color:#334155">{day}</div></td>'

        col += 1
        if col == 7 and day < num_days:
            cells += "</tr><tr>"
            col = 0
        day += 1

    while col < 7:
        cells += "<td></td>"
        col += 1
    cells += "</tr>"

    return f"""
<div class="section">
  <div class="sec-title">캘린더 히트맵</div>
  <table class="cal-table">
    <thead><tr>{header}</tr></thead>
    <tbody>{cells}</tbody>
  </table>
</div>"""


# ── Market ──


def build_market_html(snapshot: ReportSnapshot) -> str:
    """Build premium market report."""
    raw = snapshot.raw_metrics
    market_data = raw.get("market_data", {})

    # ── Header ──
    weekday = _weekday_ko(snapshot.period_key)
    date_display = snapshot.period_key.replace("-", ".")
    if weekday:
        date_display += f" ({weekday})"

    header = f"""
<div class="hdr">
  <div class="hdr-date">시장 리포트</div>
  <div class="hdr-sub">{date_display}</div>
</div>"""

    # ── Hero ──
    pnl_cls = _sign(snapshot.daily_pnl)
    hero = f"""
<div class="hero">
  <div class="hero-label">포트폴리오 P&L</div>
  <div class="hero-pnl {pnl_cls}">{_fmt(snapshot.daily_pnl)}<span class="hero-unit">원</span></div>
  <div class="hero-row">
    <div class="hero-item"><span class="hi-label">수익률</span><span class="hi-val {pnl_cls}">{_pct(snapshot.daily_return_pct)}</span></div>
    <div class="hero-divider"></div>
    <div class="hero-item"><span class="hi-label">순자산</span><span class="hi-val">{_fmt_invested(snapshot.net_asset)}</span></div>
    <div class="hero-divider"></div>
    <div class="hero-item"><span class="hi-label">승률</span><span class="hi-val blue">{snapshot.win_rate:.0f}%</span></div>
  </div>
</div>"""

    # ── Market Indices ──
    indices_html = ""
    indices = market_data.get("indices", {})
    if indices:
        rows = []
        for name, data in indices.items():
            if isinstance(data, dict):
                val = data.get("close", data.get("value", 0))
                chg = data.get("change_pct", 0)
                cls = _sign(chg)
                rows.append(
                    f'<div class="data-row">'
                    f'<div class="dr-left"><span class="dr-name">{name}</span></div>'
                    f'<div class="dr-right"><span class="dr-pnl">{val:,.2f}</span>'
                    f'<span class="dr-rate {cls}">{_pct(chg)}</span></div>'
                    f'</div>'
                )
        if rows:
            indices_html = f"""
<div class="section">
  <div class="sec-title">시장 지수</div>
  {"".join(rows)}
</div>"""

    # ── Sector Analysis ──
    sector_html = ""
    sectors = market_data.get("sectors", {})
    if sectors:
        sorted_sectors = sorted(
            [(k, v) for k, v in sectors.items() if isinstance(v, dict)],
            key=lambda x: x[1].get("change_pct", 0),
            reverse=True,
        )
        rows = []
        for name, data in sorted_sectors:
            chg = data.get("change_pct", 0)
            cls = _sign(chg)
            rows.append(
                f'<div class="data-row">'
                f'<div class="dr-left"><span class="dr-name">{name}</span></div>'
                f'<div class="dr-right"><span class="dr-rate {cls}">{_pct(chg)}</span></div>'
                f'</div>'
            )
        if rows:
            sector_html = f"""
<div class="section">
  <div class="sec-title">섹터별 등락률</div>
  {"".join(rows)}
</div>"""

    # ── Analysis Summary ──
    analysis_html = ""
    if snapshot.analysis_summary:
        analysis_html = f"""
<div class="conclusion">
  <div class="conclusion-title">시장 분석</div>
  <div class="conclusion-body">{snapshot.analysis_summary}</div>
</div>"""

    body = f"""
<div class="wrap">
  {header}
  {hero}
  {indices_html}
  {sector_html}
  {analysis_html}
  <div class="footer">Claude Pilot · Market Report</div>
</div>"""

    return wrap_report_html(
        f"시장 리포트 — {snapshot.period_key}",
        body,
        include_chartjs=False,
    )
