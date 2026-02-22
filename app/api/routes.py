"""REST API + SSE 로그 스트림"""

from __future__ import annotations

import asyncio
import logging
from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel as _PydanticBase
from sse_starlette.sse import EventSourceResponse

from app.agent import AgentWorker
from app.database import Database
from app.models import (
    ApprovalRequest,
    DailySnapshot,
    EpicCreate,
    EpicStatus,
    EpicUpdate,
    PlanCreate,
    PlanStatus,
    PlanUpdate,
    TaskCreate,
    TaskPriority,
    TaskStatus,
    TaskUpdate,
)
from app.report_theme import wrap_html

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_db(request: Request) -> Database:
    return request.app.state.db


def _get_agent(request: Request) -> AgentWorker:
    return request.app.state.agent


# ── Tasks ──


@router.get("/api/tasks")
async def list_tasks(status: str | None = None, label: str | None = None, q: str | None = None, epic_id: str | None = None, db: Database = Depends(_get_db)):
    task_status = TaskStatus(status) if status else None
    # epic_id filter: not provided = no filter, "none" = tasks without epic, number = specific epic
    epic_filter: int | None | str = "unset"
    if epic_id is not None:
        if epic_id.lower() == "none":
            epic_filter = None
        else:
            epic_filter = int(epic_id)
    tasks = await db.list_tasks(task_status, label=label, search=q, plan_id=None, epic_id=epic_filter)
    return [t.model_dump() for t in tasks]


@router.post("/api/tasks", status_code=201)
async def create_task(data: TaskCreate, db: Database = Depends(_get_db)):
    task = await db.create_task(data)
    return task.model_dump()


@router.patch("/api/tasks/{task_id}")
async def update_task(task_id: int, data: TaskUpdate, db: Database = Depends(_get_db)):
    task = await db.update_task(task_id, data)
    if not task:
        raise HTTPException(404, "Task not found")
    return task.model_dump()


@router.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, db: Database = Depends(_get_db)):
    ok = await db.delete_task(task_id)
    if not ok:
        raise HTTPException(404, "Task not found")
    return {"ok": True}


@router.get("/api/tasks/{task_id}/logs")
async def get_task_logs(task_id: int, db: Database = Depends(_get_db)):
    logs = await db.get_task_logs(task_id)
    return [l.model_dump() for l in logs]


@router.post("/api/tasks/{task_id}/retry")
async def retry_task(task_id: int, db: Database = Depends(_get_db)):
    task = await db.retry_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task.model_dump()


@router.post("/api/tasks/{task_id}/run")
async def run_task(task_id: int, db: Database = Depends(_get_db), agent: AgentWorker = Depends(_get_agent)):
    task = await db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    ok = await agent.schedule_task(task_id)
    if not ok:
        raise HTTPException(409, "Agent is busy or task not runnable")
    return {"ok": True, "task_id": task_id}


# ── Agent ──


@router.get("/api/agent/status")
async def agent_status(agent: AgentWorker = Depends(_get_agent)):
    return agent.get_status().model_dump()


class StartRequest(_PydanticBase):
    min_priority: int = 0  # 0=All, 1=Med+, 2=High+, 3=Urgent
    epic_id: int | None = None  # None=all, N=specific epic


@router.post("/api/agent/start")
async def agent_start(body: StartRequest | None = None, agent: AgentWorker = Depends(_get_agent)):
    pri = body.min_priority if body else 0
    epic = body.epic_id if body else None
    await agent.start_loop(min_priority=pri, epic_id=epic)
    return {"ok": True}


@router.post("/api/agent/stop")
async def agent_stop(agent: AgentWorker = Depends(_get_agent)):
    await agent.stop_loop()
    return {"ok": True}


@router.post("/api/agent/approve")
async def agent_approve(agent: AgentWorker = Depends(_get_agent)):
    if not agent.approve():
        raise HTTPException(400, "Agent not waiting for approval")
    return {"ok": True}


