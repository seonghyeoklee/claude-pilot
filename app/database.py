"""SQLite async CRUD (aiosqlite)"""

from __future__ import annotations

import json
from pathlib import Path

import aiosqlite

from app.models import LogEntry, LogLevel, Task, TaskCreate, TaskStatus, TaskUpdate, _now_iso

_CREATE_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL
)
"""

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
    rejection_feedback TEXT DEFAULT '',
    labels TEXT DEFAULT '[]'
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
        await self._db.execute(_CREATE_LOGS_TABLE)
        await self._db.commit()
        # Migrate: add labels column if missing
        async with self._db.execute("PRAGMA table_info(tasks)") as cur:
            cols = {row[1] for row in await cur.fetchall()}
        if "labels" not in cols:
            await self._db.execute("ALTER TABLE tasks ADD COLUMN labels TEXT DEFAULT '[]'")
            await self._db.commit()
        if "branch_name" not in cols:
            await self._db.execute("ALTER TABLE tasks ADD COLUMN branch_name TEXT DEFAULT ''")
            await self._db.execute("ALTER TABLE tasks ADD COLUMN pr_url TEXT DEFAULT ''")
            await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    def _row_to_task(self, row: aiosqlite.Row) -> Task:
        d = dict(row)
        d["labels"] = json.loads(d.get("labels") or "[]")
        return Task(**d)

    async def create_task(self, data: TaskCreate) -> Task:
        now = _now_iso()
        cursor = await self._db.execute(
            "INSERT INTO tasks (title, description, priority, status, labels, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data.title, data.description, data.priority.value, TaskStatus.PENDING.value, json.dumps(data.labels), now, now),
        )
        await self._db.commit()
        return await self.get_task(cursor.lastrowid)

    async def get_task(self, task_id: int) -> Task | None:
        async with self._db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cur:
            row = await cur.fetchone()
            return self._row_to_task(row) if row else None

    async def list_tasks(self, status: TaskStatus | None = None, label: str | None = None, search: str | None = None) -> list[Task]:
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
        conditions: list[str] = []
        params: list = []
        if status:
            conditions.append("status = ?")
            params.append(status.value)
        if label:
            # JSON array contains the label string (e.g. '["bug","feat"]' LIKE '%"bug"%')
            conditions.append("labels LIKE ?")
            params.append(f'%"{label}"%')
        if search:
            conditions.append("(title LIKE ? OR description LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM tasks {where} {order}"
        async with self._db.execute(sql, tuple(params)) as cur:
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
        if data.labels is not None:
            updates.append("labels = ?")
            values.append(json.dumps(data.labels))
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

    async def pick_next_pending(self, min_priority: int = 0) -> Task | None:
        async with self._db.execute(
            "SELECT * FROM tasks WHERE status = ? AND priority >= ? ORDER BY priority DESC, created_at ASC LIMIT 1",
            (TaskStatus.PENDING.value, min_priority),
        ) as cur:
            row = await cur.fetchone()
            return self._row_to_task(row) if row else None

    async def set_task_started(self, task_id: int, branch_name: str = "") -> None:
        now = _now_iso()
        await self._db.execute(
            "UPDATE tasks SET status = ?, started_at = ?, branch_name = ?, updated_at = ? WHERE id = ?",
            (TaskStatus.IN_PROGRESS.value, now, branch_name, now, task_id),
        )
        await self._db.commit()

    async def set_task_pr(self, task_id: int, pr_url: str) -> None:
        now = _now_iso()
        await self._db.execute(
            "UPDATE tasks SET pr_url = ?, updated_at = ? WHERE id = ?",
            (pr_url, now, task_id),
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

    async def retry_task(self, task_id: int) -> Task | None:
        """Reset a failed/done task back to pending, clearing execution artifacts."""
        task = await self.get_task(task_id)
        if not task:
            return None
        now = _now_iso()
        await self._db.execute(
            "UPDATE tasks SET status = ?, started_at = NULL, completed_at = NULL, "
            "output = '', error = '', exit_code = NULL, cost_usd = NULL, "
            "approval_status = '', rejection_feedback = '', updated_at = ? WHERE id = ?",
            (TaskStatus.PENDING.value, now, task_id),
        )
        await self._db.commit()
        return await self.get_task(task_id)

    async def reset_stuck_tasks(self) -> int:
        """Reset in_progress/waiting_approval tasks back to pending (e.g. after crash/stop)."""
        now = _now_iso()
        cursor = await self._db.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE status IN (?, ?)",
            (TaskStatus.PENDING.value, now, TaskStatus.IN_PROGRESS.value, TaskStatus.WAITING_APPROVAL.value),
        )
        await self._db.commit()
        return cursor.rowcount

    # ── Logs ──

    async def insert_log(self, task_id: int, timestamp: str, level: str, message: str) -> None:
        await self._db.execute(
            "INSERT INTO logs (task_id, timestamp, level, message) VALUES (?, ?, ?, ?)",
            (task_id, timestamp, level, message),
        )
        await self._db.commit()

    async def get_task_logs(self, task_id: int, limit: int = 500) -> list[LogEntry]:
        async with self._db.execute(
            "SELECT * FROM logs WHERE task_id = ? ORDER BY id ASC LIMIT ?",
            (task_id, limit),
        ) as cur:
            rows = await cur.fetchall()
            return [
                LogEntry(
                    index=row["id"],
                    timestamp=row["timestamp"],
                    level=LogLevel(row["level"]),
                    message=row["message"],
                    task_id=row["task_id"],
                )
                for row in rows
            ]
