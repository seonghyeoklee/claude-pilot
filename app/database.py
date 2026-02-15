"""SQLite async CRUD (aiosqlite)"""

from __future__ import annotations

from pathlib import Path

import aiosqlite

from app.models import Task, TaskCreate, TaskStatus, TaskUpdate, _now_iso

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 1,
    created_at TEXT,
    updated_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    output TEXT DEFAULT '',
    error TEXT DEFAULT '',
    exit_code INTEGER,
    cost_usd REAL,
    approval_status TEXT DEFAULT '',
    rejection_feedback TEXT DEFAULT ''
)
"""


class Database:
    def __init__(self, db_path: str = "data/tasks.db") -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(_CREATE_TABLE)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    def _row_to_task(self, row: aiosqlite.Row) -> Task:
        d = dict(row)
        return Task(**d)

    async def create_task(self, data: TaskCreate) -> Task:
        now = _now_iso()
        cursor = await self._db.execute(
            "INSERT INTO tasks (title, description, priority, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (data.title, data.description, data.priority.value, TaskStatus.PENDING.value, now, now),
        )
        await self._db.commit()
        return await self.get_task(cursor.lastrowid)

    async def get_task(self, task_id: int) -> Task | None:
        async with self._db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cur:
            row = await cur.fetchone()
            return self._row_to_task(row) if row else None

    async def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        # 정렬: 활성(in_progress/waiting) → pending → 완료(done/failed), 각 그룹 내 priority DESC
        order = """ORDER BY
            CASE status
                WHEN 'in_progress' THEN 0
                WHEN 'waiting_approval' THEN 1
                WHEN 'pending' THEN 2
                WHEN 'failed' THEN 3
                WHEN 'done' THEN 4
            END,
            priority DESC, created_at ASC"""
        if status:
            sql = f"SELECT * FROM tasks WHERE status = ? {order}"
            params = (status.value,)
        else:
            sql = f"SELECT * FROM tasks {order}"
            params = ()
        async with self._db.execute(sql, params) as cur:
            rows = await cur.fetchall()
            return [self._row_to_task(r) for r in rows]

    async def update_task(self, task_id: int, data: TaskUpdate) -> Task | None:
        task = await self.get_task(task_id)
        if not task:
            return None
        updates: list[str] = []
        values: list = []
        if data.title is not None:
            updates.append("title = ?")
            values.append(data.title)
        if data.description is not None:
            updates.append("description = ?")
            values.append(data.description)
        if data.priority is not None:
            updates.append("priority = ?")
            values.append(data.priority.value)
        if data.status is not None:
            updates.append("status = ?")
            values.append(data.status.value)
        if not updates:
            return task
        updates.append("updated_at = ?")
        values.append(_now_iso())
        values.append(task_id)
        await self._db.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", values
        )
        await self._db.commit()
        return await self.get_task(task_id)

    async def delete_task(self, task_id: int) -> bool:
        cursor = await self._db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await self._db.commit()
        return cursor.rowcount > 0

    async def pick_next_pending(self) -> Task | None:
        async with self._db.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY priority DESC, created_at ASC LIMIT 1",
            (TaskStatus.PENDING.value,),
        ) as cur:
            row = await cur.fetchone()
            return self._row_to_task(row) if row else None

    async def set_task_started(self, task_id: int) -> None:
        now = _now_iso()
        await self._db.execute(
            "UPDATE tasks SET status = ?, started_at = ?, updated_at = ? WHERE id = ?",
            (TaskStatus.IN_PROGRESS.value, now, now, task_id),
        )
        await self._db.commit()

    async def set_task_waiting(self, task_id: int, output: str, exit_code: int, cost_usd: float | None) -> None:
        now = _now_iso()
        await self._db.execute(
            "UPDATE tasks SET status = ?, output = ?, exit_code = ?, cost_usd = ?, updated_at = ? WHERE id = ?",
            (TaskStatus.WAITING_APPROVAL.value, output, exit_code, cost_usd, now, task_id),
        )
        await self._db.commit()

    async def set_task_done(self, task_id: int) -> None:
        now = _now_iso()
        await self._db.execute(
            "UPDATE tasks SET status = ?, completed_at = ?, approval_status = 'approved', updated_at = ? WHERE id = ?",
            (TaskStatus.DONE.value, now, now, task_id),
        )
        await self._db.commit()

    async def set_task_failed(self, task_id: int, error: str) -> None:
        now = _now_iso()
        await self._db.execute(
            "UPDATE tasks SET status = ?, error = ?, completed_at = ?, updated_at = ? WHERE id = ?",
            (TaskStatus.FAILED.value, error, now, now, task_id),
        )
        await self._db.commit()

    async def set_task_rejected(self, task_id: int, feedback: str) -> None:
        now = _now_iso()
        await self._db.execute(
            "UPDATE tasks SET status = ?, approval_status = 'rejected', rejection_feedback = ?, updated_at = ? WHERE id = ?",
            (TaskStatus.PENDING.value, feedback, now, task_id),
        )
        await self._db.commit()

    async def reset_stuck_tasks(self) -> int:
        """Reset in_progress/waiting_approval tasks back to pending (e.g. after crash/stop)."""
        now = _now_iso()
        cursor = await self._db.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE status IN (?, ?)",
            (TaskStatus.PENDING.value, now, TaskStatus.IN_PROGRESS.value, TaskStatus.WAITING_APPROVAL.value),
        )
        await self._db.commit()
        return cursor.rowcount
