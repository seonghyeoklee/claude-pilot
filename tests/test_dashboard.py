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


def test_kanban_board(html):
    assert 'id="kanbanBoard"' in html
    assert "kanban" in html
    assert "Backlog" in html
    assert "In Progress" in html
    assert "Review" in html
    assert "Done" in html


def test_add_form(html):
    assert 'id="addForm"' in html
    assert 'id="addTitle"' in html
    assert 'id="addDesc"' in html
    assert 'id="addPriority"' in html


def test_slide_panel_structure(html):
    assert 'id="slidePanel"' in html
    assert 'id="slideOverlay"' in html
    assert "slide-panel" in html
    assert 'id="spLeft"' in html
    assert 'id="spLogArea"' in html


def test_slide_panel_two_column(html):
    assert "sp-left" in html
    assert "sp-right" in html
    assert "sp-content" in html


def test_slide_panel_close(html):
    assert "closePanel()" in html
    assert "Escape" in html


def test_task_log_in_panel(html):
    assert "Execution Log" in html
    assert 'id="spLogArea"' in html
    assert 'id="spLogCount"' in html
    assert "appendTaskLog" in html
    assert "renderTaskLog" in html
    assert "taskLogs" in html


def test_approval_in_slide(html):
    assert "approveTask()" in html
    assert "rejectTask()" in html
    assert "Approval Gate" in html
    assert "feedbackInput" in html


def test_sse_connection(html):
    assert "EventSource" in html
    assert "/api/agent/logs" in html
    assert "ensureSSE()" in html


def test_api_polling(html):
    assert "/api/agent/status" in html
    assert "/api/tasks" in html


def test_stats_display(html):
    assert 'id="statDone"' in html
    assert 'id="statFailed"' in html


def test_toast(html):
    assert 'id="toast"' in html
    assert "showToast" in html


def test_task_elapsed_time(html):
    assert "getElapsed" in html


def test_auto_open_approval(html):
    assert "waiting_approval" in html
    assert "openPanel" in html


def test_status_badges(html):
    assert "status-badge" in html
    assert "status-pending" in html
    assert "status-done" in html


def test_panel_width(html):
    assert "width: 700px" in html


# ── Label Tests ──


def test_label_badge_css(html):
    assert "label-badge" in html
    assert "label-filter-chip" in html


def test_label_input_in_form(html):
    assert 'id="addLabels"' in html
    assert "Labels" in html


def test_label_filter_bar(html):
    assert 'id="labelFilterBar"' in html
    assert "renderLabelFilter" in html
    assert "toggleLabelFilter" in html


def test_label_badges_in_card(html):
    assert "labelBadges" in html
    assert "k-card-labels" in html


def test_label_in_slide_panel(html):
    assert "t.labels" in html


# ── Search Tests ──


def test_search_input(html):
    assert 'id="searchInput"' in html
    assert "onSearchInput()" in html


def test_search_debounce(html):
    assert "searchTimer" in html
    assert "setTimeout" in html
    assert "300" in html


def test_search_query_param(html):
    assert "baseParams.set('q', searchQuery)" in html


# ── Retry Tests ──


def test_retry_function(html):
    assert "retryTask" in html
    assert "/retry" in html


def test_delete_confirm(html):
    assert "confirm(" in html


def test_log_expand_button(html):
    assert 'id="spLogExpandBtn"' in html
    assert "toggleLogExpand" in html
    assert "log-expanded" in html


def test_log_history_load(html):
    assert "/logs" in html
    assert "api/tasks/" in html


# ── Status Filter Tab Tests ──


def test_status_filter_bar(html):
    assert 'id="statusFilterBar"' in html
    assert "status-filter-bar" in html


def test_status_tab_css(html):
    assert ".status-tab" in html
    assert ".tab-count" in html


def test_status_tabs_defined(html):
    assert "STATUS_TABS" in html
    assert "renderStatusTabs" in html
    assert "setStatusFilter" in html


def test_status_filter_options(html):
    assert "'all'" in html
    assert "'pending'" in html
    assert "'in_progress'" in html
    assert "'done'" in html
    assert "'failed'" in html


def test_status_filter_localstorage(html):
    assert "localStorage.getItem('statusFilter')" in html
    assert "localStorage.setItem('statusFilter'" in html


def test_status_filter_api_call(html):
    assert "params.set('status', activeStatusFilter)" in html


# ── Markdown Rendering Tests ──


def test_render_markdown_function_exists(html):
    assert "function renderMarkdown(text)" in html


def test_render_markdown_heading(html):
    """renderMarkdown handles # headings"""
    assert "<h' + level + '>'" in html or "h' + level + '>'" in html


def test_render_markdown_bold(html):
    """renderMarkdown converts **bold** to <strong>"""
    assert "<strong>$1</strong>" in html


def test_render_markdown_italic(html):
    """renderMarkdown converts *italic* to <em>"""
    assert "<em>$1</em>" in html


def test_render_markdown_inline_code(html):
    """renderMarkdown converts `code` to <code>"""
    assert "h.replace(/`([^`]+?)`/g" in html


def test_render_markdown_code_fence(html):
    """renderMarkdown converts ```code blocks```"""
    assert "<pre><code>" in html


def test_render_markdown_list(html):
    """renderMarkdown converts - items to <li>"""
    assert "<li>$1</li>" in html
    assert "<ul>" in html


def test_render_markdown_link(html):
    """renderMarkdown converts [text](url) to <a>"""
    assert 'target="_blank"' in html
    assert "noopener" in html


def test_render_markdown_xss_prevention(html):
    """HTML is escaped before markdown conversion"""
    assert "esc(text)" in html


def test_render_markdown_used_in_description(html):
    """Description uses renderMarkdown instead of esc"""
    assert "renderMarkdown(t.description)" in html


def test_markdown_css_inline_code(html):
    """CSS for inline code styling"""
    assert ".sp-desc code" in html
    assert "rgba(255,255,255,0.08)" in html


def test_markdown_css_code_block(html):
    """CSS for code block styling"""
    assert ".sp-desc pre code" in html
    assert "rgba(255,255,255,0.05)" in html


# ── Time Ago Tests ──


def test_time_ago_function_exists(html):
    assert "function timeAgo(isoString)" in html


def test_time_ago_just_now(html):
    """timeAgo returns 'just now' for < 30s"""
    assert "'just now'" in html


def test_time_ago_minutes(html):
    """timeAgo returns 'm ago' format"""
    assert "m ago" in html


def test_time_ago_hours(html):
    """timeAgo returns 'h ago' format"""
    assert "h ago" in html


def test_time_ago_yesterday(html):
    """timeAgo returns 'yesterday'"""
    assert "'yesterday'" in html


def test_time_ago_date_format(html):
    """timeAgo returns month abbreviation for > 7 days"""
    assert "['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']" in html


def test_time_ago_auto_refresh(html):
    """30-second interval refreshes relative times"""
    assert "setInterval(refreshTimeAgo, 30000)" in html
    assert "function refreshTimeAgo()" in html


def test_time_ago_data_attribute(html):
    """Cards use data-time attribute for refresh"""
    assert 'data-time="' in html


def test_time_ago_tooltip(html):
    """Hover shows absolute time via title attribute"""
    assert "fmtAbsolute" in html
    assert "title=" in html


def test_time_relative_css(html):
    """CSS class for relative time elements"""
    assert "time-relative" in html