@router.post("/api/agent/reject")
async def agent_reject(body: ApprovalRequest, agent: AgentWorker = Depends(_get_agent)):
    if not agent.reject(body.feedback):
        raise HTTPException(400, "Agent not waiting for approval")
    return {"ok": True}


@router.get("/api/agent/logs")
async def agent_logs(agent: AgentWorker = Depends(_get_agent)):
    async def generate():
        index = 0
        while True:
            logs = agent.get_logs(after_index=index)
            for log in logs:
                yield {"data": log.model_dump_json()}
                index = log.index + 1
            await asyncio.sleep(0.5)

    return EventSourceResponse(generate())


@router.get("/api/agent/output")
async def agent_output(agent: AgentWorker = Depends(_get_agent)):
    return {"output": agent.get_current_output()}


# ── Plans ──


@router.post("/api/plans", status_code=201)
async def create_plan(data: PlanCreate, db: Database = Depends(_get_db)):
    plan = await db.create_plan(data)
    return plan.model_dump()


@router.get("/api/plans")
async def list_plans(status: str | None = None, db: Database = Depends(_get_db)):
    plan_status = PlanStatus(status) if status else None
    plans = await db.list_plans(plan_status)
    return [p.model_dump() for p in plans]


@router.get("/api/plans/{plan_id}")
async def get_plan(plan_id: int, db: Database = Depends(_get_db)):
    plan = await db.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    tasks = await db.get_plan_tasks(plan_id)
    result = plan.model_dump()
    result["tasks"] = [t.model_dump() for t in tasks]
    return result


@router.patch("/api/plans/{plan_id}")
async def update_plan(plan_id: int, data: PlanUpdate, db: Database = Depends(_get_db)):
    plan = await db.update_plan(plan_id, data)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return plan.model_dump()


@router.delete("/api/plans/{plan_id}")
async def delete_plan(plan_id: int, db: Database = Depends(_get_db)):
    ok = await db.delete_plan(plan_id)
    if not ok:
        raise HTTPException(404, "Plan not found")
    return {"ok": True}


@router.post("/api/plans/{plan_id}/decompose")
async def decompose_plan(plan_id: int, db: Database = Depends(_get_db), agent: AgentWorker = Depends(_get_agent)):
    plan = await db.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    if plan.status not in (PlanStatus.DRAFT, PlanStatus.REVIEWING):
        raise HTTPException(409, f"Plan cannot be decomposed in '{plan.status.value}' status")
    asyncio.create_task(agent.decompose_plan(plan_id))
    return {"ok": True, "plan_id": plan_id}


@router.post("/api/plans/{plan_id}/approve")
async def approve_plan(plan_id: int, db: Database = Depends(_get_db), agent: AgentWorker = Depends(_get_agent)):
    plan = await db.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    if plan.status != PlanStatus.REVIEWING:
        raise HTTPException(409, f"Plan cannot be approved in '{plan.status.value}' status")
    await db.set_plan_status(plan_id, PlanStatus.APPROVED)
    asyncio.create_task(agent.run_plan(plan_id))
    return {"ok": True, "plan_id": plan_id}


@router.post("/api/plans/{plan_id}/stop")
async def stop_plan(plan_id: int, db: Database = Depends(_get_db), agent: AgentWorker = Depends(_get_agent)):
    plan = await db.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    if plan.status != PlanStatus.RUNNING:
        raise HTTPException(409, f"Plan is not running")
    agent._stop_requested = True
    await db.set_plan_status(plan_id, PlanStatus.FAILED)
    return {"ok": True}


class ReorderRequest(_PydanticBase):
    task_ids: list[int]


@router.post("/api/plans/{plan_id}/tasks/reorder")
async def reorder_plan_tasks(plan_id: int, body: ReorderRequest, db: Database = Depends(_get_db)):
    plan = await db.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    await db.reorder_plan_tasks(plan_id, body.task_ids)
    return {"ok": True}


# ── Epics ──


@router.post("/api/epics", status_code=201)
async def create_epic(data: EpicCreate, db: Database = Depends(_get_db)):
    epic = await db.create_epic(data)
    return epic.model_dump()


