"""Database CRUD tests"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.database import Database
from app.models import EpicCreate, EpicStatus, EpicUpdate, PlanCreate, PlanStatus, PlanUpdate, TaskCreate, TaskPriority, TaskStatus, TaskUpdate


@pytest.fixture
async def db():
    with tempfile.TemporaryDirectory() as tmp:
        d = Database(str(Path(tmp) / "test.db"))
        await d.init()
        yield d
        await d.close()


async def test_create_and_get(db: Database):
    task = await db.create_task(TaskCreate(title="Fix bug"))
    assert task.id > 0
    assert task.title == "Fix bug"
    assert task.status == TaskStatus.PENDING

    fetched = await db.get_task(task.id)
    assert fetched is not None
    assert fetched.title == "Fix bug"


async def test_get_nonexistent(db: Database):
    assert await db.get_task(9999) is None


async def test_list_tasks(db: Database):
    await db.create_task(TaskCreate(title="A"))
    await db.create_task(TaskCreate(title="B"))
    tasks = await db.list_tasks()
    assert len(tasks) == 2


async def test_list_tasks_filter_status(db: Database):
    t = await db.create_task(TaskCreate(title="A"))
    await db.set_task_done(t.id)
    await db.create_task(TaskCreate(title="B"))
    pending = await db.list_tasks(TaskStatus.PENDING)
    assert len(pending) == 1
    assert pending[0].title == "B"


async def test_update_task(db: Database):
    t = await db.create_task(TaskCreate(title="Old"))
    updated = await db.update_task(t.id, TaskUpdate(title="New", priority=TaskPriority.HIGH))
    assert updated.title == "New"
    assert updated.priority == TaskPriority.HIGH


async def test_update_nonexistent(db: Database):
    assert await db.update_task(9999, TaskUpdate(title="X")) is None


async def test_delete_task(db: Database):
    t = await db.create_task(TaskCreate(title="Del"))
    assert await db.delete_task(t.id)
    assert await db.get_task(t.id) is None


async def test_delete_nonexistent(db: Database):
    assert not await db.delete_task(9999)


async def test_pick_next_pending_priority(db: Database):
    await db.create_task(TaskCreate(title="Low", priority=TaskPriority.LOW))
    await db.create_task(TaskCreate(title="Urgent", priority=TaskPriority.URGENT))
    nxt = await db.pick_next_pending()
    assert nxt.title == "Urgent"


async def test_pick_next_pending_empty(db: Database):
    assert await db.pick_next_pending() is None


async def test_task_lifecycle(db: Database):
    t = await db.create_task(TaskCreate(title="Lifecycle"))
    await db.set_task_started(t.id)
    started = await db.get_task(t.id)
    assert started.status == TaskStatus.IN_PROGRESS
    assert started.started_at is not None

    await db.set_task_waiting(t.id, "output text", 0, 0.05)
    waiting = await db.get_task(t.id)
    assert waiting.status == TaskStatus.WAITING_APPROVAL
    assert waiting.output == "output text"

    await db.set_task_done(t.id)
    done = await db.get_task(t.id)
    assert done.status == TaskStatus.DONE
    assert done.approval_status == "approved"


async def test_task_rejection(db: Database):
    t = await db.create_task(TaskCreate(title="Reject"))
    await db.set_task_started(t.id)
    await db.set_task_waiting(t.id, "out", 0, None)
    await db.set_task_rejected(t.id, "Needs tests")
    r = await db.get_task(t.id)
    assert r.status == TaskStatus.PENDING  # back to pending
    assert r.rejection_feedback == "Needs tests"


async def test_task_failure(db: Database):
    t = await db.create_task(TaskCreate(title="Fail"))
    await db.set_task_failed(t.id, "crash")
    f = await db.get_task(t.id)
    assert f.status == TaskStatus.FAILED
    assert f.error == "crash"


# ── Label Tests ──


async def test_create_task_with_labels(db: Database):
    t = await db.create_task(TaskCreate(title="Labeled", labels=["bug", "urgent"]))
    assert t.labels == ["bug", "urgent"]
    fetched = await db.get_task(t.id)
    assert fetched.labels == ["bug", "urgent"]


async def test_create_task_without_labels(db: Database):
    t = await db.create_task(TaskCreate(title="No labels"))
    assert t.labels == []


async def test_update_task_labels(db: Database):
    t = await db.create_task(TaskCreate(title="Update labels"))
    updated = await db.update_task(t.id, TaskUpdate(labels=["feat", "v2"]))
    assert updated.labels == ["feat", "v2"]
    fetched = await db.get_task(t.id)
    assert fetched.labels == ["feat", "v2"]


async def test_update_task_clear_labels(db: Database):
    t = await db.create_task(TaskCreate(title="Clear", labels=["old"]))
    updated = await db.update_task(t.id, TaskUpdate(labels=[]))
    assert updated.labels == []


async def test_list_tasks_filter_by_label(db: Database):
    await db.create_task(TaskCreate(title="A", labels=["bug"]))
    await db.create_task(TaskCreate(title="B", labels=["feat"]))
    await db.create_task(TaskCreate(title="C", labels=["bug", "feat"]))
    bugs = await db.list_tasks(label="bug")
    assert len(bugs) == 2
    assert {t.title for t in bugs} == {"A", "C"}


async def test_list_tasks_filter_label_and_status(db: Database):
    t1 = await db.create_task(TaskCreate(title="Done bug", labels=["bug"]))
    await db.set_task_done(t1.id)
    await db.create_task(TaskCreate(title="Pending bug", labels=["bug"]))
    result = await db.list_tasks(status=TaskStatus.PENDING, label="bug")
    assert len(result) == 1
    assert result[0].title == "Pending bug"


async def test_list_tasks_filter_label_no_match(db: Database):
    await db.create_task(TaskCreate(title="A", labels=["feat"]))
    result = await db.list_tasks(label="bug")
    assert len(result) == 0


# ── Search Tests ──


async def test_search_by_title(db: Database):
    await db.create_task(TaskCreate(title="Fix login bug"))
    await db.create_task(TaskCreate(title="Add dashboard"))
    result = await db.list_tasks(search="login")
    assert len(result) == 1
    assert result[0].title == "Fix login bug"


async def test_search_by_description(db: Database):
    await db.create_task(TaskCreate(title="Task A", description="Refactor authentication module"))
    await db.create_task(TaskCreate(title="Task B", description="Update UI styles"))
    result = await db.list_tasks(search="authentication")
    assert len(result) == 1
    assert result[0].title == "Task A"


async def test_search_case_insensitive(db: Database):
    await db.create_task(TaskCreate(title="Fix Login Bug"))
    result = await db.list_tasks(search="fix login")
    assert len(result) == 1


async def test_search_no_match(db: Database):
    await db.create_task(TaskCreate(title="Fix bug"))
    result = await db.list_tasks(search="nonexistent")
    assert len(result) == 0


async def test_search_with_status_filter(db: Database):
    t1 = await db.create_task(TaskCreate(title="Fix login"))
    await db.set_task_done(t1.id)
    await db.create_task(TaskCreate(title="Fix login v2"))
    result = await db.list_tasks(status=TaskStatus.PENDING, search="login")
    assert len(result) == 1
    assert result[0].title == "Fix login v2"


async def test_search_with_label_filter(db: Database):
    await db.create_task(TaskCreate(title="Fix login", labels=["bug"]))
    await db.create_task(TaskCreate(title="Fix login styles", labels=["feat"]))
    result = await db.list_tasks(label="bug", search="login")
    assert len(result) == 1
    assert result[0].title == "Fix login"


# ── Retry Tests ──


async def test_retry_failed_task(db: Database):
    t = await db.create_task(TaskCreate(title="Flaky task"))
    await db.set_task_started(t.id)
    await db.set_task_failed(t.id, "some error")
    retried = await db.retry_task(t.id)
    assert retried.status == TaskStatus.PENDING
    assert retried.error == ""
    assert retried.exit_code is None
    assert retried.started_at is None
    assert retried.completed_at is None
    assert retried.output == ""
    assert retried.cost_usd is None


async def test_retry_nonexistent(db: Database):
    result = await db.retry_task(9999)
    assert result is None


async def test_increment_retry_count(db: Database):
    t = await db.create_task(TaskCreate(title="Retry count"))
    assert t.retry_count == 0
    new_count = await db.increment_retry_count(t.id)
    assert new_count == 1
    new_count = await db.increment_retry_count(t.id)
    assert new_count == 2
    fetched = await db.get_task(t.id)
    assert fetched.retry_count == 2


async def test_increment_retry_count_nonexistent(db: Database):
    result = await db.increment_retry_count(9999)
    assert result == 0


# ── Log Persistence Tests ──


async def test_insert_and_get_logs(db: Database):
    t = await db.create_task(TaskCreate(title="Log test"))
    await db.insert_log(t.id, "2026-02-16T00:00:00+00:00", "SYS", "Started")
    await db.insert_log(t.id, "2026-02-16T00:00:01+00:00", "CLAUDE", "Working...")
    await db.insert_log(t.id, "2026-02-16T00:00:02+00:00", "ERROR", "Crashed")
    logs = await db.get_task_logs(t.id)
    assert len(logs) == 3
    assert logs[0].level.value == "SYS"
    assert logs[1].message == "Working..."
    assert logs[2].level.value == "ERROR"


async def test_get_logs_empty(db: Database):
    t = await db.create_task(TaskCreate(title="No logs"))
    logs = await db.get_task_logs(t.id)
    assert len(logs) == 0


async def test_get_logs_limit(db: Database):
    t = await db.create_task(TaskCreate(title="Many logs"))
    for i in range(10):
        await db.insert_log(t.id, f"2026-02-16T00:00:{i:02d}+00:00", "SYS", f"Log {i}")
    logs = await db.get_task_logs(t.id, limit=5)
    assert len(logs) == 5
    assert logs[0].message == "Log 0"
    assert logs[4].message == "Log 4"


# ── Plan CRUD Tests ──


async def test_create_plan(db: Database):
    plan = await db.create_plan(PlanCreate(title="Auth System", spec="Build auth", targets={"backend": {"project": "/tmp"}}))
    assert plan.id > 0
    assert plan.title == "Auth System"
    assert plan.spec == "Build auth"
    assert plan.status == PlanStatus.DRAFT
    assert plan.targets == {"backend": {"project": "/tmp"}}


async def test_get_plan(db: Database):
    plan = await db.create_plan(PlanCreate(title="Get Plan"))
    fetched = await db.get_plan(plan.id)
    assert fetched is not None
    assert fetched.title == "Get Plan"


async def test_get_plan_nonexistent(db: Database):
    assert await db.get_plan(9999) is None


async def test_list_plans(db: Database):
    await db.create_plan(PlanCreate(title="A"))
    await db.create_plan(PlanCreate(title="B"))
    plans = await db.list_plans()
    assert len(plans) == 2


async def test_list_plans_filter_status(db: Database):
    p1 = await db.create_plan(PlanCreate(title="Running"))
    await db.set_plan_status(p1.id, PlanStatus.RUNNING)
    await db.create_plan(PlanCreate(title="Draft"))
    running = await db.list_plans(PlanStatus.RUNNING)
    assert len(running) == 1
    assert running[0].title == "Running"


async def test_update_plan(db: Database):
    plan = await db.create_plan(PlanCreate(title="Old"))
    updated = await db.update_plan(plan.id, PlanUpdate(title="New", spec="Updated spec"))
    assert updated.title == "New"
    assert updated.spec == "Updated spec"


async def test_update_plan_targets(db: Database):
    plan = await db.create_plan(PlanCreate(title="T", targets={"a": {"project": "/a"}}))
    updated = await db.update_plan(plan.id, PlanUpdate(targets={"b": {"project": "/b"}}))
    assert updated.targets == {"b": {"project": "/b"}}


async def test_update_plan_nonexistent(db: Database):
    assert await db.update_plan(9999, PlanUpdate(title="X")) is None


async def test_delete_plan(db: Database):
    plan = await db.create_plan(PlanCreate(title="Del"))
    assert await db.delete_plan(plan.id)
    assert await db.get_plan(plan.id) is None


async def test_delete_plan_nonexistent(db: Database):
    assert not await db.delete_plan(9999)


async def test_set_plan_status(db: Database):
    plan = await db.create_plan(PlanCreate(title="Status"))
    await db.set_plan_status(plan.id, PlanStatus.RUNNING)
    fetched = await db.get_plan(plan.id)
    assert fetched.status == PlanStatus.RUNNING


# ── Plan Task Tests ──


async def test_create_plan_task(db: Database):
    plan = await db.create_plan(PlanCreate(title="Plan"))
    task = await db.create_plan_task(plan.id, "Task 1", "Do stuff", "backend", 0)
    assert task.plan_id == plan.id
    assert task.target == "backend"
    assert task.task_order == 0


async def test_get_plan_tasks(db: Database):
    plan = await db.create_plan(PlanCreate(title="Plan"))
    await db.create_plan_task(plan.id, "Second", "", "api", 1)
    await db.create_plan_task(plan.id, "First", "", "api", 0)
    tasks = await db.get_plan_tasks(plan.id)
    assert len(tasks) == 2
    assert tasks[0].title == "First"
    assert tasks[1].title == "Second"


async def test_pick_next_plan_task(db: Database):
    plan = await db.create_plan(PlanCreate(title="Plan"))
    t1 = await db.create_plan_task(plan.id, "A", "", "be", 0)
    await db.create_plan_task(plan.id, "B", "", "fe", 1)
    nxt = await db.pick_next_plan_task(plan.id)
    assert nxt.title == "A"
    # Mark first done, next should be B
    await db.set_task_done(t1.id)
    nxt2 = await db.pick_next_plan_task(plan.id)
    assert nxt2.title == "B"


async def test_pick_next_plan_task_empty(db: Database):
    plan = await db.create_plan(PlanCreate(title="Empty"))
    assert await db.pick_next_plan_task(plan.id) is None


async def test_reorder_plan_tasks(db: Database):
    plan = await db.create_plan(PlanCreate(title="Reorder"))
    t1 = await db.create_plan_task(plan.id, "A", "", "", 0)
    t2 = await db.create_plan_task(plan.id, "B", "", "", 1)
    # Reverse order
    await db.reorder_plan_tasks(plan.id, [t2.id, t1.id])
    tasks = await db.get_plan_tasks(plan.id)
    assert tasks[0].title == "B"
    assert tasks[1].title == "A"


async def test_plan_task_migration(db: Database):
    """Verify plan_id, target, task_order columns exist on tasks table."""
    t = await db.create_task(TaskCreate(title="Normal task"))
    assert t.plan_id is None
    assert t.target == ""
    assert t.task_order == 0


# ── Epic CRUD Tests ──


async def test_create_epic(db: Database):
    epic = await db.create_epic(EpicCreate(title="Auth System", description="JWT auth", color="#a78bfa"))
    assert epic.id > 0
    assert epic.title == "Auth System"
    assert epic.description == "JWT auth"
    assert epic.status == EpicStatus.OPEN
    assert epic.color == "#a78bfa"
    assert epic.created_at
    assert epic.updated_at


async def test_get_epic(db: Database):
    epic = await db.create_epic(EpicCreate(title="Get Epic"))
    fetched = await db.get_epic(epic.id)
    assert fetched is not None
    assert fetched.title == "Get Epic"


async def test_get_epic_nonexistent(db: Database):
    assert await db.get_epic(9999) is None


async def test_list_epics(db: Database):
    await db.create_epic(EpicCreate(title="A"))
    await db.create_epic(EpicCreate(title="B"))
    epics = await db.list_epics()
    assert len(epics) == 2


async def test_list_epics_filter_status(db: Database):
    e1 = await db.create_epic(EpicCreate(title="Open"))
    e2 = await db.create_epic(EpicCreate(title="Done"))
    await db.update_epic(e2.id, EpicUpdate(status=EpicStatus.DONE))
    open_epics = await db.list_epics(EpicStatus.OPEN)
    assert len(open_epics) == 1
    assert open_epics[0].title == "Open"


async def test_update_epic(db: Database):
    epic = await db.create_epic(EpicCreate(title="Old", color="#000"))
    updated = await db.update_epic(epic.id, EpicUpdate(title="New", color="#fff", description="Updated"))
    assert updated.title == "New"
    assert updated.color == "#fff"
    assert updated.description == "Updated"


async def test_update_epic_status(db: Database):
    epic = await db.create_epic(EpicCreate(title="Status"))
    updated = await db.update_epic(epic.id, EpicUpdate(status=EpicStatus.IN_PROGRESS))
    assert updated.status == EpicStatus.IN_PROGRESS


async def test_update_epic_nonexistent(db: Database):
    assert await db.update_epic(9999, EpicUpdate(title="X")) is None


async def test_update_epic_no_changes(db: Database):
    epic = await db.create_epic(EpicCreate(title="NoOp"))
    result = await db.update_epic(epic.id, EpicUpdate())
    assert result.title == "NoOp"


async def test_delete_epic(db: Database):
    epic = await db.create_epic(EpicCreate(title="Del"))
    assert await db.delete_epic(epic.id)
    assert await db.get_epic(epic.id) is None


async def test_delete_epic_nonexistent(db: Database):
    assert not await db.delete_epic(9999)


async def test_delete_epic_unlinks_tasks(db: Database):
    """Deleting an epic sets epic_id to NULL on tasks, doesn't delete them."""
    epic = await db.create_epic(EpicCreate(title="Unlink"))
    t = await db.create_task(TaskCreate(title="Linked task", epic_id=epic.id))
    assert t.epic_id == epic.id
    await db.delete_epic(epic.id)
    task = await db.get_task(t.id)
    assert task is not None
    assert task.epic_id is None


