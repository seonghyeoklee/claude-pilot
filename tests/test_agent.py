"""Agent Worker tests (mock subprocess)"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.agent import AgentWorker
from app.config import AppConfig
from app.database import Database
from app.models import AgentState, LogLevel, TaskCreate, TaskStatus


@pytest.fixture
async def setup():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.init()
        config = AppConfig(target_project=tmp, auto_approve=True)
        agent = AgentWorker(config, db)
        yield agent, db, config
        await agent.stop_loop()
        await db.close()


def _make_mock_process(stdout_lines: list[str], returncode: int = 0):
    """Create a mock async process with given stdout lines."""
    proc = AsyncMock()
    proc.returncode = returncode
    proc.kill = AsyncMock()
    proc.wait = AsyncMock()

    async def _readline_gen():
        for line in stdout_lines:
            yield (line + "\n").encode()

    proc.stdout = _readline_gen()
    proc.stderr = AsyncMock()
    proc.stderr.__aiter__ = AsyncMock(return_value=iter([]))
    return proc


async def test_status_initial(setup):
    agent, _, _ = setup
    s = agent.get_status()
    assert s.state == AgentState.STOPPED
    assert s.loop_running is False


async def test_logs_empty(setup):
    agent, _, _ = setup
    assert agent.get_logs() == []


async def test_log_after_index(setup):
    agent, _, _ = setup
    agent._add_log(LogLevel.SYSTEM, "A")
    agent._add_log(LogLevel.SYSTEM, "B")
    logs = agent.get_logs(after_index=1)
    assert len(logs) == 1
    assert logs[0].message == "B"


async def test_approve_when_not_waiting(setup):
    agent, _, _ = setup
    assert agent.approve() is False


async def test_reject_when_not_waiting(setup):
    agent, _, _ = setup
    assert agent.reject("bad") is False


@patch("app.agent.asyncio.create_subprocess_exec")
async def test_run_task_auto_approve(mock_exec, setup):
    agent, db, _ = setup
    task = await db.create_task(TaskCreate(title="Test task"))

    stdout = [
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Working on it..."}]}}),
        json.dumps({"type": "result", "result": "Done!", "total_cost_usd": 0.01}),
    ]
    mock_exec.return_value = _make_mock_process(stdout, returncode=0)

    await agent.run_task(task.id)

    t = await db.get_task(task.id)
    assert t.status == TaskStatus.DONE
    assert agent._tasks_completed == 1


@patch("app.agent.asyncio.create_subprocess_exec")
async def test_run_task_failure(mock_exec, setup):
    agent, db, _ = setup
    task = await db.create_task(TaskCreate(title="Fail task"))

    stdout = [json.dumps({"type": "error", "error": "Something broke"})]
    mock_exec.return_value = _make_mock_process(stdout, returncode=1)

    await agent.run_task(task.id)

    t = await db.get_task(task.id)
    assert t.status == TaskStatus.FAILED
    assert agent._tasks_failed == 1


@patch("app.agent.asyncio.create_subprocess_exec")
async def test_approval_gate(mock_exec):
    """Test manual approval flow."""
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.init()
        config = AppConfig(target_project=tmp, auto_approve=False)
        agent = AgentWorker(config, db)

        task = await db.create_task(TaskCreate(title="Needs review"))

        stdout = [json.dumps({"type": "result", "result": "Changes made", "total_cost_usd": 0.02})]
        mock_exec.return_value = _make_mock_process(stdout, returncode=0)

        # Run in background
        run_coro = asyncio.create_task(agent.run_task(task.id))

        # Wait for approval state
        for _ in range(50):
            await asyncio.sleep(0.05)
            if agent._state == AgentState.WAITING_APPROVAL:
                break

        assert agent._state == AgentState.WAITING_APPROVAL

        # Approve
        assert agent.approve()
        await run_coro

        t = await db.get_task(task.id)
        assert t.status == TaskStatus.DONE
        await db.close()


@patch("app.agent.asyncio.create_subprocess_exec")
async def test_rejection_flow(mock_exec):
    """Test rejection sends task back to pending."""
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.init()
        config = AppConfig(target_project=tmp, auto_approve=False)
        agent = AgentWorker(config, db)

        task = await db.create_task(TaskCreate(title="Needs fix"))

        stdout = [json.dumps({"type": "result", "result": "Done", "total_cost_usd": 0.01})]
        mock_exec.return_value = _make_mock_process(stdout, returncode=0)

        run_coro = asyncio.create_task(agent.run_task(task.id))

        for _ in range(50):
            await asyncio.sleep(0.05)
            if agent._state == AgentState.WAITING_APPROVAL:
                break

        assert agent.reject("Add error handling")
        await run_coro

        t = await db.get_task(task.id)
        assert t.status == TaskStatus.PENDING
        assert t.rejection_feedback == "Add error handling"
        await db.close()


@patch("app.agent.asyncio.create_subprocess_exec")
async def test_loop_start_stop(mock_exec, setup):
    agent, db, _ = setup

    await agent.start_loop()
    assert agent.get_status().loop_running is True

    await asyncio.sleep(0.1)
    await agent.stop_loop()
    assert agent.get_status().state == AgentState.STOPPED


async def test_build_prompt(setup):
    agent, _, _ = setup
    p = agent._build_prompt("Fix bug", "In login module")
    assert "Fix bug" in p
    assert "In login module" in p


async def test_build_prompt_no_desc(setup):
    agent, _, _ = setup
    p = agent._build_prompt("Fix bug", "")
    assert p == "Fix bug"


async def test_build_prompt_with_context_files(setup):
    """Context files are injected before the task prompt."""
    agent, _, config = setup
    tmp = config.target_project

    # Create context files in the temp dir
    Path(tmp, "CLAUDE.md").write_text("# My Project\nBuild instructions here.")
    Path(tmp, "pyproject.toml").write_text('[project]\nname = "demo"')
    config.context_files = ["CLAUDE.md", "pyproject.toml"]

    p = agent._build_prompt("Fix bug", "In login module")
    assert "[Project Context]" in p
    assert "# My Project" in p
    assert "Build instructions here." in p
    assert '[project]\nname = "demo"' in p
    assert "Fix bug" in p
    assert "In login module" in p
    # Context should come before the task
    ctx_pos = p.index("[Project Context]")
    task_pos = p.index("Fix bug")
    assert ctx_pos < task_pos


async def test_build_prompt_missing_context_file(setup):
    """Missing context files are silently skipped."""
    agent, _, config = setup
    config.context_files = ["nonexistent.md", "also-missing.toml"]

    p = agent._build_prompt("Fix bug", "")
    assert p == "Fix bug"
    assert "[Project Context]" not in p


async def test_build_prompt_partial_context_files(setup):
    """Only existing files are included; missing ones skipped."""
    agent, _, config = setup
    tmp = config.target_project
    Path(tmp, "CLAUDE.md").write_text("# Rules\nFollow these.")
    config.context_files = ["CLAUDE.md", "missing.txt"]

    p = agent._build_prompt("Do work", "")
    assert "[Project Context]" in p
    assert "# Rules" in p
    assert "missing.txt" not in p


async def test_build_prompt_context_truncation(setup):
    """Context exceeding 10KB is truncated."""
    agent, _, config = setup
    tmp = config.target_project
    # Create a file larger than 10KB
    big_content = "x" * 12000
    Path(tmp, "big.md").write_text(big_content)
    config.context_files = ["big.md"]

    p = agent._build_prompt("Task", "")
    assert "truncated" in p
    # Verify log recorded truncation
    logs = agent.get_logs()
    trunc_logs = [l for l in logs if "truncated" in l.message.lower()]
    assert len(trunc_logs) >= 1


async def test_build_prompt_context_log(setup):
    """Context injection is logged with file names and size."""
    agent, _, config = setup
    tmp = config.target_project
    Path(tmp, "CLAUDE.md").write_text("Hello")
    config.context_files = ["CLAUDE.md"]

    agent._build_prompt("Task", "")

    logs = agent.get_logs()
    ctx_logs = [l for l in logs if "injected project context" in l.message.lower()]
    assert len(ctx_logs) == 1
    assert "CLAUDE.md" in ctx_logs[0].message


async def test_build_prompt_empty_context_files(setup):
    """Empty context_files list produces no context section."""
    agent, _, config = setup
    config.context_files = []

    p = agent._build_prompt("Fix bug", "Details")
    assert "[Project Context]" not in p
    assert "Fix bug" in p
    assert "Details" in p


@patch("app.agent.asyncio.create_subprocess_exec")
async def test_claude_not_found(mock_exec, setup):
    agent, db, _ = setup
    mock_exec.side_effect = FileNotFoundError()

    task = await db.create_task(TaskCreate(title="No claude"))
    await agent.run_task(task.id)

    t = await db.get_task(task.id)
    assert t.status == TaskStatus.FAILED
    logs = agent.get_logs()
    assert any("not found" in l.message for l in logs)


@patch("app.agent.asyncio.sleep", new_callable=AsyncMock)
@patch("app.agent.asyncio.create_subprocess_exec")
async def test_retry_then_success(mock_exec, mock_sleep, setup):
    """Task fails once, retries, then succeeds on 2nd attempt."""
    agent, db, config = setup
    config.max_retries = 2
    config.retry_backoff_sec = 5
    task = await db.create_task(TaskCreate(title="Flaky task"))

    fail_stdout = [json.dumps({"type": "error", "error": "Transient error"})]
    success_stdout = [json.dumps({"type": "result", "result": "Done!", "total_cost_usd": 0.01})]

    # First call fails, second succeeds
    mock_exec.side_effect = [
        _make_mock_process(fail_stdout, returncode=1),
        _make_mock_process(success_stdout, returncode=0),
    ]

    await agent.run_task(task.id)

    t = await db.get_task(task.id)
    assert t.status == TaskStatus.DONE
    assert t.retry_count == 1
    assert agent._tasks_completed == 1
    assert agent._tasks_failed == 0
    # Backoff sleep was called with 5s (5 * 2^0)
    mock_sleep.assert_called_once_with(5)


@patch("app.agent.asyncio.sleep", new_callable=AsyncMock)
@patch("app.agent.asyncio.create_subprocess_exec")
async def test_retry_exhausted(mock_exec, mock_sleep, setup):
    """Task fails all retry attempts and ends as failed."""
    agent, db, config = setup
    config.max_retries = 2
    config.retry_backoff_sec = 5
    task = await db.create_task(TaskCreate(title="Always fails"))

    fail_stdout = [json.dumps({"type": "error", "error": "Persistent error"})]

    # All 3 attempts fail (1 original + 2 retries)
    mock_exec.side_effect = [
        _make_mock_process(fail_stdout, returncode=1),
        _make_mock_process(fail_stdout, returncode=1),
        _make_mock_process(fail_stdout, returncode=1),
    ]

    await agent.run_task(task.id)

    t = await db.get_task(task.id)
    assert t.status == TaskStatus.FAILED
    assert t.retry_count == 2
    assert agent._tasks_failed == 1
    # Backoff: 5s then 10s
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(5)
    mock_sleep.assert_any_call(10)


@patch("app.agent.asyncio.sleep", new_callable=AsyncMock)
@patch("app.agent.asyncio.create_subprocess_exec")
async def test_retry_disabled(mock_exec, mock_sleep, setup):
    """With max_retries=0, tasks fail immediately without retry."""
    agent, db, config = setup
    config.max_retries = 0
    task = await db.create_task(TaskCreate(title="No retry"))

    fail_stdout = [json.dumps({"type": "error", "error": "Error"})]
    mock_exec.return_value = _make_mock_process(fail_stdout, returncode=1)

    await agent.run_task(task.id)

    t = await db.get_task(task.id)
    assert t.status == TaskStatus.FAILED
    assert t.retry_count == 0
    assert agent._tasks_failed == 1
    mock_sleep.assert_not_called()


@patch("app.agent.asyncio.sleep", new_callable=AsyncMock)
@patch("app.agent.asyncio.create_subprocess_exec")
async def test_retry_logs_recorded(mock_exec, mock_sleep, setup):
    """Retry events are logged."""
    agent, db, config = setup
    config.max_retries = 1
    config.retry_backoff_sec = 3
    task = await db.create_task(TaskCreate(title="Log retry"))

    fail_stdout = [json.dumps({"type": "error", "error": "Err"})]
    success_stdout = [json.dumps({"type": "result", "result": "Ok"})]
    mock_exec.side_effect = [
        _make_mock_process(fail_stdout, returncode=1),
        _make_mock_process(success_stdout, returncode=0),
    ]

    await agent.run_task(task.id)

    logs = agent.get_logs()
    retry_logs = [l for l in logs if "retrying" in l.message.lower()]
    assert len(retry_logs) == 1
    assert "1/1" in retry_logs[0].message
    assert "3s" in retry_logs[0].message


@patch("app.agent.asyncio.create_subprocess_exec")
async def test_stream_json_parsing(mock_exec, setup):
    agent, db, _ = setup
    task = await db.create_task(TaskCreate(title="Parse test"))

    stdout = [
        json.dumps({"type": "system", "subtype": "init", "model": "claude-opus-4-6"}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Let me check"}]}}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "id": "x"}]}}),
        "not-json-line",
        json.dumps({"type": "result", "result": "All done", "total_cost_usd": 0.03}),
    ]
    mock_exec.return_value = _make_mock_process(stdout, returncode=0)

    await agent.run_task(task.id)

    logs = agent.get_logs()
    levels = [l.level for l in logs]
    assert LogLevel.CLAUDE in levels
    assert LogLevel.TOOL in levels
    assert LogLevel.RESULT in levels
