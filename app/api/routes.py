"""REST API + SSE 로그 스트림"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.agent import AgentWorker
from app.database import Database
from pydantic import BaseModel as _PydanticBase

from app.models import ApprovalRequest, TaskCreate, TaskStatus, TaskUpdate

router = APIRouter()


def _get_db(request: Request) -> Database:
    return request.app.state.db


def _get_agent(request: Request) -> AgentWorker:
    return request.app.state.agent


# ── Tasks ──


@router.get("/api/tasks")
async def list_tasks(status: str | None = None, label: str | None = None, q: str | None = None, db: Database = Depends(_get_db)):
    task_status = TaskStatus(status) if status else None
    tasks = await db.list_tasks(task_status, label=label, search=q)
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
    asyncio.create_task(agent.run_task(task_id))
    return {"ok": True, "task_id": task_id}


# ── Agent ──


@router.get("/api/agent/status")
async def agent_status(agent: AgentWorker = Depends(_get_agent)):
    return agent.get_status().model_dump()


class StartRequest(_PydanticBase):
    min_priority: int = 0  # 0=All, 1=Med+, 2=High+, 3=Urgent


@router.post("/api/agent/start")
async def agent_start(body: StartRequest | None = None, agent: AgentWorker = Depends(_get_agent)):
    pri = body.min_priority if body else 0
    await agent.start_loop(min_priority=pri)
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