@router.get("/api/epics")
async def list_epics(status: str | None = None, db: Database = Depends(_get_db)):
    epic_status = EpicStatus(status) if status else None
    epics = await db.list_epics(epic_status)
    result = []
    for e in epics:
        d = e.model_dump()
        d["stats"] = await db.get_epic_stats(e.id)
        result.append(d)
    return result


@router.get("/api/epics/{epic_id}")
async def get_epic(epic_id: int, db: Database = Depends(_get_db)):
    epic = await db.get_epic(epic_id)
    if not epic:
        raise HTTPException(404, "Epic not found")
    result = epic.model_dump()
    result["tasks"] = [t.model_dump() for t in await db.get_epic_tasks(epic_id)]
    result["plans"] = [p.model_dump() for p in await db.get_epic_plans(epic_id)]
    result["stats"] = await db.get_epic_stats(epic_id)
    return result


@router.patch("/api/epics/{epic_id}")
async def update_epic(epic_id: int, data: EpicUpdate, db: Database = Depends(_get_db)):
    epic = await db.update_epic(epic_id, data)
    if not epic:
        raise HTTPException(404, "Epic not found")
    return epic.model_dump()


@router.delete("/api/epics/{epic_id}")
async def delete_epic(epic_id: int, db: Database = Depends(_get_db)):
    ok = await db.delete_epic(epic_id)
    if not ok:
        raise HTTPException(404, "Epic not found")
    return {"ok": True}


# ── Daily Trading Analysis ──


class AnalyzeDailyRequest(_PydanticBase):
    date: str | None = None  # YYYY-MM-DD, defaults to today
    trading_api_url: str = "http://localhost:8000"
    epic_id: int | None = None  # attach created tasks to this epic


def _build_analysis_prompt(journal_data: dict) -> str:
    """Build a Claude prompt for trading analysis with task generation."""
    import json

    journal_json = json.dumps(journal_data, ensure_ascii=False, indent=2)
    return (
        "You are a quantitative trading analyst. Analyze the following daily trading journal data "
        "and generate actionable improvement tasks for the trading system.\n\n"
        "## Trading Journal Data\n"
        f"```json\n{journal_json}\n```\n\n"
        "## Instructions\n"
        "1. Analyze the trading performance: win rate, P&L, risk management, strategy effectiveness\n"
        "2. Identify specific areas for improvement in the trading algorithms\n"
        "3. Generate concrete, actionable improvement tasks\n\n"
        "## Output Format\n"
        "Respond with ONLY a JSON object (no other text):\n"
        "```json\n"
        "{\n"
        '  "summary": "Brief overall analysis summary (2-3 sentences)",\n'
        '  "tasks": [\n'
        "    {\n"
        '      "title": "Concise task title",\n'
        '      "description": "Detailed description of what to implement or fix",\n'
        '      "priority": 0-3\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "```\n\n"
        "Priority levels: 0=Low, 1=Medium, 2=High, 3=Urgent\n"
        "Generate between 1-5 tasks based on the analysis."
    )


def _extract_summary(parsed: dict) -> str:
    """Extract summary text from parsed Claude analysis output."""
    if isinstance(parsed, dict):
        return parsed.get("summary", "")
    return ""


