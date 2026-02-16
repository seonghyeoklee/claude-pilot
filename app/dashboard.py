"""대시보드 HTML 빌더 — 칸반 보드 + 와이드 슬라이드 패널"""

from __future__ import annotations

from app.report_theme import wrap_html

_EXTRA_CSS = """
/* Layout */
.top-bar {
    display: flex; justify-content: space-between; align-items: center;
    padding: 14px 24px; background: #1a1d27; border-radius: 12px; margin-bottom: 16px;
}
.top-bar h1 { font-size: 22px; color: #fff; }
.status-dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-left: 8px; }
.status-dot.stopped { background: #666; }
.status-dot.idle { background: #22c55e; }
.status-dot.running { background: #3b82f6; animation: pulse 1.5s infinite; }
.status-dot.waiting_approval { background: #f59e0b; animation: pulse 1s infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

.btn { border: none; border-radius: 8px; padding: 8px 18px; font-size: 13px; font-weight: 600; cursor: pointer; transition: 0.2s; }
.btn-green { background: #22c55e; color: #fff; }
.btn-green:hover { background: #16a34a; }
.btn-red { background: #ef4444; color: #fff; }
.btn-red:hover { background: #dc2626; }
.btn-blue { background: #3b82f6; color: #fff; }
.btn-blue:hover { background: #2563eb; }
.btn-gray { background: #374151; color: #e0e0e0; }
.btn-gray:hover { background: #4b5563; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-sm { padding: 4px 10px; font-size: 11px; }

.stats-bar { display: flex; gap: 10px; }
.stat-chip { background: #252830; border-radius: 8px; padding: 6px 14px; font-size: 12px; }
.stat-chip span { font-weight: 700; }

/* ── Kanban Board ── */
.kanban {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
    margin-bottom: 16px; min-height: 280px;
}
@media (max-width: 1100px) { .kanban { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .kanban { grid-template-columns: 1fr; } }

.kanban-col {
    background: #13151c; border-radius: 12px; padding: 14px; display: flex; flex-direction: column;
    min-height: 180px; max-height: calc(100vh - 340px); overflow-y: auto;
}
.kanban-col.col-pending { border-top: 3px solid #3b82f6; }
.kanban-col.col-in_progress { border-top: 3px solid #a78bfa; }
.kanban-col.col-waiting_approval { border-top: 3px solid #f59e0b; }
.kanban-col.col-done { border-top: 3px solid #22c55e; }
.kanban-col.col-failed { border-top: 3px solid #ef4444; }

.col-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #252830;
}
.col-title { font-size: 13px; font-weight: 700; color: #aaa; text-transform: uppercase; letter-spacing: 0.5px; }
.col-count {
    font-size: 11px; font-weight: 700; background: #252830; color: #888;
    padding: 2px 8px; border-radius: 10px; min-width: 20px; text-align: center;
}
.col-empty { color: #333; font-size: 12px; text-align: center; padding: 24px 0; font-style: italic; }

/* Kanban Card — 3-tier design */
.k-card {
    background: #1a1d27; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px;
    cursor: pointer; transition: background 0.15s, box-shadow 0.15s;
    border: 1px solid transparent; border-left: 3px solid #374151;
}
.k-card:hover { background: #22252f; }
.k-card.selected { border-color: #3b82f6; border-left-color: #3b82f6; box-shadow: 0 0 0 1px #3b82f6; }
.k-card.card-pending { border-left-color: #6b7280; }
.k-card.card-in_progress { border-left-color: #3b82f6; }
.k-card.card-waiting_approval { border-left-color: #f59e0b; }
.k-card.card-done { border-left-color: #22c55e; }
.k-card.card-failed { border-left-color: #ef4444; }

/* Tier 1: Title */
.k-card-title {
    font-size: 14px; font-weight: 500; color: #e5e7eb; line-height: 1.4;
    word-break: break-word; display: -webkit-box; -webkit-line-clamp: 2;
    -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 6px;
}

/* Tier 2: ID + label pills */
.k-card-tier2 { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 6px; }
.k-card-id { color: #9ca3af; font-size: 11px; }

/* Tier 3: priority dot + relative time + actions */
.k-card-tier3 { display: flex; justify-content: space-between; align-items: center; }
.k-card-tier3-left { display: flex; align-items: center; gap: 6px; }
.priority-dot { width: 4px; height: 4px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.priority-dot-0 { background: #6b7280; }
.priority-dot-1 { background: #3b82f6; }
.priority-dot-2 { background: #f59e0b; }
.priority-dot-3 { background: #ef4444; }
.k-card-meta { font-size: 11px; color: #6b7280; }
.k-card-actions { display: flex; gap: 4px; }

/* Priority badge (kept for slide panel) */
.priority-badge { font-size: 10px; padding: 1px 6px; border-radius: 3px; font-weight: 700; }
.priority-0 { background: #374151; color: #9ca3af; }
.priority-1 { background: rgba(59,130,246,0.15); color: #60a5fa; }
.priority-2 { background: rgba(245,158,11,0.15); color: #fbbf24; }
.priority-3 { background: rgba(239,68,68,0.15); color: #f87171; }

.label-badge {
    display: inline-block; font-size: 10px; padding: 1px 7px; border-radius: 3px;
    font-weight: 600; background: rgba(139,92,246,0.15); color: #a78bfa; margin-right: 3px; margin-top: 3px;
}
.label-filter-bar {
    display: flex; align-items: center; gap: 6px; margin-bottom: 12px; flex-wrap: wrap;
}
.label-filter-chip {
    font-size: 11px; padding: 3px 10px; border-radius: 6px; cursor: pointer;
    background: #252830; color: #888; border: 1px solid #374151; transition: 0.15s;
}
.label-filter-chip:hover { border-color: #a78bfa; color: #a78bfa; }
.label-filter-chip.active { background: rgba(139,92,246,0.15); color: #a78bfa; border-color: #a78bfa; }

/* Status filter tabs */
.status-filter-bar {
    display: flex; align-items: center; gap: 6px; margin-bottom: 12px;
}
.status-tab {
    font-size: 12px; padding: 6px 14px; border-radius: 8px; cursor: pointer;
    background: #1a1d27; color: #888; border: 1px solid transparent; transition: 0.15s;
    display: flex; align-items: center; gap: 6px; font-weight: 600;
}
.status-tab:hover { background: #22252f; color: #ccc; }
.status-tab.active { background: #252830; color: #e0e0e0; border-color: #3b82f6; }
.status-tab .tab-count {
    font-size: 10px; font-weight: 700; background: #374151; color: #888;
    padding: 1px 7px; border-radius: 10px; min-width: 18px; text-align: center;
}
.status-tab.active .tab-count { background: rgba(59,130,246,0.2); color: #60a5fa; }

/* Search bar */
.search-bar {
    display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
}
.search-bar input {
    background: #252830; border: 1px solid #374151; border-radius: 8px; padding: 8px 14px;
    color: #e0e0e0; font-size: 13px; font-family: inherit; width: 300px;
}
.search-bar input::placeholder { color: #555; }
.search-bar input:focus { outline: none; border-color: #3b82f6; }

/* Add task form */
.add-form { display: none; gap: 8px; margin-bottom: 12px; padding: 14px; background: #1a1d27; border-radius: 10px; }
.add-form.visible { display: flex; flex-wrap: wrap; }
.add-form input, .add-form textarea {
    background: #252830; border: 1px solid #374151; border-radius: 8px; padding: 8px 12px;
    color: #e0e0e0; font-size: 13px; font-family: inherit;
}
.add-form input { flex: 1; min-width: 200px; }
.add-form input::placeholder, .add-form textarea::placeholder { color: #555; }
.add-form input:focus, .add-form textarea:focus { outline: none; border-color: #3b82f6; }
.add-form textarea { resize: vertical; min-height: 50px; width: 100%; }
.add-form .form-row { display: flex; gap: 8px; width: 100%; }

/* ── Slide Panel (와이드) ── */
.slide-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 900;
    opacity: 0; pointer-events: none; transition: opacity 0.25s;
}
.slide-overlay.open { opacity: 1; pointer-events: auto; }

.slide-panel {
    position: fixed; top: 0; right: 0; width: 700px; height: 100vh; z-index: 910;
    background: #13151c; border-left: 1px solid #252830;
    transform: translateX(100%); transition: transform 0.3s cubic-bezier(0.16,1,0.3,1);
    display: flex; flex-direction: column; overflow: hidden;
}
.slide-panel.open { transform: translateX(0); }
.slide-panel.resizing { transition: none; }
@media (max-width: 900px) { .slide-panel { width: 100vw !important; } }

/* Resize handle (outer panel edge) */
.sp-resize {
    position: absolute; top: 0; left: -5px; width: 10px; height: 100%; cursor: col-resize; z-index: 920;
}
.sp-resize::after {
    content: ''; position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
    width: 4px; height: 48px; border-radius: 2px; background: #333; opacity: 0; transition: opacity 0.2s;
}
.sp-resize:hover::after, .sp-resize.active::after { opacity: 1; background: #3b82f6; }
.sp-resize::before {
    content: '\u2261'; position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
    color: #555; font-size: 16px; opacity: 0; transition: opacity 0.2s;
}
.sp-resize:hover::before, .sp-resize.active::before { opacity: 0; }

.sp-header {
    display: flex; justify-content: space-between; align-items: flex-start;
    padding: 20px 28px 16px; border-bottom: 1px solid #252830; flex-shrink: 0;
}
.sp-title-area { flex: 1; }
.sp-title-area h2 { font-size: 18px; color: #fff; margin: 0 0 6px 0; line-height: 1.4; word-break: break-word; }
.sp-title-meta { display: flex; gap: 8px; align-items: center; }
.sp-close {
    background: none; border: none; color: #666; font-size: 24px; cursor: pointer;
    padding: 0 0 0 16px; line-height: 1; transition: color 0.15s; flex-shrink: 0;
}
.sp-close:hover { color: #fff; }

.sp-body { flex: 1; overflow-y: auto; padding: 0; display: flex; flex-direction: column; }

/* Two-column layout inside panel */
.sp-content { display: flex; flex: 1; min-height: 0; }
.sp-left { flex: 1; padding: 20px 28px; overflow-y: auto; min-width: 200px; }
.sp-right { width: 320px; flex-shrink: 0; display: flex; flex-direction: column; overflow: hidden; min-width: 180px; }

/* Inner column divider (resizable) */
.sp-divider {
    width: 6px; flex-shrink: 0; cursor: col-resize; background: #1e2030; position: relative;
    transition: background 0.15s;
}
.sp-divider:hover, .sp-divider.active { background: #3b82f6; }
.sp-divider::after {
    content: ''; position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
    width: 2px; height: 32px; border-radius: 1px; background: #444;
}
.sp-divider:hover::after, .sp-divider.active::after { background: #fff; }

@media (max-width: 700px) {
    .sp-content { flex-direction: column; }
    .sp-left { border-right: none; border-bottom: 1px solid #1e2030; }
    .sp-right { width: 100% !important; height: 300px; }
    .sp-divider { display: none; }
}

.sp-section { margin-bottom: 20px; }
.sp-section-title {
    font-size: 11px; font-weight: 700; color: #555; text-transform: uppercase;
    letter-spacing: 0.5px; margin-bottom: 8px;
}

.sp-meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.sp-meta-item { background: #1a1d27; border-radius: 8px; padding: 10px 12px; }
.sp-meta-item .label { font-size: 10px; color: #666; margin-bottom: 3px; }
.sp-meta-item .value { font-size: 13px; font-weight: 600; color: #e0e0e0; }

.sp-desc {
    background: #1a1d27; border-radius: 8px; padding: 14px; color: #ccc; font-size: 13px;
    line-height: 1.7; word-break: break-word;
}
.sp-desc h1, .sp-desc h2, .sp-desc h3, .sp-desc h4, .sp-desc h5, .sp-desc h6 {
    color: #e0e0e0; margin: 12px 0 6px 0; line-height: 1.4;
}
.sp-desc h1 { font-size: 20px; }
.sp-desc h2 { font-size: 17px; }
.sp-desc h3 { font-size: 15px; }
.sp-desc p { margin: 6px 0; }
.sp-desc ul { margin: 6px 0; padding-left: 20px; }
.sp-desc li { margin: 2px 0; }
.sp-desc code {
    padding: 2px 6px; background: rgba(255,255,255,0.08); border-radius: 3px;
    font-family: 'SF Mono','Fira Code',monospace; font-size: 12px;
}
.sp-desc pre { margin: 8px 0; }
.sp-desc pre code {
    display: block; padding: 10px 14px; background: rgba(255,255,255,0.05);
    border-radius: 6px; overflow-x: auto; white-space: pre; line-height: 1.5;
}
.sp-desc a { color: #3b82f6; text-decoration: none; }
.sp-desc a:hover { text-decoration: underline; }
.sp-desc strong { color: #e0e0e0; }

.time-relative { cursor: default; }

.sp-output {
    background: #0d0f14; border-radius: 8px; padding: 12px;
    font-family: 'SF Mono', 'Fira Code', monospace; font-size: 11px; line-height: 1.5;
    max-height: 250px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; color: #aaa;
}

.sp-actions { display: flex; gap: 8px; flex-wrap: wrap; }

/* Approval inside slide panel */
.sp-approval {
    background: #1a1d27; border-radius: 10px; padding: 14px;
    border: 2px solid #f59e0b;
}
.sp-approval-title { font-size: 13px; font-weight: 700; color: #f59e0b; margin-bottom: 10px; }
.sp-approval-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.sp-approval .feedback-input {
    flex: 1; min-width: 120px; background: #252830; border: 1px solid #374151; border-radius: 8px;
    padding: 8px 12px; color: #e0e0e0; font-size: 13px;
}
.sp-approval .feedback-input:focus { outline: none; border-color: #f59e0b; }

/* Task log inside slide panel (right column) */
.sp-log-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 14px 16px 10px; flex-shrink: 0; border-bottom: 1px solid #1e2030;
}
.sp-log-header h3 { font-size: 13px; font-weight: 700; color: #aaa; margin: 0; }
.sp-log-header-actions { display: flex; gap: 6px; align-items: center; }
.sp-log-expand-btn {
    background: none; border: 1px solid #374151; border-radius: 6px; color: #888;
    font-size: 14px; width: 28px; height: 28px; cursor: pointer; transition: 0.15s;
    display: flex; align-items: center; justify-content: center;
}
.sp-log-expand-btn:hover { border-color: #3b82f6; color: #3b82f6; }
.sp-log-area {
    flex: 1; background: #0d0f14; padding: 12px; overflow-y: auto;
    font-family: 'SF Mono', 'Fira Code', monospace; font-size: 11px; line-height: 1.6;
}
.sp-log-empty { color: #333; font-style: italic; text-align: center; padding: 40px 12px; font-size: 12px; }

/* Expanded log mode: hide left column, log fills entire panel */
.sp-content.log-expanded .sp-left { display: none; }
.sp-content.log-expanded .sp-divider { display: none; }
.sp-content.log-expanded .sp-right { width: 100% !important; flex: 1; }

.status-badge { display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; }
.status-pending { background: rgba(59,130,246,0.15); color: #60a5fa; }
.status-in_progress { background: rgba(167,139,250,0.15); color: #a78bfa; }
.status-waiting_approval { background: rgba(245,158,11,0.15); color: #fbbf24; }
.status-done { background: rgba(34,197,94,0.15); color: #22c55e; }
.status-failed { background: rgba(239,68,68,0.15); color: #f87171; }

/* Toast — stacking, 3-tier */
.toast-container {
    position: fixed; bottom: 24px; right: 24px; z-index: 1000;
    display: flex; flex-direction: column-reverse; gap: 8px; pointer-events: none;
}
.toast {
    background: #1a1d27; border: 1px solid #374151; border-radius: 10px;
    padding: 12px 20px; font-size: 13px; color: #e0e0e0;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4); pointer-events: auto;
    transform: translateX(120%); transition: transform 200ms ease-out, opacity 200ms ease-out;
    opacity: 0;
}
.toast-visible { transform: translateX(0); opacity: 1; }
.toast-exit { transform: translateX(120%); opacity: 0; }
.toast-success { border-left: 3px solid #22c55e; }
.toast-error { border-left: 3px solid #ef4444; }
.toast-info { border-left: 3px solid #3b82f6; }
"""

