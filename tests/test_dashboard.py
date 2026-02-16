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
    assert 'id="toastContainer"' in html
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
    assert "labelPills" in html
    assert "label-badge" in html


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


# ── Card 3-Tier Structure Tests ──


def test_card_3tier_title(html):
    """Tier 1: title with 14px, font-weight 500, line-clamp 2"""
    assert "k-card-title" in html
    assert "font-size: 14px" in html
    assert "-webkit-line-clamp: 2" in html


def test_card_3tier_tier2(html):
    """Tier 2: #ID + label pills"""
    assert "k-card-tier2" in html
    assert "k-card-id" in html


def test_card_3tier_tier3(html):
    """Tier 3: priority dot + time + actions"""
    assert "k-card-tier3" in html
    assert "priority-dot" in html


def test_card_status_border(html):
    """Card left border colored by status"""
    assert "card-pending" in html
    assert "card-in_progress" in html
    assert "card-waiting_approval" in html
    assert "card-done" in html
    assert "card-failed" in html


def test_card_priority_dot_css(html):
    """Priority dot: 4px circle with color per priority"""
    assert "priority-dot-0" in html
    assert "priority-dot-1" in html
    assert "priority-dot-2" in html
    assert "priority-dot-3" in html
    assert "width: 4px" in html
    assert "height: 4px" in html


def test_card_renders_status_class(html):
    """renderCard adds card-${status} class"""
    assert "card-${t.status}" in html or "card-' + t.status" in html or 'card-${t.status}' in html


# ── Toast System Tests ──


def test_toast_container(html):
    """Toast container element exists"""
    assert "toast-container" in html
    assert 'id="toastContainer"' in html


def test_toast_types_css(html):
    """Toast types: success (green), error (red), info (blue)"""
    assert "toast-success" in html
    assert "toast-error" in html
    assert "toast-info" in html
    assert "#22c55e" in html  # success green
    assert "#ef4444" in html  # error red
    assert "#3b82f6" in html  # info blue


def test_toast_animation_classes(html):
    """Toast CSS classes: .toast, .toast-visible, .toast-exit"""
    assert ".toast-visible" in html
    assert ".toast-exit" in html


def test_toast_slide_in(html):
    """Toast slide-in animation: translateX + 200ms ease-out"""
    assert "translateX" in html
    assert "200ms" in html
    assert "ease-out" in html


def test_toast_max_stack(html):
    """Toast max 3 stacked"""
    assert "children.length > 3" in html


def test_toast_auto_dismiss(html):
    """Toast auto-dismiss: 4s default, 8s for error"""
    assert "4000" in html
    assert "8000" in html


def test_toast_show_type_param(html):
    """showToast accepts message and type parameter"""
    assert "function showToast(msg, type)" in html


def test_toast_on_task_create(html):
    """Toast shown on task creation"""
    assert "Task created" in html


def test_toast_on_task_delete(html):
    """Toast shown on task deletion"""
    assert "Task deleted" in html


def test_toast_on_agent_start(html):
    """Toast shown on agent start"""
    assert "Agent started" in html


def test_toast_on_approve_reject(html):
    """Toast shown on approve and reject"""
    assert "Task approved" in html
    assert "Task rejected" in html


# ── Command Palette (Cmd+K) Tests ──


def test_cmd_palette_overlay(html):
    """Command palette overlay element exists"""
    assert 'id="cmdPaletteOverlay"' in html
    assert "cmd-palette-overlay" in html


def test_cmd_palette_input(html):
    """Command palette has search input with placeholder"""
    assert 'id="cmdPaletteInput"' in html
    assert 'Search tasks, actions...' in html


def test_cmd_palette_results(html):
    """Command palette has results container"""
    assert 'id="cmdPaletteResults"' in html
    assert "cmd-palette-results" in html


def test_cmd_palette_open_close(html):
    """openCmdPalette and closeCmdPalette functions exist"""
    assert "function openCmdPalette()" in html
    assert "function closeCmdPalette()" in html


def test_cmd_palette_render_results(html):
    """renderCmdResults function for fuzzy matching"""
    assert "function renderCmdResults(query)" in html
    assert "toLowerCase" in html