async def test_delete_epic_unlinks_plans(db: Database):
    """Deleting an epic sets epic_id to NULL on plans, doesn't delete them."""
    epic = await db.create_epic(EpicCreate(title="Unlink Plans"))
    plan = await db.create_plan(PlanCreate(title="Linked plan", epic_id=epic.id))
    assert plan.epic_id == epic.id
    await db.delete_epic(epic.id)
    fetched_plan = await db.get_plan(plan.id)
    assert fetched_plan is not None
    assert fetched_plan.epic_id is None


# ── Epic-Task Relationship Tests ──


async def test_create_task_with_epic_id(db: Database):
    epic = await db.create_epic(EpicCreate(title="Epic"))
    task = await db.create_task(TaskCreate(title="Task", epic_id=epic.id))
    assert task.epic_id == epic.id
    fetched = await db.get_task(task.id)
    assert fetched.epic_id == epic.id


async def test_update_task_epic_id(db: Database):
    epic = await db.create_epic(EpicCreate(title="Epic"))
    task = await db.create_task(TaskCreate(title="Task"))
    assert task.epic_id is None
    updated = await db.update_task(task.id, TaskUpdate(epic_id=epic.id))
    assert updated.epic_id == epic.id


async def test_update_task_remove_epic(db: Database):
    """Setting epic_id=0 removes task from epic."""
    epic = await db.create_epic(EpicCreate(title="Epic"))
    task = await db.create_task(TaskCreate(title="Task", epic_id=epic.id))
    assert task.epic_id == epic.id
    updated = await db.update_task(task.id, TaskUpdate(epic_id=0))
    assert updated.epic_id is None