_BODY = """
<div class="container">
    <div class="top-bar">
        <div style="display:flex;align-items:center;gap:12px;">
            <h1>Claude Pilot</h1>
            <span id="statusDot" class="status-dot stopped"></span>
            <span id="statusLabel" style="color:#888;font-size:13px;">Stopped</span>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
            <div class="stats-bar">
                <div class="stat-chip">Done: <span id="statDone" class="positive">0</span></div>
                <div class="stat-chip">Failed: <span id="statFailed" class="negative">0</span></div>
            </div>
            <button class="btn btn-blue btn-sm" onclick="toggleAddForm()">+ Add</button>
            <select id="minPriority" style="background:#252830;border:1px solid #374151;border-radius:8px;padding:6px 10px;color:#e0e0e0;font-size:12px;">
                <option value="0">All</option>
                <option value="1">Medium+</option>
                <option value="2" selected>High+</option>
                <option value="3">Urgent</option>
            </select>
            <button class="btn btn-green" id="btnStart" onclick="agentStart()">Start</button>
            <button class="btn btn-red" id="btnStop" onclick="agentStop()" disabled>Stop</button>
        </div>
    </div>

    <div class="add-form" id="addForm">
        <input id="addTitle" placeholder="Task title..." onkeydown="if(event.key==='Enter')addTask()">
        <div class="form-row">
            <textarea id="addDesc" placeholder="Description (optional)..." rows="2"></textarea>
        </div>
        <div class="form-row">
            <input id="addLabels" placeholder="Labels (comma-separated)..." style="flex:1;min-width:150px;">
        </div>
        <div class="form-row">
            <select id="addPriority" style="background:#252830;border:1px solid #374151;border-radius:8px;padding:6px 10px;color:#e0e0e0;font-size:12px;">
                <option value="0">Low</option>
                <option value="1" selected>Medium</option>
                <option value="2">High</option>
                <option value="3">Urgent</option>
            </select>
            <button class="btn btn-blue btn-sm" onclick="addTask()">Add Task</button>
            <button class="btn btn-gray btn-sm" onclick="toggleAddForm()">Cancel</button>
        </div>
    </div>

    <div class="status-filter-bar" id="statusFilterBar"></div>

    <div class="search-bar">
        <input id="searchInput" placeholder="Search tasks..." oninput="onSearchInput()">
    </div>
    <div class="label-filter-bar" id="labelFilterBar"></div>
    <div class="kanban" id="kanbanBoard"></div>
</div>

<!-- Slide Panel -->
<div class="slide-overlay" id="slideOverlay" onclick="closePanel()"></div>
<div class="slide-panel" id="slidePanel">
    <div class="sp-resize" id="spResize"></div>
    <div class="sp-header">
        <div class="sp-title-area">
            <h2 id="spTitle">Task Detail</h2>
            <div class="sp-title-meta" id="spTitleMeta"></div>
        </div>
        <button class="sp-close" onclick="closePanel()">&times;</button>
    </div>
    <div class="sp-body">
        <div class="sp-content">
            <div class="sp-left" id="spLeft"></div>
            <div class="sp-divider" id="spDivider"></div>
            <div class="sp-right" id="spRight">
                <div class="sp-log-header">
                    <h3>Execution Log</h3>
                    <div class="sp-log-header-actions">
                        <span id="spLogCount" style="font-size:11px;color:#555;"></span>
                        <button class="sp-log-expand-btn" id="spLogExpandBtn" onclick="toggleLogExpand()" title="Expand log">&#x26F6;</button>
                    </div>
                </div>
                <div class="sp-log-area" id="spLogArea">
                    <div class="sp-log-empty">No logs yet for this task.</div>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="toast-container" id="toastContainer"></div>
"""

