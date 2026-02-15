"""Agent Worker — subprocess claude -p, 로그 스트리밍, 승인 게이트"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import deque

from app.config import AppConfig
from app.database import Database
from app.models import (
    AgentState,
    AgentStatus,
    LogEntry,
    LogLevel,
    TaskStatus,
    _now_iso,
)

logger = logging.getLogger(__name__)


class AgentWorker:
    def __init__(self, config: AppConfig, db: Database) -> None:
        self.config = config
        self.db = db
        self._state = AgentState.STOPPED
        self._current_task_id: int | None = None
        self._current_task_title: str | None = None
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._loop_task: asyncio.Task | None = None
        self._approval_event = asyncio.Event()
        self._approved: bool = False
        self._rejection_feedback: str = ""
        self._logs: deque[LogEntry] = deque(maxlen=1000)
        self._log_index = 0
        self._current_output: str = ""
        self._stop_requested = False
        self._proc: asyncio.subprocess.Process | None = None

    # ── Status ──

    def get_status(self) -> AgentStatus:
        return AgentStatus(
            state=self._state,
            current_task_id=self._current_task_id,
            current_task_title=self._current_task_title,
            tasks_completed=self._tasks_completed,
            tasks_failed=self._tasks_failed,
            loop_running=self._loop_task is not None and not self._loop_task.done(),
        )

    def get_logs(self, after_index: int = 0) -> list[LogEntry]:
        return [e for e in self._logs if e.index >= after_index]

    def get_current_output(self) -> str:
        return self._current_output

    # ── Logging ──

    def _add_log(self, level: LogLevel, message: str, task_id: int | None = None) -> None:
        entry = LogEntry(
            index=self._log_index,
            timestamp=_now_iso(),
            level=level,
            message=message,
            task_id=task_id,
        )
        self._logs.append(entry)
        self._log_index += 1

    # ── Loop Control ──

    async def start_loop(self) -> None:
        if self._loop_task and not self._loop_task.done():
            return
        self._stop_requested = False
        self._state = AgentState.IDLE
        self._add_log(LogLevel.SYSTEM, "Agent loop started")
        self._loop_task = asyncio.create_task(self._run_loop())

    async def stop_loop(self) -> None:
        self._stop_requested = True
        self._approval_event.set()  # unblock if waiting
        # Kill running claude process
        if self._proc and self._proc.returncode is None:
            try:
                self._proc.kill()
            except ProcessLookupError:
                pass
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        # Reset stuck in_progress tasks back to pending
        await self.db.reset_stuck_tasks()
        self._state = AgentState.STOPPED
        self._current_task_id = None
        self._current_task_title = None
        self._add_log(LogLevel.SYSTEM, "Agent loop stopped")

    # ── Approval ──

    def approve(self) -> bool:
        if self._state != AgentState.WAITING_APPROVAL:
            return False
        self._approved = True
        self._approval_event.set()
        return True

    def reject(self, feedback: str = "") -> bool:
        if self._state != AgentState.WAITING_APPROVAL:
            return False
        self._approved = False
        self._rejection_feedback = feedback
        self._approval_event.set()
        return True

    # ── Run Single Task ──

    async def run_task(self, task_id: int) -> None:
        """Execute a single task (without the loop)."""
        task = await self.db.get_task(task_id)
        if not task:
            return
        if task.status not in (TaskStatus.PENDING, TaskStatus.FAILED):
            return
        await self._execute_task(task_id, task.title, task.description)

    # ── Internal Loop ──

    async def _run_loop(self) -> None:
        try:
            while not self._stop_requested:
                task = await self.db.pick_next_pending()
                if not task:
                    self._state = AgentState.IDLE
                    await asyncio.sleep(self.config.poll_interval)
                    continue
                await self._execute_task(task.id, task.title, task.description)
                if self._stop_requested:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            self._state = AgentState.STOPPED

    async def _execute_task(self, task_id: int, title: str, description: str) -> None:
        self._current_task_id = task_id
        self._current_task_title = title
        self._current_output = ""
        self._state = AgentState.RUNNING

        await self.db.set_task_started(task_id)
        self._add_log(LogLevel.SYSTEM, f"Starting task #{task_id}: {title}", task_id)
        logger.info("Starting task #%d: %s", task_id, title)

        try:
            prompt = self._build_prompt(title, description)
            exit_code, output, cost = await self._run_claude(prompt, task_id)
        except Exception as exc:
            logger.exception("Unexpected error running task #%d", task_id)
            self._tasks_failed += 1
            await self.db.set_task_failed(task_id, str(exc)[:2000])
            self._add_log(LogLevel.ERROR, f"Task #{task_id} crashed: {exc}", task_id)
            self._state = AgentState.IDLE
            self._current_task_id = None
            self._current_task_title = None
            return

        self._current_output = output
        logger.info("Task #%d finished: exit=%d, output=%d chars, cost=%s", task_id, exit_code, len(output), cost)

        if self._stop_requested:
            return

        if exit_code != 0:
            self._state = AgentState.IDLE
            self._tasks_failed += 1
            await self.db.set_task_failed(task_id, output[-2000:] if output else "Process failed")
            self._add_log(LogLevel.ERROR, f"Task #{task_id} failed (exit={exit_code})", task_id)
            self._current_task_id = None
            self._current_task_title = None
            return

        # Approval gate
        if self.config.auto_approve:
            self._tasks_completed += 1
            await self.db.set_task_done(task_id)
            self._add_log(LogLevel.SYSTEM, f"Task #{task_id} completed (auto-approved)", task_id)
        else:
            self._state = AgentState.WAITING_APPROVAL
            await self.db.set_task_waiting(task_id, output[-5000:] if output else "", exit_code, cost)
            self._add_log(LogLevel.SYSTEM, f"Task #{task_id} waiting for approval", task_id)

            self._approval_event.clear()
            self._approved = False
            self._rejection_feedback = ""
            await self._approval_event.wait()

            if self._stop_requested:
                return

            if self._approved:
                self._tasks_completed += 1
                await self.db.set_task_done(task_id)
                self._add_log(LogLevel.SYSTEM, f"Task #{task_id} approved", task_id)
            else:
                self._tasks_failed += 1
                await self.db.set_task_rejected(task_id, self._rejection_feedback)
                self._add_log(LogLevel.SYSTEM, f"Task #{task_id} rejected: {self._rejection_feedback}", task_id)

        self._state = AgentState.IDLE
        self._current_task_id = None
        self._current_task_title = None

    def _build_prompt(self, title: str, description: str) -> str:
        parts = [title]
        if description:
            parts.append(description)
        return "\n\n".join(parts)

    async def _run_claude(self, prompt: str, task_id: int) -> tuple[int, str, float | None]:
        cmd = [self.config.claude_command, "-p", prompt, "--output-format", "stream-json", "--verbose"]
        if self.config.claude_model:
            cmd.extend(["--model", self.config.claude_model])
        if self.config.claude_max_budget:
            cmd.extend(["--max-budget-usd", str(self.config.claude_max_budget)])
        cmd.append("--dangerously-skip-permissions")

        env = os.environ.copy()
        env.pop("CLAUDECODE", None)

        logger.info("Executing: %s", " ".join(cmd[:5]) + " ...")
        self._add_log(LogLevel.SYSTEM, f"Running claude CLI (cwd: {self.config.target_project})", task_id)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # merge stderr → stdout (prevent deadlock)
                cwd=self.config.target_project,
                env=env,
            )
        except FileNotFoundError:
            self._add_log(LogLevel.ERROR, f"claude command not found: {self.config.claude_command}", task_id)
            return 1, "claude command not found", None

        self._proc = proc
        output_parts: list[str] = []
        cost: float | None = None

        async def read_stream():
            nonlocal cost
            assert proc.stdout
            async for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    # Non-JSON line (stderr or plain text)
                    self._add_log(LogLevel.CLAUDE, line[:500], task_id)
                    output_parts.append(line)
                    continue

                etype = event.get("type", "")

                if etype == "system":
                    # init event — log model info
                    model = event.get("model", "")
                    if model:
                        self._add_log(LogLevel.SYSTEM, f"Model: {model}", task_id)

                elif etype == "assistant":
                    # message is the full API response object: {content: [{type, text}], ...}
                    msg_obj = event.get("message", {})
                    if isinstance(msg_obj, dict):
                        content_blocks = msg_obj.get("content", [])
                        for block in content_blocks:
                            if isinstance(block, dict):
                                if block.get("type") == "text":
                                    text = block.get("text", "")
                                    if text:
                                        self._add_log(LogLevel.CLAUDE, text[:500], task_id)
                                        output_parts.append(text)
                                elif block.get("type") == "tool_use":
                                    tool_name = block.get("name", "")
                                    self._add_log(LogLevel.TOOL, f"Tool: {tool_name}", task_id)
                    elif isinstance(msg_obj, str) and msg_obj:
                        self._add_log(LogLevel.CLAUDE, msg_obj[:500], task_id)
                        output_parts.append(msg_obj)

                elif etype == "tool_use":
                    tool_name = event.get("tool", event.get("name", ""))
                    self._add_log(LogLevel.TOOL, f"Tool: {tool_name}", task_id)

                elif etype == "result":
                    result_text = str(event.get("result", "") or "")
                    cost = event.get("total_cost_usd") or event.get("cost_usd") or event.get("cost")
                    if result_text:
                        output_parts.append(result_text)
                        self._add_log(LogLevel.RESULT, result_text[:500], task_id)
                    cost_str = f" (${cost:.4f})" if cost else ""
                    duration = event.get("duration_ms")
                    dur_str = f" in {duration/1000:.1f}s" if duration else ""
                    self._add_log(LogLevel.SYSTEM, f"Claude finished{dur_str}{cost_str}", task_id)

                elif etype == "error":
                    err = str(event.get("error", event))
                    self._add_log(LogLevel.ERROR, err[:500], task_id)
                    output_parts.append(err)

                else:
                    # other events — log type for visibility
                    pass

        try:
            await asyncio.wait_for(read_stream(), timeout=600)
        except asyncio.TimeoutError:
            proc.kill()
            self._add_log(LogLevel.ERROR, "Claude process timed out (10min)", task_id)
            return 1, "timeout", cost
        except asyncio.CancelledError:
            proc.kill()
            return 1, "cancelled", cost

        await proc.wait()
        self._proc = None
        logger.info("Claude process exited: code=%s", proc.returncode)
        return proc.returncode or 0, "\n".join(output_parts), cost
