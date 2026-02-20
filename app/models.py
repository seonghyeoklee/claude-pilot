"""Task, Plan, AgentStatus, LogEntry 모델"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class EpicStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlanStatus(str, Enum):
    DRAFT = "draft"
    DECOMPOSING = "decomposing"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    RUNNING = "running"
    COMPLETED = "completed"
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
    labels: list[str] = Field(default_factory=list)
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
    retry_count: int = 0
    branch_name: str = ""
    pr_url: str = ""
    # Plan fields
    plan_id: int | None = None
    target: str = ""
    task_order: int = 0
    # Epic fields
    epic_id: int | None = None


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    labels: list[str] = Field(default_factory=list)
    epic_id: int | None = None
    target: str = ""  # 프로젝트 경로 (빈 문자열 = config 기본값)


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    labels: list[str] | None = None
    epic_id: int | None = None  # 0 = remove from epic
    target: str | None = None


class Plan(BaseModel):
    id: int = 0
    title: str
    spec: str = ""
    targets: dict[str, dict] = Field(default_factory=dict)
    status: PlanStatus = PlanStatus.DRAFT
    created_at: str = Field(default_factory=lambda: _now_iso())
    updated_at: str = Field(default_factory=lambda: _now_iso())
    epic_id: int | None = None


class PlanCreate(BaseModel):
    title: str
    spec: str = ""
    targets: dict[str, dict] = Field(default_factory=dict)
    epic_id: int | None = None


class PlanUpdate(BaseModel):
    title: str | None = None
    spec: str | None = None
    targets: dict[str, dict] | None = None
    status: PlanStatus | None = None
    epic_id: int | None = None  # 0 = remove from epic


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


class Epic(BaseModel):
    id: int = 0
    title: str
    description: str = ""
    status: EpicStatus = EpicStatus.OPEN
    color: str = ""
    created_at: str = Field(default_factory=lambda: _now_iso())
    updated_at: str = Field(default_factory=lambda: _now_iso())


class EpicCreate(BaseModel):
    title: str
    description: str = ""
    color: str = ""


class EpicUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: EpicStatus | None = None
    color: str | None = None


class ApprovalRequest(BaseModel):
    feedback: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