async def test_get_epic_tasks(db: Database):
    epic = await db.create_epic(EpicCreate(title="Epic"))
    await db.create_task(TaskCreate(title="T1", epic_id=epic.id))
    await db.create_task(TaskCreate(title="T2", epic_id=epic.id))
    await db.create_task(TaskCreate(title="T3"))  # no epic
    tasks = await db.get_epic_tasks(epic.id)
    assert len(tasks) == 2
    assert {t.title for t in tasks} == {"T1", "T2"}


async def test_get_epic_tasks_includes_plan_tasks(db: Database):
    """get_epic_tasks includes plan-generated tasks that belong to the epic."""
    epic = await db.create_epic(EpicCreate(title="Epic"))
    plan = await db.create_plan(PlanCreate(title="Plan", epic_id=epic.id))
    await db.create_plan_task(plan.id, "PT1", "", "be", 0, epic_id=epic.id)
    await db.create_task(TaskCreate(title="Manual", epic_id=epic.id))
    tasks = await db.get_epic_tasks(epic.id)
    assert len(tasks) == 2


async def test_get_epic_plans(db: Database):
    epic = await db.create_epic(EpicCreate(title="Epic"))
    await db.create_plan(PlanCreate(title="P1", epic_id=epic.id))
    await db.create_plan(PlanCreate(title="P2", epic_id=epic.id))
    await db.create_plan(PlanCreate(title="P3"))  # no epic
    plans = await db.get_epic_plans(epic.id)
    assert len(plans) == 2
    assert {p.title for p in plans} == {"P1", "P2"}


