"""Agent Worker — subprocess claude -p, 로그 스트리밍, 승인 게이트"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from collections import deque

from pathlib import Path

from app.config import AppConfig
from app.database import Database
from app.models import (
    AgentState,
    AgentStatus,
    LogEntry,
    LogLevel,
    PlanStatus,
    TaskPriority,
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
        self._min_priority: int = 0  # 0=all, 1=Med+, 2=High+, 3=Urgent only
        self._epic_id: int | None = None  # None=all epics, N=specific epic
        self._exec_lock = asyncio.Lock()  # serialize task execution

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
        ts = _now_iso()
        entry = LogEntry(
            index=self._log_index,
            timestamp=ts,
            level=level,
            message=message,
            task_id=task_id,
        )
        self._logs.append(entry)
        self._log_index += 1
        # Persist to DB (fire-and-forget)
        if task_id is not None:
            try:
                asyncio.get_event_loop().create_task(
                    self.db.insert_log(task_id, ts, level.value, message)
                )
            except Exception:
                pass  # never block on log persistence

    # ── Loop Control ──

    async def start_loop(self, min_priority: int = 0, epic_id: int | None = None) -> None:
        if self._loop_task and not self._loop_task.done():
            return
        self._stop_requested = False
        self._min_priority = min_priority
        self._epic_id = epic_id
        self._state = AgentState.IDLE
        pri_label = {0:"All", 1:"Medium+", 2:"High+", 3:"Urgent"}
        epic_label = f", epic #{epic_id}" if epic_id else ""
        self._add_log(LogLevel.SYSTEM, f"Agent loop started (priority: {pri_label.get(min_priority, min_priority)}{epic_label})")
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

    async def run_task(self, task_id: int) -> bool:
        """Execute a single task (blocks until complete). Returns False if agent is busy."""
        if self._exec_lock.locked():
            return False
        task = await self.db.get_task(task_id)
        if not task:
            return False
        if task.status not in (TaskStatus.PENDING, TaskStatus.FAILED):
            return False
        async with self._exec_lock:
            await self._execute_task(task_id, task.title, task.description)
        return True

    async def schedule_task(self, task_id: int) -> bool:
        """Schedule a task for background execution. Returns False if agent is busy."""
        if self._exec_lock.locked():
            return False
        task = await self.db.get_task(task_id)
        if not task:
            return False
        if task.status not in (TaskStatus.PENDING, TaskStatus.FAILED):
            return False
        bg = asyncio.create_task(self._run_task_with_lock(task_id, task.title, task.description))
        bg.add_done_callback(self._on_bg_task_done)
        return True

    async def _run_task_with_lock(self, task_id: int, title: str, description: str) -> None:
        async with self._exec_lock:
            await self._execute_task(task_id, title, description)

    def _on_bg_task_done(self, task: asyncio.Task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            logger.error("Background task failed: %s", exc)

    # ── Internal Loop ──

    async def _run_loop(self) -> None:
        try:
            while not self._stop_requested:
                task = await self.db.pick_next_pending(min_priority=self._min_priority, epic_id=self._epic_id)
                if not task:
                    self._state = AgentState.IDLE
                    await asyncio.sleep(self.config.poll_interval)
                    continue
                async with self._exec_lock:
                    await self._execute_task(task.id, task.title, task.description)
                if self._stop_requested:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            self._state = AgentState.STOPPED

    async def _execute_task(
        self,
        task_id: int,
        title: str,
        description: str,
        *,
        cwd_override: str | None = None,
        context_files_override: list[str] | None = None,
        prior_outputs: list[tuple[str, str]] | None = None,
    ) -> None:
        self._current_task_id = task_id
        self._current_task_title = title
        self._current_output = ""
        self._state = AgentState.RUNNING

        run_cwd = cwd_override or self.config.target_project
        branch_name = ""

        # ── Gitflow: create feature branch ──
        if self.config.gitflow and not cwd_override:
            branch_name = await self._create_branch(task_id, title) or ""
            if not branch_name:
                self._tasks_failed += 1
                await self.db.set_task_failed(task_id, "Failed to create feature branch")
                self._state = AgentState.IDLE
                self._current_task_id = None
                self._current_task_title = None
                return

        await self.db.set_task_started(task_id, branch_name=branch_name)
        self._add_log(LogLevel.SYSTEM, f"Starting task #{task_id}: {title}", task_id)
        logger.info("Starting task #%d: %s", task_id, title)

        try:
            prompt = self._build_prompt(
                title,
                description,
                context_dir=cwd_override,
                context_files=context_files_override,
                prior_outputs=prior_outputs,
            )
            exit_code, output, cost = await self._run_claude(prompt, task_id, cwd=cwd_override)
        except Exception as exc:
            logger.exception("Unexpected error running task #%d", task_id)
            self._tasks_failed += 1
            await self.db.set_task_failed(task_id, str(exc)[:2000])
            self._add_log(LogLevel.ERROR, f"Task #{task_id} crashed: {exc}", task_id)
            if self.config.gitflow and branch_name:
                await self._cleanup_branch(branch_name, task_id)
            self._state = AgentState.IDLE
            self._current_task_id = None
            self._current_task_title = None
            return

        self._current_output = output
        logger.info("Task #%d finished: exit=%d, output=%d chars, cost=%s", task_id, exit_code, len(output), cost)

        if self._stop_requested:
            return

        if exit_code != 0:
            # ── Auto-retry logic ──
            task = await self.db.get_task(task_id)
            current_retries = task.retry_count if task else 0
            if current_retries < self.config.max_retries and not self._stop_requested:
                new_count = await self.db.increment_retry_count(task_id)
                backoff = self.config.retry_backoff_sec * (2 ** (new_count - 1))
                self._add_log(
                    LogLevel.SYSTEM,
                    f"Task #{task_id} failed (exit={exit_code}), retrying {new_count}/{self.config.max_retries} after {backoff}s backoff",
                    task_id,
                )
                if self.config.gitflow and branch_name:
                    await self._cleanup_branch(branch_name, task_id)
                await asyncio.sleep(backoff)
                if not self._stop_requested:
                    await self._execute_task(
                        task_id, title, description,
                        cwd_override=cwd_override,
                        context_files_override=context_files_override,
                        prior_outputs=prior_outputs,
                    )
                return

            self._state = AgentState.IDLE
            self._tasks_failed += 1
            await self.db.set_task_failed(task_id, output[-2000:] if output else "Process failed")
            self._add_log(
                LogLevel.ERROR,
                f"Task #{task_id} failed (exit={exit_code}) after {current_retries} retries",
                task_id,
            )
            if self.config.gitflow and branch_name:
                await self._cleanup_branch(branch_name, task_id)
            self._current_task_id = None
            self._current_task_title = None
            return

        # ── Gitflow: commit + push + create PR ──
        pr_url = ""
        if self.config.gitflow and branch_name:
            await self._git("add", "-A", task_id=task_id)
            rc, diff_stat = await self._git("diff", "--cached", "--stat", task_id=task_id)
            if diff_stat:
                await self._git("commit", "-m", f"[Task #{task_id}] {title}", task_id=task_id)
                await self._git("push", "-u", "origin", branch_name, task_id=task_id)
                pr_url = await self._create_pr(
                    task_id, title, branch_name,
                    description=description, diff_stat=diff_stat, cost=cost,
                ) or ""
                if pr_url:
                    await self.db.set_task_pr(task_id, pr_url)
            else:
                self._add_log(LogLevel.SYSTEM, "No changes to commit", task_id)

        # Approval gate
        if self.config.auto_approve:
            self._tasks_completed += 1
            # Gitflow: wait for code review, address comments, then merge
            if self.config.gitflow and pr_url and self.config.auto_merge:
                await self._merge_pr(pr_url, task_id)
                # 백그라운드에서 리뷰 수집 → 개선 백로그 태스크 생성
                self._schedule_review_followup(pr_url, task_id, title)
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
                # Gitflow: merge PR on approval
                if self.config.gitflow and pr_url:
                    merged = await self._merge_pr(pr_url, task_id)
                    if not merged:
                        self._add_log(LogLevel.ERROR, "PR merge failed — resolve conflicts manually", task_id)
                await self.db.set_task_done(task_id)
                self._add_log(LogLevel.SYSTEM, f"Task #{task_id} approved", task_id)
            else:
                self._tasks_failed += 1
                await self.db.set_task_rejected(task_id, self._rejection_feedback)
                self._add_log(LogLevel.SYSTEM, f"Task #{task_id} rejected: {self._rejection_feedback}", task_id)
                # Gitflow: cleanup branch on rejection
                if self.config.gitflow and branch_name:
                    await self._cleanup_branch(branch_name, task_id)

        self._state = AgentState.IDLE
        self._current_task_id = None
        self._current_task_title = None

    # ── Git Helpers ──

    async def _git(self, *args: str, task_id: int | None = None, cwd: str | None = None) -> tuple[int, str]:
        """Run git command in target_project directory."""
        run_cwd = cwd or self.config.target_project
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=run_cwd,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0 and task_id:
            self._add_log(LogLevel.ERROR, f"git {args[0]} failed: {output}", task_id)
        return proc.returncode, output

    def _slugify(self, title: str) -> str:
        """Convert task title to branch-safe slug."""
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()
        slug = re.sub(r"-+", "-", slug)
        return slug[:40].rstrip("-")

    async def _create_branch(self, task_id: int, title: str) -> str | None:
        """Checkout base branch, pull, create feature branch. Returns branch name or None on failure."""
        base = self.config.base_branch
        prefix = self.config.branch_prefix
        slug = self._slugify(title)
        branch = f"{prefix}/task-{task_id}-{slug}"

        # Checkout base and pull latest
        rc, _ = await self._git("checkout", base, task_id=task_id)
        if rc != 0:
            return None
        await self._git("pull", "--ff-only", task_id=task_id)

        # Create and checkout feature branch
        rc, _ = await self._git("checkout", "-b", branch, task_id=task_id)
        if rc != 0:
            return None

        self._add_log(LogLevel.SYSTEM, f"Created branch: {branch}", task_id)
        return branch

    async def _build_pr_body(
        self,
        task_id: int,
        branch: str,
        *,
        description: str = "",
        diff_stat: str = "",
        cost: float | None = None,
    ) -> str:
        """Build a rich PR body from task metadata."""
        _PRIORITY_LABELS = {
            TaskPriority.LOW: "Low",
            TaskPriority.MEDIUM: "Medium",
            TaskPriority.HIGH: "High",
            TaskPriority.URGENT: "Urgent",
        }
        task = await self.db.get_task(task_id)
        sections: list[str] = []

        # Summary
        if description:
            summary = description[:1000]
            sections.append(f"## Summary\n{summary}")

        # Changes
        if diff_stat:
            sections.append(f"## Changes\n```\n{diff_stat}\n```")

        # Details table
        rows: list[str] = []
        if task:
            rows.append(f"| Priority | {_PRIORITY_LABELS.get(task.priority, 'Medium')} |")
            if task.labels:
                rows.append(f"| Labels | {', '.join(task.labels)} |")
            if task.epic_id:
                epic = await self.db.get_epic(task.epic_id)
                if epic:
                    rows.append(f"| Epic | #{epic.id} {epic.title} |")
        if cost is not None:
            rows.append(f"| Cost | ${cost:.4f} |")
        rows.append(f"| Branch | `{branch}` |")

        table_header = "| Field | Value |\n|-------|-------|"
        sections.append(f"## Details\n{table_header}\n" + "\n".join(rows))

        sections.append("---\n🤖 Generated by [Claude Pilot](https://github.com/seonghyeoklee/claude-pilot)")

        return "\n\n".join(sections)

    async def _create_pr(
        self,
        task_id: int,
        title: str,
        branch: str,
        *,
        description: str = "",
        diff_stat: str = "",
        cost: float | None = None,
    ) -> str | None:
        """Create PR via gh CLI. Returns PR URL or None."""
        body = await self._build_pr_body(
            task_id, branch,
            description=description, diff_stat=diff_stat, cost=cost,
        )
        proc = await asyncio.create_subprocess_exec(
            "gh", "pr", "create",
            "--title", f"[Task #{task_id}] {title}",
            "--body", body,
            "--base", self.config.base_branch,
            "--head", branch,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=self.config.target_project,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            self._add_log(LogLevel.ERROR, f"gh pr create failed: {output}", task_id)
            return None
        # gh pr create outputs the PR URL
        pr_url = output.strip().split("\n")[-1]
        self._add_log(LogLevel.SYSTEM, f"PR created: {pr_url}", task_id)
        return pr_url

    def _schedule_review_followup(self, pr_url: str, task_id: int, title: str) -> None:
        """Fire-and-forget: poll for review comments after merge and create backlog task."""
        asyncio.create_task(self._poll_and_create_review_task(pr_url, task_id, title))

    async def _poll_and_create_review_task(self, pr_url: str, task_id: int, title: str) -> None:
        """Background: collect review comments and create a backlog task if actionable."""
        pr_number = pr_url.rstrip("/").split("/")[-1]
        initial_wait = 180  # 3 min — give CodeRabbit time to post
        poll_interval = 30
        max_poll = 420  # 7 min additional polling (total ~10 min)

        self._add_log(LogLevel.SYSTEM, f"Background review polling for PR #{pr_number} (initial wait {initial_wait}s)", task_id)

        try:
            await asyncio.sleep(initial_wait)

            review_comments: list[str] = []
            elapsed = 0
            while elapsed < max_poll:
                inline = await self._get_inline_review_comments(pr_number, task_id)
                review_body = await self._get_review_body_comments(pr_number, task_id)
                comments = inline + review_body

                if comments:
                    # Wait extra 30s for late-arriving comments then re-fetch
                    await asyncio.sleep(30)
                    inline2 = await self._get_inline_review_comments(pr_number, task_id)
                    review_body2 = await self._get_review_body_comments(pr_number, task_id)
                    review_comments = inline2 + review_body2
                    self._add_log(
                        LogLevel.SYSTEM,
                        f"Review poll: found {len(review_comments)} actionable comment(s) for PR #{pr_number}",
                        task_id,
                    )
                    break

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            if not review_comments:
                self._add_log(LogLevel.SYSTEM, f"No actionable review comments for PR #{pr_number}", task_id)
                return

            # Look up original task's epic_id
            original_task = await self.db.get_task(task_id)
            epic_id = original_task.epic_id if original_task else None

            # Build description with review comments
            comments_md = "\n\n".join(f"- {c}" for c in review_comments)
            description = (
                f"Code review comments from PR: {pr_url}\n\n"
                f"## Review Comments\n\n{comments_md}"
            )

            from app.models import TaskCreate as _TC
            new_task = await self.db.create_task(_TC(
                title=f"[Review] {title}",
                description=description,
                priority=TaskPriority.LOW,
                labels=["review"],
                epic_id=epic_id,
            ))
            self._add_log(
                LogLevel.SYSTEM,
                f"Created review backlog task #{new_task.id} for PR #{pr_number} ({len(review_comments)} comments)",
                task_id,
            )

        except Exception as exc:
            logger.error("Review followup failed for PR %s: %s", pr_url, exc)

    # Patterns to skip: walkthrough summaries, processing messages, tips
    _SKIP_PATTERNS = [
        "walkthrough",
        "processing",
        "in progress",
        "<!-- tips_start",
        "Thank you for using CodeRabbit",
        "📝 Walkthrough",
    ]

    async def _get_inline_review_comments(self, pr_number: str, task_id: int) -> list[str]:
        """Fetch inline (file-level) review comments — these are the actionable ones."""
        proc = await asyncio.create_subprocess_exec(
            "gh", "api", f"repos/:owner/:repo/pulls/{pr_number}/comments",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.config.target_project,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            self._add_log(LogLevel.ERROR, f"gh api pulls/comments failed (rc={proc.returncode}): {err[:200]}", task_id)
            return []

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            self._add_log(LogLevel.ERROR, f"gh api pulls/comments JSON parse failed: {output[:200]}", task_id)
            return []

        comments: list[str] = []
        for c in data:
            body = c.get("body", "")
            author = c.get("user", {}).get("login", "")
            path = c.get("path", "")
            if not body or not body.strip():
                continue
            # Skip non-actionable patterns
            if any(pat.lower() in body.lower() for pat in self._SKIP_PATTERNS):
                continue
            comments.append(f"[{author} on {path}]: {body}")

        return comments

    async def _get_review_body_comments(self, pr_number: str, task_id: int) -> list[str]:
        """Fetch review-level comments (the summary posted with 'Actionable comments posted: N')."""
        proc = await asyncio.create_subprocess_exec(
            "gh", "pr", "view", pr_number, "--json", "reviews",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.config.target_project,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            self._add_log(LogLevel.ERROR, f"gh pr view reviews failed (rc={proc.returncode}): {err[:200]}", task_id)
            return []

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            self._add_log(LogLevel.ERROR, f"gh pr view reviews JSON parse failed: {output[:200]}", task_id)
            return []

        comments: list[str] = []
        for r in data.get("reviews", []):
            body = r.get("body", "")
            author = r.get("author", {}).get("login", "")
            if not body or not body.strip():
                continue
            # Only include reviews with actionable content
            body_lower = body.lower()
            if "actionable comments posted: 0" in body_lower:
                continue
            if any(pat.lower() in body_lower for pat in self._SKIP_PATTERNS):
                continue
            # Any non-empty review body that passed skip/zero-actionable filters is worth processing
            comments.append(f"[{author} review]: {body}")

        return comments

    async def _merge_pr(self, pr_url: str, task_id: int) -> bool:
        """Merge PR via gh CLI."""
        proc = await asyncio.create_subprocess_exec(
            "gh", "pr", "merge", pr_url, "--merge", "--delete-branch",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=self.config.target_project,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            self._add_log(LogLevel.ERROR, f"gh pr merge failed: {output}", task_id)
            return False
        self._add_log(LogLevel.SYSTEM, f"PR merged: {pr_url}", task_id)
        # Return to base branch
        await self._git("checkout", self.config.base_branch, task_id=task_id)
        await self._git("pull", "--ff-only", task_id=task_id)
        return True

    async def _cleanup_branch(self, branch: str, task_id: int) -> None:
        """Return to base branch on failure."""
        await self._git("checkout", self.config.base_branch, task_id=task_id)
        await self._git("branch", "-D", branch, task_id=task_id)

    # ── Plan Decomposition + Execution ──

    async def decompose_plan(self, plan_id: int) -> bool:
        """Use Claude to decompose a plan's spec into tasks. Returns True on success."""
        plan = await self.db.get_plan(plan_id)
        if not plan:
            return False

        await self.db.set_plan_status(plan_id, PlanStatus.DECOMPOSING)
        self._add_log(LogLevel.SYSTEM, f"Decomposing plan #{plan_id}: {plan.title}")

        # Build context from each target's CLAUDE.md / context_files
        target_context_parts: list[str] = []
        for target_name, target_cfg in plan.targets.items():
            project_path = target_cfg.get("project", "")
            ctx_files = target_cfg.get("context_files", ["CLAUDE.md"])
            if project_path:
                base = Path(project_path)
                for cf in ctx_files:
                    fp = base / cf
                    try:
                        content = fp.read_text(encoding="utf-8")
                        target_context_parts.append(f"### Target: {target_name} — {cf}\n{content}")
                    except (OSError, UnicodeDecodeError):
                        continue

        target_context = "\n\n".join(target_context_parts)
        target_names = ", ".join(plan.targets.keys()) if plan.targets else "(default)"

        system_prompt = (
            "You are a project planner. Given a specification and target project contexts, "
            "decompose the spec into ordered implementation tasks.\n\n"
            "RULES:\n"
            "- Each task must have: title, description, target (which project)\n"
            "- Tasks should be ordered logically (dependencies first)\n"
            "- Be specific and actionable — each task should be completable in one Claude Code session\n"
            "- Output ONLY valid JSON array, no other text\n\n"
            f"Available targets: {target_names}\n\n"
        )

        if target_context:
            system_prompt += f"[Target Project Contexts]\n{target_context[:8000]}\n[/Target Project Contexts]\n\n"

        full_prompt = (
            f"{system_prompt}"
            f"## Specification\n\n{plan.spec}\n\n"
            f"## Output Format\n\n"
            f'Respond with ONLY a JSON array:\n'
            f'[{{"title": "...", "description": "...", "target": "..."}}]\n'
        )

        # Use first target's project as cwd, or temp dir
        first_target = next(iter(plan.targets.values()), {})
        cwd = first_target.get("project", "") or None

        try:
            exit_code, output, cost = await self._run_claude(full_prompt, 0, cwd=cwd)
        except Exception as exc:
            self._add_log(LogLevel.ERROR, f"Plan decomposition failed: {exc}")
            await self.db.set_plan_status(plan_id, PlanStatus.DRAFT)
            return False

        if exit_code != 0:
            self._add_log(LogLevel.ERROR, f"Plan decomposition failed (exit={exit_code})")
            await self.db.set_plan_status(plan_id, PlanStatus.DRAFT)
            return False

        # Parse JSON from output
        tasks_data = self._parse_json_from_output(output)
        if not tasks_data:
            self._add_log(LogLevel.ERROR, "Failed to parse tasks JSON from decomposition output")
            await self.db.set_plan_status(plan_id, PlanStatus.DRAFT)
            return False

        # Create tasks in DB (inherit epic_id from plan)
        for order, td in enumerate(tasks_data):
            title = td.get("title", f"Task {order + 1}")
            desc = td.get("description", "")
            target = td.get("target", "")
            await self.db.create_plan_task(plan_id, title, desc, target, order, epic_id=plan.epic_id)

        self._add_log(LogLevel.SYSTEM, f"Plan #{plan_id} decomposed into {len(tasks_data)} tasks")
        await self.db.set_plan_status(plan_id, PlanStatus.REVIEWING)
        return True

    def _parse_json_from_output(self, output: str) -> list[dict] | None:
        """Extract JSON array from Claude output text."""
        import re

        # Try direct parse first
        try:
            data = json.loads(output.strip())
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, ValueError):
            pass

        # Try extracting content from first markdown code fence (```json ... ```)
        fence_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n```', output)
        if fence_match:
            try:
                data = json.loads(fence_match.group(1).strip())
                if isinstance(data, list):
                    return data
            except (json.JSONDecodeError, ValueError):
                pass

        # Try to find first valid JSON array in output
        # Use balanced bracket counting to find the array boundary
        start = output.find('[')
        while start != -1:
            depth = 0
            in_string = False
            escape = False
            for i in range(start, len(output)):
                c = output[i]
                if escape:
                    escape = False
                    continue
                if c == '\\' and in_string:
                    escape = True
                    continue
                if c == '"' and not escape:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == '[':
                    depth += 1
                elif c == ']':
                    depth -= 1
                    if depth == 0:
                        candidate = output[start:i + 1]
                        try:
                            data = json.loads(candidate)
                            if isinstance(data, list):
                                return data
                        except (json.JSONDecodeError, ValueError):
                            break
            start = output.find('[', start + 1)

        return None

    async def run_plan(self, plan_id: int) -> bool:
        """Execute all tasks in a plan sequentially. Returns True on success."""
        plan = await self.db.get_plan(plan_id)
        if not plan:
            return False

        await self.db.set_plan_status(plan_id, PlanStatus.RUNNING)
        self._add_log(LogLevel.SYSTEM, f"Running plan #{plan_id}: {plan.title}")

        prior_outputs: list[tuple[str, str]] = []

        while not self._stop_requested:
            task = await self.db.pick_next_plan_task(plan_id)
            if not task:
                break

            # Resolve target config
            target_cfg = plan.targets.get(task.target, {})
            cwd = target_cfg.get("project", "") or None
            ctx_files = target_cfg.get("context_files") if target_cfg else None

            self._add_log(
                LogLevel.SYSTEM,
                f"Plan #{plan_id} — executing task #{task.id}: {task.title} (target: {task.target or 'default'})",
            )

            async with self._exec_lock:
                await self._execute_task(
                    task.id,
                    task.title,
                    task.description,
                    cwd_override=cwd,
                    context_files_override=ctx_files,
                    prior_outputs=prior_outputs if prior_outputs else None,
                )

            # Check result
            completed_task = await self.db.get_task(task.id)
            if not completed_task or completed_task.status == TaskStatus.FAILED:
                self._add_log(LogLevel.ERROR, f"Plan #{plan_id} failed at task #{task.id}")
                await self.db.set_plan_status(plan_id, PlanStatus.FAILED)
                return False

            # Accumulate output for context chaining
            if completed_task.output:
                prior_outputs.append((completed_task.title, completed_task.output[-3000:]))

        if self._stop_requested:
            self._add_log(LogLevel.SYSTEM, f"Plan #{plan_id} stopped by user")
            return False

        self._add_log(LogLevel.SYSTEM, f"Plan #{plan_id} completed successfully")
        await self.db.set_plan_status(plan_id, PlanStatus.COMPLETED)
        return True

    _MAX_CONTEXT_BYTES = 10 * 1024  # 10KB limit for injected context

    def _build_prompt(
        self,
        title: str,
        description: str,
        *,
        context_dir: str | None = None,
        context_files: list[str] | None = None,
        prior_outputs: list[tuple[str, str]] | None = None,
    ) -> str:
        parts: list[str] = []

        # Inject project context files
        ctx_dir = context_dir or self.config.target_project
        ctx_files = context_files if context_files is not None else self.config.context_files
        context = self._load_context_files(base_dir=ctx_dir, files=ctx_files)
        if context:
            parts.append(context)

        # Inject prior task outputs (context chaining)
        if prior_outputs:
            chain_parts: list[str] = []
            for ptitle, poutput in prior_outputs:
                chain_parts.append(f"### {ptitle}\n{poutput}")
            chain = "\n\n---\n\n".join(chain_parts)
            parts.append(f"[Prior Task Outputs]\n{chain}\n[/Prior Task Outputs]")

        parts.append(title)
        if description:
            parts.append(description)
        return "\n\n".join(parts)

    def _load_context_files(
        self, *, base_dir: str = "", files: list[str] | None = None
    ) -> str:
        """Read context_files from base_dir and return combined text."""
        file_list = files if files is not None else self.config.context_files
        if not file_list:
            return ""

        base = Path(base_dir) if base_dir else Path(self.config.target_project)
        sections: list[str] = []
        total_size = 0

        for relpath in file_list:
            filepath = base / relpath
            try:
                content = filepath.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue  # skip missing or unreadable files

            total_size += len(content.encode("utf-8"))
            sections.append(f"# {relpath}\n{content}")

        if not sections:
            return ""

        combined = "\n\n".join(sections)

        if total_size > self._MAX_CONTEXT_BYTES:
            # Truncate to limit and add notice
            truncated = combined[: self._MAX_CONTEXT_BYTES]
            combined = truncated + "\n\n... (context truncated, exceeded 10KB limit)"
            self._add_log(
                LogLevel.SYSTEM,
                f"Project context truncated ({total_size} bytes > 10KB limit)",
                self._current_task_id,
            )

        file_names = ", ".join(file_list)
        self._add_log(
            LogLevel.SYSTEM,
            f"Injected project context: {file_names} ({total_size} bytes)",
            self._current_task_id,
        )

        return f"[Project Context]\n{combined}\n[/Project Context]"

    async def _run_claude(self, prompt: str, task_id: int, *, cwd: str | None = None) -> tuple[int, str, float | None]:
        # Pass prompt via stdin (not CLI arg) to avoid OS arg length limits and hanging
        cmd = [self.config.claude_command, "-p", "--output-format", "stream-json", "--verbose"]
        if self.config.claude_model:
            cmd.extend(["--model", self.config.claude_model])
        if self.config.claude_max_budget:
            cmd.extend(["--max-budget-usd", str(self.config.claude_max_budget)])
        cmd.append("--dangerously-skip-permissions")

        run_cwd = cwd or self.config.target_project
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)

        logger.info("Executing: claude -p (stdin, %d chars)", len(prompt))
        self._add_log(LogLevel.SYSTEM, f"Running claude CLI (cwd: {run_cwd}, prompt: {len(prompt)} chars)", task_id)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # merge stderr → stdout (prevent deadlock)
                cwd=run_cwd,
                env=env,
                limit=4 * 1024 * 1024,  # 4MB line buffer (default 64KB too small for large stream-json)
            )
        except FileNotFoundError:
            self._add_log(LogLevel.ERROR, f"claude command not found: {self.config.claude_command}", task_id)
            return 1, "claude command not found", None

        self._proc = proc
        # Feed prompt via stdin and close
        proc.stdin.write(prompt.encode("utf-8"))
        await proc.stdin.drain()
        proc.stdin.close()

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

        timeout_sec = self.config.claude_timeout_sec
        try:
            await asyncio.wait_for(read_stream(), timeout=timeout_sec)
        except asyncio.TimeoutError:
            proc.kill()
            self._add_log(LogLevel.ERROR, f"Claude process timed out after {timeout_sec}s ({timeout_sec // 60}min)", task_id)
            return 1, "timeout", cost
        except asyncio.LimitOverrunError:
            # Stream line exceeded buffer limit — drain and continue
            self._add_log(LogLevel.ERROR, "Stream buffer overflow (line too long), draining...", task_id)
            if proc.stdout:
                try:
                    await proc.stdout.read()  # drain remaining data
                except Exception:
                    pass
            proc.kill()
            return 1, "stream buffer overflow", cost
        except asyncio.CancelledError:
            proc.kill()
            return 1, "cancelled", cost

        await proc.wait()
        self._proc = None
        logger.info("Claude process exited: code=%s", proc.returncode)
        return proc.returncode or 0, "\n".join(output_parts), cost