_JS = r"""
const COLUMNS = [
    {key:'pending',          title:'Backlog',      color:'#3b82f6'},
    {key:'in_progress',      title:'In Progress',  color:'#a78bfa'},
    {key:'waiting_approval', title:'Review',        color:'#f59e0b'},
    {key:'done',             title:'Done',          color:'#22c55e'},
];
const PRIORITY_LABELS = {0:'Low',1:'Med',2:'High',3:'Urgent'};
const STATUS_LABELS = {pending:'Backlog', in_progress:'In Progress', waiting_approval:'Review', done:'Done', failed:'Failed'};
let eventSource = null;
let selectedTaskId = null;
let prevState = null;
let allTasks = [];
let allTasksUnfiltered = [];
let activeLabel = null;
let searchQuery = '';
let searchTimer = null;
let activeStatusFilter = localStorage.getItem('statusFilter') || 'all';
let approvalShownFor = null;  // track which task auto-opened for approval
let _lastSlideKey = null;  // diff check to avoid unnecessary re-render
let _lastKanbanKey = null;  // diff check for kanban board

// Task-specific log storage: { taskId: [{timestamp, level, message}, ...] }
const taskLogs = {};

// ── Kanban Board ──

function renderKanban(tasks) {
    allTasks = tasks;

    // Skip re-render if data unchanged
    const kanbanKey = tasks.map(t => `${t.id}:${t.status}:${t.priority}:${t.id===selectedTaskId}`).join('|');
    if(kanbanKey === _lastKanbanKey) return;
    _lastKanbanKey = kanbanKey;

    const board = document.getElementById('kanbanBoard');

    const hasFailed = tasks.some(t => t.status === 'failed');
    const hasCancelled = tasks.some(t => t.status === 'cancelled');
    let cols = [...COLUMNS];
    if(hasFailed) cols.push({key:'failed', title:'Failed', color:'#ef4444'});
    if(hasCancelled) cols.push({key:'cancelled', title:'Cancelled', color:'#6b7280'});

    board.style.gridTemplateColumns = `repeat(${cols.length}, 1fr)`;

    board.innerHTML = cols.map(col => {
        const colTasks = tasks.filter(t => t.status === col.key);
        const cardsHtml = colTasks.length === 0
            ? `<div class="col-empty">No tasks</div>`
            : colTasks.map(t => renderCard(t)).join('');
        return `
        <div class="kanban-col col-${col.key}">
            <div class="col-header">
                <span class="col-title">${col.title}</span>
                <span class="col-count">${colTasks.length}</span>
            </div>
            ${cardsHtml}
        </div>`;
    }).join('');
}

function renderCard(t) {
    const elapsed = getElapsed(t);
    const sel = t.id === selectedTaskId ? ' selected' : '';
    const actions = [];
    if(t.status === 'pending') actions.push(`<button class="btn btn-blue btn-sm" onclick="event.stopPropagation();runTask(${t.id})" title="Run now">▶</button>`);
    if(t.status === 'failed') actions.push(`<button class="btn btn-blue btn-sm" onclick="event.stopPropagation();retryTask(${t.id})" title="Retry">↻</button>`);
    if(t.status === 'pending') actions.push(`<button class="btn btn-gray btn-sm" onclick="event.stopPropagation();cancelTask(${t.id})" title="Cancel">⊘</button>`);
    if(t.status === 'pending') actions.push(`<button class="btn btn-gray btn-sm" onclick="event.stopPropagation();deleteTask(${t.id})" title="Delete">×</button>`);
    const labelPills = (t.labels || []).map(l => `<span class="label-badge">${esc(l)}</span>`).join('');

    // Time display: elapsed for running/done, relative for others
    let timeHtml = '';
    if(elapsed) {
        timeHtml = `<span class="k-card-meta">${elapsed}</span>`;
    } else {
        const ts = t.updated_at || t.created_at;
        if(ts) timeHtml = `<span class="k-card-meta time-relative" data-time="${esc(ts)}" title="${fmtAbsolute(ts)}">${timeAgo(ts)}</span>`;
    }

    return `
    <div class="k-card card-${t.status}${sel}" onclick="selectTask(${t.id})">
        <div class="k-card-title">${esc(t.title)}</div>
        <div class="k-card-tier2">
            <span class="k-card-id">#${t.id}</span>
            ${labelPills}
        </div>
        <div class="k-card-tier3">
            <div class="k-card-tier3-left">
                <span class="priority-dot priority-dot-${t.priority}"></span>
                ${timeHtml}
            </div>
            <div class="k-card-actions">${actions.join('')}</div>
        </div>
    </div>`;
}

// ── Label Filter ──

function renderLabelFilter(tasks) {
    const allLabels = new Set();
    tasks.forEach(t => (t.labels || []).forEach(l => allLabels.add(l)));
    const bar = document.getElementById('labelFilterBar');
    if(allLabels.size === 0) { bar.innerHTML = ''; return; }
    bar.innerHTML = `<span style="font-size:11px;color:#666;">Labels:</span>` +
        [...allLabels].sort().map(l => {
            const cls = l === activeLabel ? ' active' : '';
            return `<span class="label-filter-chip${cls}" onclick="toggleLabelFilter('${esc(l)}')">${esc(l)}</span>`;
        }).join('');
}

function toggleLabelFilter(label) {
    activeLabel = activeLabel === label ? null : label;
    loadTasks();
}

// ── Status Filter Tabs ──

const STATUS_TABS = [
    {key:'all',              label:'All'},
    {key:'pending',          label:'Pending'},
    {key:'in_progress',      label:'Running'},
    {key:'done',             label:'Done'},
    {key:'failed',           label:'Failed'},
    {key:'cancelled',        label:'Cancelled'},
];

function renderStatusTabs(tasks) {
    const bar = document.getElementById('statusFilterBar');
    const counts = {};
    tasks.forEach(t => { counts[t.status] = (counts[t.status] || 0) + 1; });
    bar.innerHTML = STATUS_TABS.map(tab => {
        const cnt = tab.key === 'all' ? tasks.length : (counts[tab.key] || 0);
        const cls = activeStatusFilter === tab.key ? ' active' : '';
        return `<div class="status-tab${cls}" onclick="setStatusFilter('${tab.key}')">
            ${tab.label}<span class="tab-count">${cnt}</span>
        </div>`;
    }).join('');
}

function setStatusFilter(key) {
    activeStatusFilter = key;
    localStorage.setItem('statusFilter', key);
    loadTasks();
}

// ── Search ──

function onSearchInput() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
        searchQuery = document.getElementById('searchInput').value.trim();
        loadTasks();
    }, 300);
}

// ── Tasks ──

async function loadTasks() {
    try {
        // Fetch all tasks (for tab counts, without status filter)
        const baseParams = new URLSearchParams();
        if(activeLabel) baseParams.set('label', activeLabel);
        if(searchQuery) baseParams.set('q', searchQuery);
        const baseQs = baseParams.toString();
        const baseUrl = baseQs ? `/api/tasks?${baseQs}` : '/api/tasks';
        const baseRes = await fetch(baseUrl);
        allTasksUnfiltered = await baseRes.json();
        renderStatusTabs(allTasksUnfiltered);

        // If status filter active, fetch filtered subset; otherwise reuse
        let tasks;
        if(activeStatusFilter && activeStatusFilter !== 'all') {
            const params = new URLSearchParams(baseParams);
            params.set('status', activeStatusFilter);
            const res = await fetch(`/api/tasks?${params}`);
            tasks = await res.json();
        } else {
            tasks = allTasksUnfiltered;
        }
        renderLabelFilter(tasks);
        renderKanban(tasks);
        // Only re-render slide panel if task data actually changed
        if(selectedTaskId) {
            const t = tasks.find(x => x.id === selectedTaskId);
            if(t) {
                const key = JSON.stringify({s:t.status, p:t.priority, o:t.output?.length, e:t.error, pr:t.pr_url, b:t.branch_name});
                if(key !== _lastSlideKey) {
                    _lastSlideKey = key;
                    renderSlideLeft(t);
                }
            }
        }
    } catch(e) { console.error('loadTasks', e); }
}

function getElapsed(t) {
    if(t.status === 'in_progress' && t.started_at) {
        const sec = Math.floor((Date.now() - new Date(t.started_at).getTime()) / 1000);
        return sec < 60 ? `${sec}s` : `${Math.floor(sec/60)}m${sec%60}s`;
    }
    if((t.status === 'done' || t.status === 'failed') && t.started_at && t.completed_at) {
        const sec = Math.floor((new Date(t.completed_at) - new Date(t.started_at)) / 1000);
        return sec < 60 ? `${sec}s` : `${Math.floor(sec/60)}m${sec%60}s`;
    }
    return '';
}

function toggleAddForm() {
    const f = document.getElementById('addForm');
    f.classList.toggle('visible');
    if(f.classList.contains('visible')) document.getElementById('addTitle').focus();
}

async function addTask() {
    const title = document.getElementById('addTitle').value.trim();
    if(!title) return;
    const desc = document.getElementById('addDesc').value.trim();
    const pri = parseInt(document.getElementById('addPriority').value);
    const labelsRaw = document.getElementById('addLabels').value.trim();
    const labels = labelsRaw ? labelsRaw.split(',').map(s => s.trim()).filter(Boolean) : [];
    await fetch('/api/tasks', {method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({title, description:desc, priority:pri, labels})});
    document.getElementById('addTitle').value = '';
    document.getElementById('addDesc').value = '';
    document.getElementById('addLabels').value = '';
    document.getElementById('addForm').classList.remove('visible');
    showToast('Task created', 'success');
    loadTasks();
}

async function deleteTask(id) {
    if(!confirm('Delete this task?')) return;
    await fetch(`/api/tasks/${id}`, {method:'DELETE'});
    if(selectedTaskId === id) closePanel();
    showToast('Task deleted', 'info');
    loadTasks();
}

async function retryTask(id) {
    await fetch(`/api/tasks/${id}/retry`, {method:'POST'});
    showToast('Task moved to Backlog', 'info');
    loadTasks();
}

async function cancelTask(id) {
    await fetch(`/api/tasks/${id}`, {method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({status:'cancelled'})});
    showToast('Task cancelled', 'info');
    loadTasks();
}

async function reopenTask(id) {
    await fetch(`/api/tasks/${id}`, {method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({status:'pending'})});
    showToast('Task reopened', 'info');
    loadTasks();
}

async function runTask(id) {
    await fetch(`/api/tasks/${id}/run`, {method:'POST'});
    showToast('Task started', 'info');
    ensureSSE();
    loadTasks();
}

// ── Slide Panel ──

function selectTask(id) {
    selectedTaskId = id;
    const t = allTasks.find(x => x.id === id);
    if(!t) return;
    openPanel(t);
    renderKanban(allTasks);
}

async function openPanel(t) {
    document.getElementById('slideOverlay').classList.add('open');
    document.getElementById('slidePanel').classList.add('open');
    document.getElementById('spTitle').textContent = `#${t.id}  ${t.title}`;

    // Reset expand state
    document.querySelector('.sp-content').classList.remove('log-expanded');
    document.getElementById('spLogExpandBtn').innerHTML = '&#x26F6;';

    // Title meta: status + priority badges
    const meta = document.getElementById('spTitleMeta');
    meta.innerHTML = `<span class="status-badge status-${t.status}">${STATUS_LABELS[t.status]||t.status}</span>
        <span class="priority-badge priority-${t.priority}">${PRIORITY_LABELS[t.priority]}</span>`;
    const elapsed = getElapsed(t);
    if(elapsed) meta.innerHTML += `<span style="font-size:11px;color:#666">${elapsed}</span>`;

    renderSlideLeft(t);

    // Load persisted logs from DB if not already in memory
    if(!taskLogs[t.id] || taskLogs[t.id].length === 0) {
        try {
            const res = await fetch(`/api/tasks/${t.id}/logs`);
            const logs = await res.json();
            if(logs.length > 0) taskLogs[t.id] = logs;
        } catch(e) {}
    }
    renderTaskLog(t.id);
}

function closePanel() {
    document.getElementById('slideOverlay').classList.remove('open');
    document.getElementById('slidePanel').classList.remove('open');
    selectedTaskId = null;
    _lastSlideKey = null;
    renderKanban(allTasks);
}

function toggleLogExpand() {
    const content = document.querySelector('.sp-content');
    const btn = document.getElementById('spLogExpandBtn');
    content.classList.toggle('log-expanded');
    btn.innerHTML = content.classList.contains('log-expanded') ? '&#x2716;' : '&#x26F6;';
}

function renderSlideLeft(t) {
    const left = document.getElementById('spLeft');
    let html = '';

    // ── Description / Goal ──
    if(t.description) {
        html += `<div class="sp-section">
            <div class="sp-section-title">Description</div>
            <div class="sp-desc">${renderMarkdown(t.description)}</div>
        </div>`;
    }

    // ── Labels ──
    if(t.labels && t.labels.length > 0) {
        html += `<div class="sp-section">
            <div class="sp-section-title">Labels</div>
            <div>${t.labels.map(l => `<span class="label-badge">${esc(l)}</span>`).join(' ')}</div>
        </div>`;
    }

    // ── Meta grid ──
    html += `<div class="sp-section">
        <div class="sp-section-title">Details</div>
        <div class="sp-meta-grid">`;
    if(t.started_at)
        html += `<div class="sp-meta-item"><div class="label">Started</div><div class="value">${fmtTime(t.started_at)}</div></div>`;
    if(t.completed_at)
        html += `<div class="sp-meta-item"><div class="label">Completed</div><div class="value">${fmtTime(t.completed_at)}</div></div>`;
    if(t.exit_code !== null && t.exit_code !== undefined)
        html += `<div class="sp-meta-item"><div class="label">Exit Code</div><div class="value">${t.exit_code}</div></div>`;
    if(t.cost_usd)
        html += `<div class="sp-meta-item"><div class="label">Cost</div><div class="value">$${t.cost_usd.toFixed(4)}</div></div>`;
    if(t.branch_name)
        html += `<div class="sp-meta-item"><div class="label">Branch</div><div class="value" style="font-size:11px;font-family:monospace">${esc(t.branch_name)}</div></div>`;
    if(t.pr_url)
        html += `<div class="sp-meta-item"><div class="label">PR</div><div class="value"><a href="${esc(t.pr_url)}" target="_blank" style="color:#3b82f6;text-decoration:none;font-size:11px">#${esc(t.pr_url.split('/').pop())} ${esc(t.title)}</a></div></div>`;
    if(t.rejection_feedback)
        html += `<div class="sp-meta-item" style="grid-column:1/-1"><div class="label">Rejection Feedback</div><div class="value" style="color:#f87171">${esc(t.rejection_feedback)}</div></div>`;
    html += `</div></div>`;

    // ── Approval Gate ──
    if(t.status === 'waiting_approval') {
        html += `<div class="sp-section">
            <div class="sp-approval" id="approvalPanel">
                <div class="sp-approval-title">Approval Gate</div>
                <div class="sp-approval-actions">
                    <button class="btn btn-green" onclick="approveTask()">Approve</button>
                    <input class="feedback-input" id="feedbackInput" placeholder="Rejection feedback...">
                    <button class="btn btn-red" onclick="rejectTask()">Reject</button>
                </div>
            </div>
        </div>`;
    }

    // ── Output / Error ──
    if(t.output) {
        html += `<div class="sp-section">
            <div class="sp-section-title">Output</div>
            <div class="sp-output">${esc(t.output)}</div>
        </div>`;
    } else if(t.error) {
        html += `<div class="sp-section">
            <div class="sp-section-title">Error</div>
            <div class="sp-output" style="color:#ef4444">${esc(t.error)}</div>
        </div>`;
    }

    // ── Actions ──
    const actions = [];
    if(t.status === 'pending')
        actions.push(`<button class="btn btn-blue" onclick="runTask(${t.id})">Run Now</button>`);
    if(t.status === 'failed')
        actions.push(`<button class="btn btn-blue" onclick="retryTask(${t.id})">Retry</button>`);
    if(t.status === 'done')
        actions.push(`<button class="btn btn-gray" onclick="retryTask(${t.id})">Re-run</button>`);
    if(t.status === 'cancelled')
        actions.push(`<button class="btn btn-blue" onclick="reopenTask(${t.id})">Reopen</button>`);
    if(['pending'].includes(t.status))
        actions.push(`<button class="btn btn-gray" onclick="cancelTask(${t.id})">Cancel</button>`);
    if(['pending','failed','cancelled'].includes(t.status))
        actions.push(`<button class="btn btn-gray" onclick="deleteTask(${t.id})">Delete</button>`);
    if(actions.length) {
        html += `<div class="sp-section">
            <div class="sp-section-title">Actions</div>
            <div class="sp-actions">${actions.join('')}</div>
        </div>`;
    }

    left.innerHTML = html;
}

// ── Task-specific Log ──

function isLogNearBottom(area) {
    return area.scrollHeight - area.scrollTop - area.clientHeight < 80;
}

function renderTaskLog(taskId) {
    const area = document.getElementById('spLogArea');
    const counter = document.getElementById('spLogCount');
    const logs = taskLogs[taskId] || [];
    counter.textContent = logs.length > 0 ? `${logs.length}` : '';

    if(logs.length === 0) {
        area.innerHTML = '<div class="sp-log-empty">No logs yet for this task.</div>';
        return;
    }
    const wasNearBottom = isLogNearBottom(area);
    area.innerHTML = logs.map(log => {
        const ts = log.timestamp ? fmtTime(log.timestamp) : '';
        return `<div class="log-line"><span class="log-time">${ts}</span> <span class="log-${log.level}">[${log.level}]</span> ${esc(log.message)}</div>`;
    }).join('');
    if(wasNearBottom) area.scrollTop = area.scrollHeight;
}

function appendTaskLog(taskId, log) {
    if(!taskLogs[taskId]) taskLogs[taskId] = [];
    taskLogs[taskId].push(log);
    // Keep max 500 per task
    if(taskLogs[taskId].length > 500) taskLogs[taskId].shift();

    // If this task's panel is open, append live
    if(selectedTaskId === taskId) {
        const area = document.getElementById('spLogArea');
        const counter = document.getElementById('spLogCount');
        // Clear empty placeholder
        const empty = area.querySelector('.sp-log-empty');
        if(empty) area.innerHTML = '';

        const wasNearBottom = isLogNearBottom(area);
        const ts = log.timestamp ? fmtTime(log.timestamp) : '';
        const line = document.createElement('div');
        line.className = 'log-line';
        line.innerHTML = `<span class="log-time">${ts}</span> <span class="log-${log.level}">[${log.level}]</span> ${esc(log.message)}`;
        area.appendChild(line);
        while(area.children.length > 500) area.removeChild(area.firstChild);
        if(wasNearBottom) area.scrollTop = area.scrollHeight;
        counter.textContent = `${taskLogs[taskId].length}`;
    }
}

function fmtTime(iso) {
    if(!iso) return '';
    const d = new Date(iso);
    return d.toLocaleTimeString('ko-KR', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
}

// ── Agent ──

async function agentStart() {
    const pri = parseInt(document.getElementById('minPriority').value);
    await fetch('/api/agent/start', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({min_priority:pri})});
    showToast('Agent started', 'success');
    ensureSSE();
}

async function agentStop() {
    await fetch('/api/agent/stop', {method:'POST'});
    showToast('Agent stopped', 'info');
}

async function pollStatus() {
    try {
        const res = await fetch('/api/agent/status');
        const s = await res.json();
        const dot = document.getElementById('statusDot');
        const label = document.getElementById('statusLabel');
        dot.className = 'status-dot ' + s.state;
        const stateText = s.state.replace(/_/g, ' ');
        label.textContent = stateText.charAt(0).toUpperCase() + stateText.slice(1);
        document.getElementById('statDone').textContent = s.tasks_completed;
        document.getElementById('statFailed').textContent = s.tasks_failed;
        document.getElementById('btnStart').disabled = s.loop_running;
        document.getElementById('btnStop').disabled = !s.loop_running;

        if(s.state !== 'stopped' && !eventSource) ensureSSE();

        // Auto-open approval task in slide panel (once per task)
        if(s.state === 'waiting_approval' && s.current_task_id && approvalShownFor !== s.current_task_id) {
            approvalShownFor = s.current_task_id;
            const t = allTasks.find(x => x.id === s.current_task_id);
            if(t) { selectedTaskId = s.current_task_id; openPanel(t); renderKanban(allTasks); }
        }
        if(s.state !== 'waiting_approval') approvalShownFor = null;

        if(prevState && prevState !== s.state) {
            if(s.state === 'idle' && prevState === 'running') showToast('Task completed', 'success');
            if(s.state === 'waiting_approval') showToast('Awaiting approval', 'info');
            if(s.state === 'stopped' && prevState !== 'stopped') showToast('Agent stopped', 'info');
        }
        prevState = s.state;

        loadTasks();
    } catch(e) { console.error('pollStatus', e); }
}

async function approveTask() {
    await fetch('/api/agent/approve', {method:'POST'});
    showToast('Task approved', 'success');
}

async function rejectTask() {
    const input = document.getElementById('feedbackInput');
    const fb = input ? input.value.trim() : '';
    await fetch('/api/agent/reject', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({feedback:fb})});
    if(input) input.value = '';
    showToast('Task rejected', 'error');
}

// ── SSE Logs ──

function ensureSSE() {
    if(eventSource) return;
    eventSource = new EventSource('/api/agent/logs');

    eventSource.onmessage = (e) => {
        try {
            const log = JSON.parse(e.data);
            // Store per task
            if(log.task_id) {
                appendTaskLog(log.task_id, log);
            }
        } catch(err) {}
    };
    eventSource.onerror = () => {
        eventSource.close();
        eventSource = null;
        setTimeout(() => { if(prevState && prevState !== 'stopped') ensureSSE(); }, 3000);
    };
}

function showToast(msg, type) {
    type = type || 'info';
    const container = document.getElementById('toastContainer');
    const el = document.createElement('div');
    el.className = 'toast toast-' + type;
    el.textContent = msg;
    container.appendChild(el);
    // Enforce max 3 toasts
    while(container.children.length > 3) {
        container.removeChild(container.firstChild);
    }
    // Trigger slide-in
    requestAnimationFrame(() => { el.classList.add('toast-visible'); });
    const delay = type === 'error' ? 8000 : 4000;
    setTimeout(() => {
        el.classList.remove('toast-visible');
        el.classList.add('toast-exit');
        setTimeout(() => { if(el.parentNode) el.parentNode.removeChild(el); }, 200);
    }, delay);
}

function esc(s) { const d=document.createElement('div'); d.textContent=s||''; return d.innerHTML; }

function renderMarkdown(text) {
    if(!text) return '';
    // Escape HTML first (XSS prevention)
    let h = esc(text);
    // Code fence blocks (```...```)
    h = h.replace(/```(\w*)\n?([\s\S]*?)```/g, function(_, lang, code) {
        return '<pre><code>' + code.replace(/\n$/, '') + '</code></pre>';
    });
    // Headings (# ~ ######)
    h = h.replace(/^(#{1,6})\s+(.+)$/gm, function(_, hashes, content) {
        const level = hashes.length;
        return '<h' + level + '>' + content + '</h' + level + '>';
    });
    // Bold **text**
    h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic *text*
    h = h.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Inline code `text`
    h = h.replace(/`([^`]+?)`/g, '<code>$1</code>');
    // Links [text](url)
    h = h.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    // Unordered list items (- item)
    h = h.replace(/^- (.+)$/gm, '<li>$1</li>');
    h = h.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');
    // Wrap remaining plain lines in <p> (skip tags)
    h = h.split('\n').map(function(line) {
        const trimmed = line.trim();
        if(!trimmed) return '';
        if(/^<(h[1-6]|ul|li|pre|p)/.test(trimmed)) return line;
        return '<p>' + line + '</p>';
    }).join('\n');
    return h;
}

function timeAgo(isoString) {
    if(!isoString) return '';
    const now = Date.now();
    const then = new Date(isoString).getTime();
    const diffSec = Math.floor((now - then) / 1000);
    if(diffSec < 30) return 'just now';
    if(diffSec < 3600) return Math.floor(diffSec / 60) + 'm ago';
    if(diffSec < 86400) return Math.floor(diffSec / 3600) + 'h ago';
    if(diffSec < 172800) return 'yesterday';
    if(diffSec < 604800) return Math.floor(diffSec / 86400) + 'd ago';
    const d = new Date(isoString);
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return months[d.getMonth()] + ' ' + d.getDate();
}

function fmtAbsolute(isoString) {
    if(!isoString) return '';
    return new Date(isoString).toLocaleString('ko-KR', {year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'});
}

function refreshTimeAgo() {
    document.querySelectorAll('[data-time]').forEach(function(el) {
        el.textContent = timeAgo(el.getAttribute('data-time'));
    });
}

// Keyboard: Escape closes panel
document.addEventListener('keydown', (e) => { if(e.key === 'Escape') closePanel(); });

// ── Panel Resize (outer width) ──
(function() {
    const panel = document.getElementById('slidePanel');
    const handle = document.getElementById('spResize');
    const MIN_W = 400, MAX_W = Math.max(window.innerWidth - 100, 500);
    let startX = 0, startW = 0, dragging = false;

    const saved = localStorage.getItem('sp-width');
    if(saved) panel.style.width = saved + 'px';

    handle.addEventListener('mousedown', (e) => {
        e.preventDefault();
        dragging = true;
        startX = e.clientX;
        startW = panel.offsetWidth;
        panel.classList.add('resizing');
        handle.classList.add('active');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', (e) => {
        if(!dragging) return;
        const diff = startX - e.clientX;
        const newW = Math.min(MAX_W, Math.max(MIN_W, startW + diff));
        panel.style.width = newW + 'px';
    });

    document.addEventListener('mouseup', () => {
        if(!dragging) return;
        dragging = false;
        panel.classList.remove('resizing');
        handle.classList.remove('active');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        localStorage.setItem('sp-width', panel.offsetWidth);
    });
})();

// ── Inner Divider Resize (left/right columns) ──
(function() {
    const divider = document.getElementById('spDivider');
    const right = document.getElementById('spRight');
    const MIN_R = 180, MAX_R = 600;
    let startX = 0, startRW = 0, dragging = false;

    const saved = localStorage.getItem('sp-right-w');
    if(saved) right.style.width = saved + 'px';

    divider.addEventListener('mousedown', (e) => {
        e.preventDefault();
        dragging = true;
        startX = e.clientX;
        startRW = right.offsetWidth;
        divider.classList.add('active');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', (e) => {
        if(!dragging) return;
        const diff = startX - e.clientX;
        const newW = Math.min(MAX_R, Math.max(MIN_R, startRW + diff));
        right.style.width = newW + 'px';
    });

    document.addEventListener('mouseup', () => {
        if(!dragging) return;
        dragging = false;
        divider.classList.remove('active');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        localStorage.setItem('sp-right-w', right.offsetWidth);
    });
})();

// ── Init ──
loadTasks();
pollStatus();
setInterval(pollStatus, 3000);
setInterval(refreshTimeAgo, 30000);
ensureSSE();
"""


def build_dashboard_html() -> str:
    return wrap_html(
        title="Claude Pilot",
        body=_BODY,
        extra_css=_EXTRA_CSS,
        extra_js=_JS,
        include_chartjs=False,
    )
