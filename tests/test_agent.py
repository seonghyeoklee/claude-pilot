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