def test_cmd_palette_task_group(html):
    """Palette shows TASKS group from allTasksUnfiltered"""
    assert "cmd-palette-group-title" in html
    assert "Tasks" in html


def test_cmd_palette_actions_group(html):
    """Palette shows ACTIONS group with predefined actions"""
    assert "CMD_ACTIONS" in html
    assert "Start Agent" in html
    assert "Stop Agent" in html
    assert "Add Task" in html


def test_cmd_palette_filter_actions(html):
    """Palette includes status filter actions"""
    assert "Filter: All" in html
    assert "Filter: Pending" in html
    assert "Filter: Done" in html
    assert "Filter: Failed" in html


def test_cmd_palette_arrow_keys(html):
    """Arrow keys navigate palette items"""
    assert "ArrowDown" in html
    assert "ArrowUp" in html


def test_cmd_palette_enter_select(html):
    """Enter selects active palette item"""
    assert "cmdSelect" in html
    assert "function cmdSelect(idx)" in html


def test_cmd_palette_escape_close(html):
    """Escape closes palette"""
    assert "closeCmdPalette()" in html


def test_cmd_palette_background_click(html):
    """Clicking overlay background closes palette"""
    assert "e.target === e.currentTarget" in html


def test_cmd_palette_css(html):
    """Command palette CSS: max-width 560px, z-index 2000"""
    assert "max-width: 560px" in html
    assert "z-index: 2000" in html


def test_cmd_palette_item_hover(html):
    """Palette items have hover/active states"""
    assert "cmd-palette-item" in html
    assert "cmdHover" in html
    assert "updateCmdActive" in html


def test_cmd_palette_empty_state(html):
    """Palette shows empty message when no results"""
    assert "cmd-palette-empty" in html
    assert "No results for" in html


# ── Help Overlay (?) Tests ──


def test_help_overlay(html):
    """Help overlay element exists"""
    assert 'id="helpOverlay"' in html
    assert "help-overlay" in html


def test_help_dialog_content(html):
    """Help dialog shows keyboard shortcuts"""
    assert "Keyboard Shortcuts" in html
    assert "help-dialog" in html


def test_help_shortcut_list(html):
    """Help lists all keyboard shortcuts"""
    assert "Command palette" in html
    assert "Navigate cards down" in html
    assert "Navigate cards up" in html
    assert "Open selected card" in html
    assert "Close panel / modal" in html
    assert "Focus search" in html
    assert "Approve task" in html
    assert "Reject task" in html


def test_help_key_badges(html):
    """Help shows key badges with help-key class"""
    assert "help-key" in html
    assert "help-row" in html


def test_help_open_close(html):
    """openHelp and closeHelp functions exist"""
    assert "function openHelp()" in html
    assert "function closeHelp()" in html


# ── Keyboard Navigation Tests ──


def test_keyboard_cmd_k(html):
    """Cmd+K / Ctrl+K opens command palette"""
    assert "e.metaKey || e.ctrlKey" in html
    assert "openCmdPalette()" in html


def test_keyboard_j_k_navigation(html):
    """J/K keys navigate cards"""
    assert "kbFocusIdx" in html
    assert "function setKbFocus(idx)" in html
    assert "kb-focus" in html


def test_keyboard_focus_ring_css(html):
    """Focus ring: 2px accent color box-shadow"""
    assert ".k-card.kb-focus" in html
    assert "0 0 0 2px #3b82f6" in html


def test_keyboard_enter_opens_card(html):
    """Enter key opens selected card detail"""
    assert "kbFocusIdx >= 0" in html
    assert "cards[kbFocusIdx]" in html


def test_keyboard_slash_focuses_search(html):
    """/ key focuses search input"""
    assert "key === '/'" in html
    assert "searchInput" in html


def test_keyboard_a_approve(html):
    """A key triggers approve on waiting_approval"""
    assert "key === 'a'" in html
    assert "approvalPanel" in html


def test_keyboard_r_reject(html):
    """R key triggers reject on waiting_approval"""
    assert "key === 'r'" in html
    assert "approvalPanel" in html


def test_keyboard_input_disabled(html):
    """Shortcuts disabled when input/textarea focused"""
    assert "function isInputFocused()" in html
    assert "isContentEditable" in html


def test_keyboard_question_help(html):
    """? key toggles help overlay"""
    assert "key === '?'" in html
    assert "openHelp()" in html


