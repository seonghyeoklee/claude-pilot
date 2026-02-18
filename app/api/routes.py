"""REST API + SSE 로그 스트림"""

from __future__ import annotations

import asyncio

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
    TaskStatus,
    TaskUpdate,
)

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
