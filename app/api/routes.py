"""REST API + SSE 로그 스트림"""

from __future__ import annotations

import asyncio
import logging
from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel as _PydanticBase
from sse_starlette.sse import EventSourceResponse

from app.agent import AgentWorker
from app.database import Database
from app.models import (
    ApprovalRequest,
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

    # Check for empty trades
    trades = journal_data.get("trades", journal_data.get("entries", []))
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
    parsed = agent._parse_json_from_output(output)
    if parsed is None:
        # Try parsing as a single object (not array)
        import json
        try:
            parsed = json.loads(output.strip())
        except (json.JSONDecodeError, ValueError):
            pass

    if parsed is None:
        raise HTTPException(500, "Failed to parse analysis output from Claude")

    # Handle both formats: direct dict or list wrapping a dict
    analysis: dict = {}
    if isinstance(parsed, dict):
        analysis = parsed
    elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
        analysis = parsed[0]
    else:
        raise HTTPException(500, "Unexpected analysis output format")

    summary = _extract_summary(analysis)
    task_items = analysis.get("tasks", [])

    # 4. Create tasks in DB
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