@router.post("/api/analyze-daily")
async def analyze_daily(
    body: AnalyzeDailyRequest | None = None,
    db: Database = Depends(_get_db),
    agent: AgentWorker = Depends(_get_agent),
):
    req = body or AnalyzeDailyRequest()
    target_date = req.date or date.today().isoformat()
    trading_url = req.trading_api_url.rstrip("/")

    # 1. Fetch trading journal from quantum-trading-platform
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{trading_url}/trading/journal/{target_date}")
    except httpx.ConnectError:
        raise HTTPException(502, f"Cannot connect to trading platform at {trading_url}")
    except httpx.RequestError as exc:
        raise HTTPException(502, f"Trading platform request failed: {exc}")

    if resp.status_code == 404:
        return {
            "date": target_date,
            "trade_count": 0,
            "analysis_summary": "No trading data found for this date.",
            "tasks_created": [],
            "cost_usd": None,
        }
    if resp.status_code != 200:
        raise HTTPException(502, f"Trading platform returned {resp.status_code}")

    journal_data = resp.json()

    # Check for empty trades (key varies: trades, entries, events)
    trades = journal_data.get("trades") or journal_data.get("entries") or journal_data.get("events") or []
    trade_count = len(trades) if isinstance(trades, list) else 0
    if trade_count == 0:
        return {
            "date": target_date,
            "trade_count": 0,
            "analysis_summary": "No trades recorded for this date.",
            "tasks_created": [],
            "cost_usd": None,
        }

    # 2. Run Claude analysis
    prompt = _build_analysis_prompt(journal_data)
    try:
        exit_code, output, cost = await agent._run_claude(prompt, 0)
    except Exception as exc:
        logger.exception("Claude analysis failed for %s", target_date)
        raise HTTPException(500, f"Claude analysis failed: {exc}")

    if exit_code != 0:
        raise HTTPException(500, f"Claude analysis failed (exit={exit_code})")

    # 3. Parse JSON from Claude output
    import json as _json
    import re as _re

    analysis: dict | None = None

    # Try direct JSON parse
    try:
        candidate = _json.loads(output.strip())
        if isinstance(candidate, dict):
            analysis = candidate
        elif isinstance(candidate, list) and candidate and isinstance(candidate[0], dict):
            analysis = candidate[0]
    except (ValueError, _json.JSONDecodeError):
        pass

    # Try extracting from markdown code fence
    if analysis is None:
        fence_match = _re.search(r'```(?:json)?\s*\n([\s\S]*?)\n```', output)
        if fence_match:
            try:
                candidate = _json.loads(fence_match.group(1).strip())
                if isinstance(candidate, dict):
                    analysis = candidate
            except (ValueError, _json.JSONDecodeError):
                pass

    # Try finding first { ... } balanced JSON object
    if analysis is None:
        start = output.find('{')
        while start != -1:
            depth = 0
            in_string = False
            escape = False
            for i in range(start, len(output)):
                c = output[i]
                if escape:
                    escape = False
                    continue
                if c == '\\' and in_string:
                    escape = True
                    continue
                if c == '"' and not escape:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            candidate = _json.loads(output[start:i + 1])
                            if isinstance(candidate, dict) and ("tasks" in candidate or "summary" in candidate):
                                analysis = candidate
                        except (ValueError, _json.JSONDecodeError):
                            pass
                        break
            if analysis is not None:
                break
            start = output.find('{', start + 1)

    if analysis is None:
        logger.error("Failed to parse analysis JSON. Output (first 2000 chars): %s", output[:2000])
        raise HTTPException(500, "Failed to parse analysis output from Claude")

    summary = _extract_summary(analysis)
    task_items = analysis.get("tasks", [])

    # 4. Delete existing tasks for same date, then create new ones
    existing = await db.list_tasks(label="trading-analysis")
    date_tag = f"[Auto-generated from {target_date} trading analysis]"
    deleted_count = 0
    for t in existing:
        if date_tag in t.description:
            await db.delete_task(t.id)
            deleted_count += 1
    if deleted_count:
        logger.info("Replaced %d existing trading-analysis tasks for %s", deleted_count, target_date)

    created_tasks = []
    for item in task_items:
        title = item.get("title", "")
        if not title:
            continue
        description = item.get("description", "")
        raw_priority = item.get("priority", 1)
        try:
            priority = TaskPriority(raw_priority)
        except ValueError:
            priority = TaskPriority.MEDIUM

        task = await db.create_task(TaskCreate(
            title=f"[Trading] {title}",
            description=f"[Auto-generated from {target_date} trading analysis]\n\n{description}",
            priority=priority,
            labels=["trading-analysis"],
            epic_id=req.epic_id,
        ))
        created_tasks.append({"id": task.id, "title": task.title, "priority": priority.value})

    return {
        "date": target_date,
        "trade_count": trade_count,
        "analysis_summary": summary,
        "tasks_created": created_tasks,
        "cost_usd": cost,
    }


