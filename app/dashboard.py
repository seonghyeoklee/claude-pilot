"""대시보드 HTML 빌더"""

from __future__ import annotations

from app.report_theme import wrap_html

_EXTRA_CSS = """
/* Layout */
.top-bar {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 24px; background: #1a1d27; border-radius: 12px; margin-bottom: 20px;
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

/* Main Grid */
.main-grid {
    display: grid; grid-template-columns: 380px 1fr; gap: 20px; min-height: calc(100vh - 200px);
}
@media (max-width: 900px) { .main-grid { grid-template-columns: 1fr; } }

/* Backlog Panel */
.backlog { background: #1a1d27; border-radius: 12px; padding: 20px; overflow-y: auto; max-height: calc(100vh - 180px); }
.backlog h2 { font-size: 16px; color: #fff; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
.task-item {
    display: flex; align-items: center; gap: 8px; padding: 10px 12px;
    background: #252830; border-radius: 8px; margin-bottom: 6px; cursor: pointer;
    transition: background 0.15s;
}
.task-item:hover { background: #2d3040; }
.task-item.selected { background: #2d3040; border-left: 3px solid #3b82f6; }
.task-id { color: #666; font-size: 12px; min-width: 28px; }
.task-title { flex: 1; font-size: 13px; color: #e0e0e0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.task-status { font-size: 14px; min-width: 22px; text-align: center; }
.task-meta { font-size: 10px; color: #555; white-space: nowrap; }
.task-actions { display: flex; gap: 4px; }

.priority-badge { font-size: 10px; padding: 1px 6px; border-radius: 3px; font-weight: 700; }
.priority-0 { background: #374151; color: #9ca3af; }
.priority-1 { background: rgba(59,130,246,0.15); color: #60a5fa; }
.priority-2 { background: rgba(245,158,11,0.15); color: #fbbf24; }
.priority-3 { background: rgba(239,68,68,0.15); color: #f87171; }

/* Add task form */
.add-form { display: none; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.add-form.visible { display: flex; }
.add-form input, .add-form textarea {
    background: #252830; border: 1px solid #374151; border-radius: 8px; padding: 8px 12px;
    color: #e0e0e0; font-size: 13px; font-family: inherit;
}
.add-form input::placeholder, .add-form textarea::placeholder { color: #555; }
.add-form input:focus, .add-form textarea:focus { outline: none; border-color: #3b82f6; }
.add-form textarea { resize: vertical; min-height: 60px; }
.add-form .form-row { display: flex; gap: 8px; }

/* Right Panel */
.right-panel { display: flex; flex-direction: column; gap: 16px; }

/* Log Panel */
.log-panel { background: #1a1d27; border-radius: 12px; padding: 20px; flex: 1; display: flex; flex-direction: column; }
.log-panel h2 { font-size: 16px; color: #fff; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
.log-area {
    flex: 1; background: #0d0f14; border-radius: 8px; padding: 12px;
    font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px; line-height: 1.6;
    overflow-y: auto; max-height: 600px; min-height: 350px;
}
.log-line { margin-bottom: 2px; word-break: break-all; }
.log-time { color: #555; }
.log-SYS { color: #60a5fa; }
.log-CLAUDE { color: #a78bfa; }
.log-TOOL { color: #fbbf24; }
.log-RESULT { color: #22c55e; }
.log-ERROR { color: #ef4444; }
.log-empty { color: #555; font-style: italic; padding: 20px; text-align: center; }

/* Approval Panel */
.approval-panel {
    background: #1a1d27; border-radius: 12px; padding: 20px;
    border: 2px solid transparent; transition: border-color 0.3s;
}
.approval-panel.active { border-color: #f59e0b; }
.approval-panel h2 { font-size: 16px; color: #fff; margin-bottom: 12px; }
.approval-info { color: #aaa; font-size: 13px; margin-bottom: 12px; }
.approval-actions { display: flex; gap: 12px; align-items: center; }
.feedback-input { flex: 1; background: #252830; border: 1px solid #374151; border-radius: 8px; padding: 8px 12px; color: #e0e0e0; font-size: 13px; }
.feedback-input:focus { outline: none; border-color: #f59e0b; }

/* Detail Panel */
.detail-panel { background: #1a1d27; border-radius: 12px; padding: 20px; display: none; }
.detail-panel.visible { display: block; }
.detail-panel h2 { font-size: 16px; color: #fff; margin-bottom: 12px; }
.detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 16px; }
.detail-card { background: #252830; border-radius: 8px; padding: 10px 14px; }
.detail-card .label { font-size: 11px; color: #666; margin-bottom: 4px; }
.detail-card .value { font-size: 14px; font-weight: 600; color: #e0e0e0; }
.detail-output {
    background: #0d0f14; border-radius: 8px; padding: 12px;
    font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px; line-height: 1.5;
    max-height: 300px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; color: #aaa;
}

/* Stats bar */
.stats-bar { display: flex; gap: 12px; }
.stat-chip { background: #252830; border-radius: 8px; padding: 6px 14px; font-size: 12px; }
.stat-chip span { font-weight: 700; }

/* Toast */
.toast {
    position: fixed; bottom: 24px; right: 24px; background: #1a1d27; border: 1px solid #374151;
    border-radius: 10px; padding: 12px 20px; font-size: 13px; color: #e0e0e0;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4); opacity: 0; transition: opacity 0.3s;
    z-index: 1000; pointer-events: none;
}
.toast.show { opacity: 1; }
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
            <button class="btn btn-green" id="btnStart" onclick="agentStart()">Start</button>
            <button class="btn btn-red" id="btnStop" onclick="agentStop()" disabled>Stop</button>
        </div>
    </div>

    <div class="main-grid">
        <div class="backlog">
            <h2>
                Backlog
                <button class="btn btn-blue btn-sm" onclick="toggleAddForm()">+ Add</button>
            </h2>
            <div class="add-form" id="addForm">
                <input id="addTitle" placeholder="Task title..." onkeydown="if(event.key==='Enter')addTask()">
                <textarea id="addDesc" placeholder="Description (optional)..." rows="2"></textarea>
                <div class="form-row">
                    <select id="addPriority" style="background:#252830;border:1px solid #374151;border-radius:8px;padding:6px 10px;color:#e0e0e0;font-size:12px;">
                        <option value="0">Low</option>
                        <option value="1" selected>Medium</option>
                        <option value="2">High</option>
                        <option value="3">Urgent</option>
                    </select>
                    <button class="btn btn-blue btn-sm" onclick="addTask()">Add Task</button>
                </div>
            </div>
            <div id="taskList"></div>
        </div>

        <div class="right-panel">
            <div class="detail-panel" id="detailPanel">
                <h2 id="detailTitle">Task Detail</h2>
                <div class="detail-grid" id="detailGrid"></div>
                <div class="detail-output" id="detailOutput"></div>
            </div>

            <div class="log-panel">
                <h2>
                    Agent Log
                    <button class="btn btn-gray btn-sm" onclick="clearLog()">Clear</button>
                </h2>
                <div class="log-area" id="logArea">
                    <div class="log-empty">Logs will appear here when the agent runs.</div>
                </div>
            </div>

            <div class="approval-panel" id="approvalPanel">
                <h2>Approval Gate</h2>
                <div class="approval-info" id="approvalInfo">No task awaiting approval.</div>
                <div class="approval-actions" id="approvalActions" style="display:none;">
                    <button class="btn btn-green" onclick="approveTask()">Approve</button>
                    <input class="feedback-input" id="feedbackInput" placeholder="Rejection feedback (optional)...">
                    <button class="btn btn-red" onclick="rejectTask()">Reject</button>
                </div>
            </div>
        </div>
    </div>
</div>
<div class="toast" id="toast"></div>
"""

