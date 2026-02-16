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

    async def start_loop(self, min_priority: int = 0) -> None:
        if self._loop_task and not self._loop_task.done():
            return
        self._stop_requested = False
        self._min_priority = min_priority
        self._state = AgentState.IDLE
        pri_label = {0:"All", 1:"Medium+", 2:"High+", 3:"Urgent"}
        self._add_log(LogLevel.SYSTEM, f"Agent loop started (priority: {pri_label.get(min_priority, min_priority)})")
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
                task = await self.db.pick_next_pending(min_priority=self._min_priority)
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

        branch_name = ""

        # ── Gitflow: create feature branch ──
        if self.config.gitflow:
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
            prompt = self._build_prompt(title, description)
            exit_code, output, cost = await self._run_claude(prompt, task_id)
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
                    await self._execute_task(task_id, title, description)
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
                pr_url = await self._create_pr(task_id, title, branch_name) or ""
                if pr_url:
                    await self.db.set_task_pr(task_id, pr_url)
            else:
                self._add_log(LogLevel.SYSTEM, "No changes to commit", task_id)

        # Approval gate
        if self.config.auto_approve:
            self._tasks_completed += 1
            # Gitflow: wait for code review, address comments, then merge
            if self.config.gitflow and pr_url and self.config.auto_merge:
                await self._wait_for_review_and_address(pr_url, branch_name, task_id, title)
                if self._stop_requested:
                    return
                await self._merge_pr(pr_url, task_id)
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

    async def _git(self, *args: str, task_id: int | None = None) -> tuple[int, str]:
        """Run git command in target_project directory."""
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=self.config.target_project,
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

    async def _create_pr(self, task_id: int, title: str, branch: str) -> str | None:
        """Create PR via gh CLI. Returns PR URL or None."""
        proc = await asyncio.create_subprocess_exec(
            "gh", "pr", "create",
            "--title", f"[Task #{task_id}] {title}",
            "--body", f"Auto-generated PR for Task #{task_id}.\n\nBranch: `{branch}`",
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

    async def _wait_for_review_and_address(self, pr_url: str, branch_name: str, task_id: int, title: str) -> None:
        """Wait for CodeRabbit review (max 10min), address actionable inline comments."""
        pr_number = pr_url.rstrip("/").split("/")[-1]
        max_wait = 600  # 10 minutes total
        poll_interval = 30  # check every 30 seconds
        elapsed = 0

        self._add_log(LogLevel.SYSTEM, f"Waiting for code review on PR #{pr_number} (max {max_wait//60}min)...", task_id)

        # Phase 1: Wait for inline review comments (not just walkthrough summary)
        review_comments: list[str] = []
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            if self._stop_requested:
                return

            # Fetch actionable inline comments (file-level, not PR summary)
            inline = await self._get_inline_review_comments(pr_number, task_id)
            # Also check review body for actionable content
            review_body = await self._get_review_body_comments(pr_number, task_id)
            comments = inline + review_body

            if comments:
                review_comments = comments
                self._add_log(LogLevel.SYSTEM, f"Found {len(comments)} actionable comment(s) after {elapsed}s", task_id)
                # Wait extra 30s — CodeRabbit may still be posting more inline comments
                self._add_log(LogLevel.SYSTEM, "Waiting 30s for additional comments...", task_id)
                await asyncio.sleep(30)
                elapsed += 30
                if self._stop_requested:
                    return
                # Re-fetch to catch any late comments
                inline2 = await self._get_inline_review_comments(pr_number, task_id)
                review_body2 = await self._get_review_body_comments(pr_number, task_id)
                review_comments = inline2 + review_body2
                self._add_log(LogLevel.SYSTEM, f"Final count: {len(review_comments)} actionable comment(s)", task_id)
                break

            if elapsed % 60 == 0:
                self._add_log(LogLevel.SYSTEM, f"Still waiting for review... ({elapsed}s/{max_wait}s)", task_id)

        if not review_comments:
            self._add_log(LogLevel.SYSTEM, "No actionable review comments, proceeding to merge", task_id)
            return

        # Address review comments (max 2 rounds)
        for round_num in range(1, 3):
            self._add_log(LogLevel.SYSTEM, f"Addressing review comments (round {round_num}): {len(review_comments)} comment(s)", task_id)

            # Build prompt from review comments
            review_prompt = self._build_review_prompt(title, review_comments, round_num)
            exit_code, output, cost = await self._run_claude(review_prompt, task_id)

            if exit_code != 0:
                self._add_log(LogLevel.ERROR, f"Review fix failed (exit={exit_code}), skipping", task_id)
                break

            # Commit and push fixes
            await self._git("add", "-A", task_id=task_id)
            rc, diff_stat = await self._git("diff", "--cached", "--stat", task_id=task_id)
            if diff_stat:
                await self._git("commit", "-m", f"[Task #{task_id}] Address review comments (round {round_num})", task_id=task_id)
                await self._git("push", "origin", branch_name, task_id=task_id)
                self._add_log(LogLevel.SYSTEM, f"Pushed review fixes (round {round_num})", task_id)
            else:
                self._add_log(LogLevel.SYSTEM, "No changes from review fix, skipping", task_id)
                break

            # Wait briefly for new review comments on the fix
            if round_num < 2:
                self._add_log(LogLevel.SYSTEM, "Waiting 60s for follow-up review...", task_id)
                await asyncio.sleep(60)
                if self._stop_requested:
                    return
                new_comments = await self._get_review_comments(pr_number, task_id)
                # Only continue if there are NEW comments (more than before)
                if not new_comments or len(new_comments) <= len(review_comments):
                    self._add_log(LogLevel.SYSTEM, "No new review comments, done addressing", task_id)
                    break
                review_comments = new_comments

    # Patterns to skip: walkthrough summaries, processing messages, tips
    _SKIP_PATTERNS = [
        "walkthrough",
        "processing",
        "in progress",
        "<!-- This is an auto-generated comment",
        "<!-- tips_start",
        "Thank you for using CodeRabbit",
        "📝 Walkthrough",
    ]

    async def _get_inline_review_comments(self, pr_number: str, task_id: int) -> list[str]:
        """Fetch inline (file-level) review comments — these are the actionable ones."""
        proc = await asyncio.create_subprocess_exec(
            "gh", "api", f"repos/:owner/:repo/pulls/{pr_number}/comments",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=self.config.target_project,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            return []

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
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
            stderr=asyncio.subprocess.STDOUT,
            cwd=self.config.target_project,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            return []

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
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
            if "actionable" in body_lower or "issue" in body_lower or "suggestion" in body_lower:
                comments.append(f"[{author} review]: {body}")

        return comments

    def _build_review_prompt(self, title: str, comments: list[str], round_num: int) -> str:
        """Build a prompt for Claude to address review comments."""
        comments_text = "\n\n---\n\n".join(comments)
        return (
            f"A code review was submitted for the changes in task: {title}\n\n"
            f"## Review Comments (round {round_num})\n\n{comments_text}\n\n"
            f"## Instructions\n"
            f"Read the review comments above carefully. For each comment:\n"
            f"1. If it's a valid suggestion/bug/improvement → fix the code\n"
            f"2. If it's a nitpick about style/naming → fix it if easy\n"
            f"3. If it's a question or praise → ignore (no action needed)\n"
            f"4. If it's about missing tests → add the tests\n\n"
            f"Make minimal, focused changes to address the review feedback. Do NOT refactor unrelated code.\n"
            f"Run the existing tests to make sure nothing breaks."
        )

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

    _MAX_CONTEXT_BYTES = 10 * 1024  # 10KB limit for injected context

    def _build_prompt(self, title: str, description: str) -> str:
        parts: list[str] = []

        # Inject project context files
        context = self._load_context_files()
        if context:
            parts.append(context)

        parts.append(title)
        if description:
            parts.append(description)
        return "\n\n".join(parts)

    def _load_context_files(self) -> str:
        """Read context_files from target_project and return combined text."""
        if not self.config.context_files:
            return ""

        base = Path(self.config.target_project)
        sections: list[str] = []
        total_size = 0

        for relpath in self.config.context_files:
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

        file_names = ", ".join(self.config.context_files)
        self._add_log(
            LogLevel.SYSTEM,
            f"Injected project context: {file_names} ({total_size} bytes)",
            self._current_task_id,
        )

        return f"[Project Context]\n{combined}\n[/Project Context]"

    async def _run_claude(self, prompt: str, task_id: int) -> tuple[int, str, float | None]:
        # Pass prompt via stdin (not CLI arg) to avoid OS arg length limits and hanging
        cmd = [self.config.claude_command, "-p", "--output-format", "stream-json", "--verbose"]
        if self.config.claude_model:
            cmd.extend(["--model", self.config.claude_model])
        if self.config.claude_max_budget:
            cmd.extend(["--max-budget-usd", str(self.config.claude_max_budget)])
        cmd.append("--dangerously-skip-permissions")

        env = os.environ.copy()
        env.pop("CLAUDECODE", None)

        logger.info("Executing: claude -p (stdin, %d chars)", len(prompt))
        self._add_log(LogLevel.SYSTEM, f"Running claude CLI (cwd: {self.config.target_project}, prompt: {len(prompt)} chars)", task_id)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # merge stderr → stdout (prevent deadlock)
                cwd=self.config.target_project,
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

        try:
            await asyncio.wait_for(read_stream(), timeout=1800)
        except asyncio.TimeoutError:
            proc.kill()
            self._add_log(LogLevel.ERROR, "Claude process timed out (30min)", task_id)
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