# ── Daily Trading Report ──


class ReportDailyRequest(_PydanticBase):
    date: str | None = None  # YYYY-MM-DD, defaults to today
    trading_api_url: str = "http://localhost:8000"


def _calculate_metrics(events: list[dict], positions: dict) -> dict:
    """Calculate trading metrics from journal events and positions."""
    signals = [e for e in events if e.get("event_type") == "signal"]
    orders = [e for e in events if e.get("event_type") == "order" and e.get("success")]

    buys = [o for o in orders if o.get("side", "").lower() == "buy"]
    sells = [o for o in orders if o.get("side", "").lower() == "sell"]

    # FIFO matching per symbol
    from collections import defaultdict

    buy_queue: dict[str, list[dict]] = defaultdict(list)
    for b in sorted(buys, key=lambda x: x.get("timestamp", "")):
        sym = b.get("symbol", "unknown")
        buy_queue[sym].append(b)

    trades: list[dict] = []
    for s in sorted(sells, key=lambda x: x.get("timestamp", "")):
        sym = s.get("symbol", "unknown")
        if not buy_queue[sym]:
            continue
        b = buy_queue[sym].pop(0)
        buy_price = float(b.get("price", 0))
        sell_price = float(s.get("price", 0))
        qty = min(float(b.get("quantity", 0)), float(s.get("quantity", 0)))
        pnl = (sell_price - buy_price) * qty
        trades.append({"symbol": sym, "pnl": pnl, "buy_price": buy_price, "sell_price": sell_price, "quantity": qty})

    win_count = sum(1 for t in trades if t["pnl"] > 0)
    loss_count = sum(1 for t in trades if t["pnl"] < 0)
    total_matched = win_count + loss_count
    win_rate = (win_count / total_matched * 100) if total_matched > 0 else 0.0

    pnl_values = [t["pnl"] for t in trades]
    best_trade_pnl = max(pnl_values) if pnl_values else 0.0
    worst_trade_pnl = min(pnl_values) if pnl_values else 0.0
    daily_pnl = sum(pnl_values)

    symbols_traded = sorted(set(o.get("symbol", "unknown") for o in orders)) if orders else []

    # Net asset from positions
    net_asset = 0.0
    for market in ("domestic", "us"):
        mkt = positions.get(market, {})
        summary = mkt.get("summary", {})
        net_asset += float(summary.get("net_asset", 0))

    # Per-symbol P&L breakdown
    symbol_pnl: dict[str, float] = defaultdict(float)
    for t in trades:
        symbol_pnl[t["symbol"]] += t["pnl"]

    # Daily return % (from previous snapshot — caller should compute if needed)
    return {
        "net_asset": net_asset,
        "daily_pnl": daily_pnl,
        "daily_return_pct": 0.0,  # will be computed with prev snapshot
        "total_signals": len(signals),
        "total_orders": len(orders),
        "buy_count": len(buys),
        "sell_count": len(sells),
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round(win_rate, 2),
        "best_trade_pnl": round(best_trade_pnl, 2),
        "worst_trade_pnl": round(worst_trade_pnl, 2),
        "symbols_traded": symbols_traded,
        "raw_metrics": {"symbol_pnl": dict(symbol_pnl), "trades": trades},
    }