async def test_get_epic_stats(db: Database):
    epic = await db.create_epic(EpicCreate(title="Stats"))
    t1 = await db.create_task(TaskCreate(title="A", epic_id=epic.id))
    t2 = await db.create_task(TaskCreate(title="B", epic_id=epic.id))
    t3 = await db.create_task(TaskCreate(title="C", epic_id=epic.id))
    await db.set_task_done(t1.id)
    await db.set_task_done(t2.id)
    stats = await db.get_epic_stats(epic.id)
    assert stats["total"] == 3
    assert stats["done"] == 2
    assert stats["by_status"]["done"] == 2
    assert stats["by_status"]["pending"] == 1


async def test_get_epic_stats_empty(db: Database):
    epic = await db.create_epic(EpicCreate(title="Empty"))
    stats = await db.get_epic_stats(epic.id)
    assert stats["total"] == 0
    assert stats["done"] == 0


async def test_list_tasks_filter_by_epic(db: Database):
    epic = await db.create_epic(EpicCreate(title="Epic"))
    await db.create_task(TaskCreate(title="In epic", epic_id=epic.id))
    await db.create_task(TaskCreate(title="No epic"))
    epic_tasks = await db.list_tasks(epic_id=epic.id)
    assert len(epic_tasks) == 1
    assert epic_tasks[0].title == "In epic"