_JS = r"""
const STATUS_ICONS = {pending:'○', in_progress:'▶', waiting_approval:'⏳', done:'✅', failed:'❌'};
const STATUS_LABELS = {pending:'Pending', in_progress:'Running', waiting_approval:'Awaiting', done:'Done', failed:'Failed'};
const PRIORITY_LABELS = {0:'Low',1:'Med',2:'High',3:'Urgent'};
let eventSource = null;
let selectedTaskId = null;
let prevState = null;
let logHasContent = false;

// ── Tasks ──

async function loadTasks() {
    try {
        const res = await fetch('/api/tasks');
        const tasks = await res.json();
        const el = document.getElementById('taskList');
        el.innerHTML = tasks.map(t => {
            const elapsed = getElapsed(t);
            const sel = t.id === selectedTaskId ? ' selected' : '';
            return `
            <div class="task-item${sel}" data-id="${t.id}" onclick="selectTask(${t.id})">
                <span class="task-id">#${t.id}</span>
                <span class="priority-badge priority-${t.priority}">${PRIORITY_LABELS[t.priority]}</span>
                <span class="task-title" title="${esc(t.title)}">${esc(t.title)}</span>
                ${elapsed ? `<span class="task-meta">${elapsed}</span>` : ''}
                <span class="task-status" title="${STATUS_LABELS[t.status]||t.status}">${STATUS_ICONS[t.status]||'?'}</span>
                <div class="task-actions" onclick="event.stopPropagation()">
                    ${t.status==='pending'?`<button class="btn btn-blue btn-sm" onclick="runTask(${t.id})" title="Run now">▶</button>`:''}
                    ${['pending','failed'].includes(t.status)?`<button class="btn btn-gray btn-sm" onclick="deleteTask(${t.id})" title="Delete">×</button>`:''}
                </div>
            </div>`;
        }).join('');
        // refresh detail if open
        if(selectedTaskId) {
            const t = tasks.find(x => x.id === selectedTaskId);
            if(t) showDetail(t);
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
    await fetch('/api/tasks', {method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({title, description:desc, priority:pri})});
    document.getElementById('addTitle').value = '';
    document.getElementById('addDesc').value = '';
    loadTasks();
}

async function deleteTask(id) {
    await fetch(`/api/tasks/${id}`, {method:'DELETE'});
    if(selectedTaskId === id) { selectedTaskId = null; document.getElementById('detailPanel').classList.remove('visible'); }
    loadTasks();
}

async function runTask(id) {
    await fetch(`/api/tasks/${id}/run`, {method:'POST'});
    ensureSSE();
    loadTasks();
}

async function selectTask(id) {
    selectedTaskId = id;
    const res = await fetch('/api/tasks');
    const tasks = await res.json();
    const t = tasks.find(x => x.id === id);
    if(t) showDetail(t);
    loadTasks();  // highlight
}

function showDetail(t) {
    const panel = document.getElementById('detailPanel');
    panel.classList.add('visible');
    document.getElementById('detailTitle').textContent = `#${t.id} ${t.title}`;

    const cards = [];
    cards.push(cardHtml('Status', STATUS_LABELS[t.status] || t.status));
    cards.push(cardHtml('Priority', PRIORITY_LABELS[t.priority]));
    if(t.started_at) cards.push(cardHtml('Started', fmtTime(t.started_at)));
    if(t.completed_at) cards.push(cardHtml('Completed', fmtTime(t.completed_at)));
    const elapsed = getElapsed(t);
    if(elapsed) cards.push(cardHtml('Duration', elapsed));
    if(t.exit_code !== null) cards.push(cardHtml('Exit Code', t.exit_code));
    if(t.cost_usd) cards.push(cardHtml('Cost', `$${t.cost_usd.toFixed(4)}`));
    if(t.rejection_feedback) cards.push(cardHtml('Feedback', t.rejection_feedback));
    document.getElementById('detailGrid').innerHTML = cards.join('');

    const out = document.getElementById('detailOutput');
    if(t.output) { out.textContent = t.output; out.style.display = 'block'; }
    else if(t.error) { out.textContent = t.error; out.style.display = 'block'; out.style.color = '#ef4444'; }
    else if(t.description) { out.textContent = t.description; out.style.display = 'block'; out.style.color = '#888'; }
    else { out.style.display = 'none'; }
}

function cardHtml(label, value) {
    return `<div class="detail-card"><div class="label">${label}</div><div class="value">${esc(String(value))}</div></div>`;
}

function fmtTime(iso) {
    if(!iso) return '';
    const d = new Date(iso);
    return d.toLocaleTimeString('ko-KR', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
}

// ── Agent ──

async function agentStart() {
    await fetch('/api/agent/start', {method:'POST'});
    ensureSSE();
}

async function agentStop() {
    await fetch('/api/agent/stop', {method:'POST'});
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

        // Auto-connect SSE when agent is active
        if(s.state !== 'stopped' && !eventSource) ensureSSE();

        // Approval panel
        const panel = document.getElementById('approvalPanel');
        const info = document.getElementById('approvalInfo');
        const actions = document.getElementById('approvalActions');
        if(s.state === 'waiting_approval') {
            panel.classList.add('active');
            info.textContent = `Task #${s.current_task_id}: ${s.current_task_title || ''}`;
            actions.style.display = 'flex';
        } else {
            panel.classList.remove('active');
            if(s.state === 'running' && s.current_task_id) {
                info.textContent = `Running: #${s.current_task_id} ${s.current_task_title||''}`;
            } else if(s.state === 'idle' && s.loop_running) {
                info.textContent = 'Agent idle — waiting for next task.';
            } else {
                info.textContent = 'No task awaiting approval.';
            }
            actions.style.display = 'none';
        }

        // Toast on state change
        if(prevState && prevState !== s.state) {
            if(s.state === 'idle' && prevState === 'running') showToast('Task completed');
            if(s.state === 'waiting_approval') showToast('Awaiting approval — check the approval panel');
            if(s.state === 'stopped' && prevState !== 'stopped') showToast('Agent stopped');
        }
        prevState = s.state;

        loadTasks();
    } catch(e) { console.error('pollStatus', e); }
}

async function approveTask() {
    await fetch('/api/agent/approve', {method:'POST'});
}

async function rejectTask() {
    const fb = document.getElementById('feedbackInput').value.trim();
    await fetch('/api/agent/reject', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({feedback:fb})});
    document.getElementById('feedbackInput').value = '';
}

// ── SSE Logs ──

function ensureSSE() {
    if(eventSource) return;
    eventSource = new EventSource('/api/agent/logs');
    const logArea = document.getElementById('logArea');

    eventSource.onmessage = (e) => {
        try {
            const log = JSON.parse(e.data);
            if(!logHasContent) { logArea.innerHTML = ''; logHasContent = true; }
            const ts = log.timestamp ? log.timestamp.substring(11,19) : '';
            const line = document.createElement('div');
            line.className = 'log-line';
            const taskTag = log.task_id ? `<span style="color:#555">#${log.task_id}</span> ` : '';
            line.innerHTML = `<span class="log-time">${ts}</span> ${taskTag}<span class="log-${log.level}">[${log.level}]</span> ${esc(log.message)}`;
            logArea.appendChild(line);
            // cap at 500 lines
            while(logArea.children.length > 500) logArea.removeChild(logArea.firstChild);
            logArea.scrollTop = logArea.scrollHeight;
        } catch(err) {}
    };
    eventSource.onerror = () => {
        eventSource.close();
        eventSource = null;
        // reconnect after 3s
        setTimeout(() => { if(prevState && prevState !== 'stopped') ensureSSE(); }, 3000);
    };
}

function clearLog() {
    const logArea = document.getElementById('logArea');
    logArea.innerHTML = '<div class="log-empty">Logs cleared.</div>';
    logHasContent = false;
}

function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

function esc(s) { const d=document.createElement('div'); d.textContent=s||''; return d.innerHTML; }

// ── Init ──
loadTasks();
pollStatus();
setInterval(pollStatus, 3000);
// Always connect SSE on load to catch existing logs
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
