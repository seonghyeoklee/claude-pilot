"""Task, AgentStatus, LogEntry 모델"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"
    FAILED = "failed"


class TaskPriority(int, Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    URGENT = 3


class Task(BaseModel):
    id: int = 0
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: str = Field(default_factory=lambda: _now_iso())
    updated_at: str = Field(default_factory=lambda: _now_iso())
    started_at: str | None = None
    completed_at: str | None = None
    output: str = ""
    error: str = ""
    exit_code: int | None = None
    cost_usd: float | None = None
    approval_status: str = ""
    rejection_feedback: str = ""


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None


class AgentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    STOPPED = "stopped"


class AgentStatus(BaseModel):
    state: AgentState = AgentState.STOPPED
    current_task_id: int | None = None
    current_task_title: str | None = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    loop_running: bool = False


class LogLevel(str, Enum):
    SYSTEM = "SYS"
    CLAUDE = "CLAUDE"
    TOOL = "TOOL"
    RESULT = "RESULT"
    ERROR = "ERROR"


class LogEntry(BaseModel):
    index: int = 0
    timestamp: str = Field(default_factory=lambda: _now_iso())
    level: LogLevel = LogLevel.SYSTEM
    message: str = ""
    task_id: int | None = None


class ApprovalRequest(BaseModel):
    feedback: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
