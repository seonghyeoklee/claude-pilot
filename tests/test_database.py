"""Database CRUD tests"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.database import Database
from app.models import TaskCreate, TaskPriority, TaskStatus, TaskUpdate


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