def _build_report_html(snapshot: DailySnapshot, history: list[DailySnapshot]) -> str:
    """Build an HTML report page for a daily snapshot."""
    # Sign helper
    def _sign(v: float) -> str:
        return "positive" if v >= 0 else "negative"

    def _fmt(v: float) -> str:
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:,.0f}"

    def _pct(v: float) -> str:
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:.2f}%"

    # Summary cards
    cards = f"""
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:16px; margin-bottom:24px;">
      <div class="summary-card">
        <h3>순자산</h3>
        <div style="font-size:24px; font-weight:700;">₩{snapshot.net_asset:,.0f}</div>
      </div>
      <div class="summary-card">
        <h3>일일 P&amp;L</h3>
        <div style="font-size:24px; font-weight:700;" class="{_sign(snapshot.daily_pnl)}">{_fmt(snapshot.daily_pnl)}원</div>
      </div>
      <div class="summary-card">
        <h3>일일 수익률</h3>
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

    # Cumulative return chart data (oldest first)
    chart_history = list(reversed(history))
    chart_labels = [s.date for s in chart_history]
    chart_returns = []
    cumulative = 0.0
    for s in chart_history:
        cumulative += s.daily_return_pct
        chart_returns.append(round(cumulative, 4))

    import json as _json

    chart_labels_json = _json.dumps(chart_labels)
    chart_data_json = _json.dumps(chart_returns)

    chart_section = f"""
    <div class="section">
      <h2>누적 수익률 (최근 {len(chart_history)}일)</h2>
      <canvas id="cumReturnChart" height="100"></canvas>
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

    symbol_table = f"""
    <div class="section">
      <h2>종목별 P&amp;L</h2>
      <table>
        <thead><tr><th>종목</th><th>P&amp;L</th></tr></thead>
        <tbody>{rows if rows else '<tr><td colspan="2" style="color:var(--text-secondary)">거래 없음</td></tr>'}</tbody>
      </table>
    </div>""" if symbol_pnl or not rows else ""

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
        <p>{snapshot.date}</p>
      </header>
      {cards}
      {chart_section}
      {symbol_table}
      {analysis_section}
      <footer>Claude Pilot &mdash; Daily Trading Report</footer>
    </div>"""

    return wrap_html(
        f"Trading Report — {snapshot.date}",
        body,
        include_chartjs=True,
        extra_js=chart_js,
    )


@router.post("/api/report-daily")
async def report_daily(
    body: ReportDailyRequest | None = None,
    db: Database = Depends(_get_db),
):
    req = body or ReportDailyRequest()
    target_date = req.date or date.today().isoformat()
    trading_url = req.trading_api_url.rstrip("/")

    # 1. Fetch journal + positions concurrently
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            journal_task = client.get(f"{trading_url}/trading/journal/{target_date}")
            positions_task = client.get(f"{trading_url}/trading/positions")
            journal_resp, positions_resp = await asyncio.gather(journal_task, positions_task)
    except httpx.ConnectError:
        raise HTTPException(502, f"Cannot connect to trading platform at {trading_url}")
    except httpx.RequestError as exc:
        raise HTTPException(502, f"Trading platform request failed: {exc}")

    # Parse journal events
    events: list[dict] = []
    if journal_resp.status_code == 200:
        journal_data = journal_resp.json()
        events = journal_data.get("events") or journal_data.get("trades") or journal_data.get("entries") or []

    # Parse positions
    positions: dict = {}
    if positions_resp.status_code == 200:
        positions = positions_resp.json()

    # 2. Calculate metrics
    metrics = _calculate_metrics(events, positions)

    # Compute daily_return_pct from previous snapshot
    snapshots = await db.list_snapshots(limit=2)
    prev = next((s for s in snapshots if s.date != target_date), None)
    if prev and prev.net_asset > 0 and metrics["net_asset"] > 0:
        metrics["daily_return_pct"] = round(
            (metrics["net_asset"] - prev.net_asset) / prev.net_asset * 100, 4
        )

    # 3. Upsert snapshot
    snapshot = await db.upsert_snapshot(target_date, metrics)

    return snapshot.model_dump()


@router.get("/api/reports/{report_date}")
async def get_report_html(report_date: str, db: Database = Depends(_get_db)):
    snapshot = await db.get_snapshot(report_date)
    if not snapshot:
        raise HTTPException(404, "No report found for this date")
    history = await db.list_snapshots(limit=30)
    html = _build_report_html(snapshot, history)
    return HTMLResponse(html)


@router.get("/api/reports")
async def list_reports(limit: int = 30, db: Database = Depends(_get_db)):
    snapshots = await db.list_snapshots(limit=limit)
    return [s.model_dump() for s in snapshots]