# ── Drag and Drop Tests ──


def test_drag_handle_element(html):
    """Drag handle with 6-dot grip exists in card"""
    assert "drag-handle" in html
    assert "drag-handle-dot" in html
    assert "drag-handle-dot-row" in html


def test_drag_handle_css(html):
    """Drag handle CSS: cursor grab, opacity transition"""
    assert "cursor: grab" in html
    assert ".drag-handle" in html


def test_drag_handle_draggable(html):
    """Drag handle has draggable=true attribute"""
    assert 'draggable="true"' in html


def test_drag_start_function(html):
    """onDragStart sets dragTaskId and adds dragging class"""
    assert "function onDragStart(e, taskId)" in html
    assert "dragTaskId" in html
    assert "dragging" in html


def test_drag_over_function(html):
    """onDragOver prevents default and adds drag-over class"""
    assert "function onDragOver(e)" in html
    assert "drag-over" in html


def test_drag_leave_function(html):
    """onDragLeave removes drag-over class"""
    assert "function onDragLeave(e)" in html


def test_drag_drop_function(html):
    """onDrop calls PATCH API and updates status"""
    assert "function onDrop(e)" in html
    assert "PATCH" in html
    assert "newStatus" in html


def test_drag_optimistic_update(html):
    """Drop performs optimistic UI update before API call"""
    assert "task.status = newStatus" in html
    assert "renderKanban(allTasks)" in html


def test_drag_revert_on_failure(html):
    """Drop reverts to old status on API failure"""
    assert "task.status = oldStatus" in html
    assert "Failed to move task" in html


def test_drag_insert_line(html):
    """Insertion line shown at drop position"""
    assert "drag-insert-line" in html
    assert "removeDragInsertLines" in html


def test_drag_column_data_status(html):
    """Kanban columns have data-status attribute for drop target"""
    assert 'data-status="' in html


def test_drag_card_data_task_id(html):
    """Cards have data-task-id attribute"""
    assert 'data-task-id="' in html


def test_drag_card_content_wrapper(html):
    """Card content wrapped in k-card-content div"""
    assert "k-card-content" in html


def test_drag_over_column_css(html):
    """Drag-over column: dashed border highlight"""
    assert ".kanban-col.drag-over" in html
    assert "dashed" in html


def test_drag_dragend_cleanup(html):
    """dragend event cleans up all drag state"""
    assert "dragend" in html


# ── Slide Panel Animation Tests ──


def test_panel_slide_animation(html):
    """Panel uses 200ms cubic-bezier(0.32,0.72,0,1) transition"""
    assert "200ms cubic-bezier(0.32,0.72,0,1)" in html


def test_panel_overlay_opacity(html):
    """Overlay uses rgba(0,0,0,0.3) background"""
    assert "rgba(0,0,0,0.3)" in html


def test_panel_sticky_header(html):
    """Panel header is sticky"""
    assert "position: sticky" in html
    assert "top: 0" in html


def test_panel_sticky_footer(html):
    """Panel has sticky footer action bar"""
    assert "sp-footer" in html
    assert 'id="spFooter"' in html
    assert "bottom: 0" in html


def test_panel_footer_actions(html):
    """Footer renders action buttons"""
    assert "footer.innerHTML" in html
    assert "footer.style.display" in html


# ── Collapsible Section Tests ──


def test_collapsible_section_function(html):
    """toggleSection function exists"""
    assert "function toggleSection(sectionKey)" in html


def test_collapsible_section_localstorage(html):
    """Collapsed state persisted to localStorage"""
    assert "sp-sections" in html
    assert "localStorage" in html
    assert "sectionCollapseState" in html


def test_collapsible_section_chevron(html):
    """Chevron icon rotates on collapse"""
    assert "sp-section-chevron" in html
    assert "rotate(-90deg)" in html


def test_collapsible_section_html_builder(html):
    """sectionHtml helper generates collapsible sections"""
    assert "function sectionHtml(key, title, content)" in html


def test_collapsible_description_section(html):
    """Description section uses collapsible sectionHtml"""
    assert "sectionHtml('description'" in html


def test_collapsible_details_section(html):
    """Details section uses collapsible sectionHtml"""
    assert "sectionHtml('details'" in html