async def test_list_tasks_filter_no_epic(db: Database):
    epic = await db.create_epic(EpicCreate(title="Epic"))
    await db.create_task(TaskCreate(title="In epic", epic_id=epic.id))
    await db.create_task(TaskCreate(title="No epic"))
    orphan_tasks = await db.list_tasks(epic_id=None)
    assert len(orphan_tasks) == 1
    assert orphan_tasks[0].title == "No epic"


async def test_create_plan_with_epic_id(db: Database):
    epic = await db.create_epic(EpicCreate(title="Epic"))
    plan = await db.create_plan(PlanCreate(title="Plan", epic_id=epic.id))
    assert plan.epic_id == epic.id


async def test_update_plan_epic_id(db: Database):
    epic = await db.create_epic(EpicCreate(title="Epic"))
    plan = await db.create_plan(PlanCreate(title="Plan"))
    assert plan.epic_id is None
    updated = await db.update_plan(plan.id, PlanUpdate(epic_id=epic.id))
    assert updated.epic_id == epic.id


async def test_update_plan_remove_epic(db: Database):
    epic = await db.create_epic(EpicCreate(title="Epic"))
    plan = await db.create_plan(PlanCreate(title="Plan", epic_id=epic.id))
    updated = await db.update_plan(plan.id, PlanUpdate(epic_id=0))
    assert updated.epic_id is None


async def test_create_plan_task_with_epic_id(db: Database):
    epic = await db.create_epic(EpicCreate(title="Epic"))
    plan = await db.create_plan(PlanCreate(title="Plan"))
    task = await db.create_plan_task(plan.id, "Task", "Desc", "be", 0, epic_id=epic.id)
    assert task.epic_id == epic.id


async def test_epic_migration(db: Database):
    """Verify epic_id column exists on tasks and plans."""
    t = await db.create_task(TaskCreate(title="Normal"))
    assert t.epic_id is None
    p = await db.create_plan(PlanCreate(title="Normal"))
    assert p.epic_id is None
