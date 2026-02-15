"""Dashboard HTML structure tests"""

from __future__ import annotations

import pytest

from app.dashboard import build_dashboard_html


@pytest.fixture
def html():
    return build_dashboard_html()


def test_html_valid(html):
    assert "<!DOCTYPE html>" in html
    assert "</html>" in html


def test_title(html):
    assert "<title>Claude Pilot</title>" in html


def test_dark_theme(html):
    assert "#0f1117" in html


def test_top_bar(html):
    assert "top-bar" in html
    assert "Claude Pilot" in html


def test_start_stop_buttons(html):
    assert 'id="btnStart"' in html
    assert 'id="btnStop"' in html


def test_status_dot(html):
    assert 'id="statusDot"' in html
    assert "status-dot" in html


def test_backlog_section(html):
    assert "Backlog" in html
    assert 'id="taskList"' in html


def test_add_form(html):
    assert 'id="addForm"' in html
    assert 'id="addTitle"' in html
    assert 'id="addDesc"' in html
    assert 'id="addPriority"' in html


def test_log_area(html):
    assert 'id="logArea"' in html
    assert "log-area" in html


def test_approval_panel(html):
    assert 'id="approvalPanel"' in html
    assert "Approval Gate" in html


def test_approval_actions(html):
    assert "approveTask()" in html
    assert "rejectTask()" in html


def test_feedback_input(html):
    assert 'id="feedbackInput"' in html


def test_sse_connection(html):
    assert "EventSource" in html
    assert "/api/agent/logs" in html
    assert "ensureSSE()" in html  # auto-connect on load


def test_api_polling(html):
    assert "/api/agent/status" in html
    assert "/api/tasks" in html


def test_stats_display(html):
    assert 'id="statDone"' in html
    assert 'id="statFailed"' in html


def test_detail_panel(html):
    assert 'id="detailPanel"' in html
    assert 'id="detailGrid"' in html
    assert 'id="detailOutput"' in html


def test_toast(html):
    assert 'id="toast"' in html
    assert "showToast" in html


def test_task_elapsed_time(html):
    assert "getElapsed" in html


def test_clear_log_button(html):
    assert "clearLog()" in html
