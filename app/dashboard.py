"""대시보드 HTML 빌더 — 칸반 보드 + 와이드 슬라이드 패널"""

from __future__ import annotations

from app.report_theme import wrap_html

_EXTRA_CSS = """
/* Override container max-width for dashboard (wider) */
.container { max-width: 100%; padding: 20px 32px; }

/* ── Custom Scrollbar (Dark Theme) ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #374151; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #4b5563; }
::-webkit-scrollbar-corner { background: transparent; }
/* Firefox */
* { scrollbar-width: thin; scrollbar-color: #374151 transparent; }
/* Kanban column scrollbar — slightly thinner */
.kanban-col::-webkit-scrollbar { width: 4px; }
.kanban-col::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); }
.kanban-col::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
/* Log area scrollbar */
.sp-log-area::-webkit-scrollbar { width: 5px; }
.sp-log-area::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); }
.sp-log-area::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.25); }
/* Command palette scrollbar */
.cmd-palette-results::-webkit-scrollbar { width: 4px; }
.cmd-palette-results::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); }

/* Layout */
.top-bar {
    display: flex; justify-content: space-between; align-items: center;
    padding: 14px 24px; background: var(--bg-card); border-radius: 12px; margin-bottom: 16px;
    border: 1px solid var(--border);
}
.top-bar h1 { font-size: 22px; color: #fff; }
.status-dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-left: 8px; }
.status-dot.stopped { background: #666; }
.status-dot.idle { background: #22c55e; }
.status-dot.running { background: var(--accent); animation: pulse-dot 1.5s infinite; }
.status-dot.waiting_approval { background: #f59e0b; animation: pulse-dot 1s infinite; }
@keyframes pulse-dot { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

/* ── Agent Running: Header effects ── */
.top-bar { position: relative; overflow: hidden; transition: border-color 0.3s; }
.top-bar.agent-running { border-color: rgba(88,166,255,0.25); }
.top-bar.agent-running::after {
    content: ''; position: absolute; bottom: 0; left: 0; width: 100%; height: 2px;
    background: linear-gradient(90deg, transparent 0%, var(--accent) 30%, #a78bfa 50%, var(--accent) 70%, transparent 100%);
    background-size: 200% 100%;
    animation: header-stripe 2s linear infinite;
}
@keyframes header-stripe {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
.working-text {
    font-size: 12px; color: var(--text-tertiary); max-width: 400px; overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap; transition: opacity 0.3s;
}
.working-text .working-task { color: var(--accent); font-weight: 600; }
.working-dots::after {
    content: ''; display: inline-block; width: 16px; text-align: left;
    animation: typing-dots 1.4s steps(4, end) infinite;
}
@keyframes typing-dots {
    0% { content: ''; }
    25% { content: '.'; }
    50% { content: '..'; }
    75% { content: '...'; }
}

/* ── In-Progress Card: Breathing Glow + LIVE ── */
.k-card.card-in_progress {
    border-left-color: #3b82f6;
    animation: card-breathe 2.5s ease-in-out infinite;
}
@keyframes card-breathe {
    0%, 100% { box-shadow: 0 0 0 0 rgba(59,130,246,0); border-left-color: #3b82f6; }
    50% { box-shadow: -2px 0 16px 2px rgba(59,130,246,0.15), 0 0 8px 0 rgba(59,130,246,0.08); border-left-color: #60a5fa; }
}
.live-badge {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 9px; font-weight: 800; color: #ef4444; letter-spacing: 0.8px; text-transform: uppercase;
    background: rgba(239,68,68,0.1); padding: 1px 6px; border-radius: 3px;
}
.live-dot {
    width: 5px; height: 5px; border-radius: 50%; background: #ef4444;
    animation: live-blink 1.2s ease-in-out infinite;
}
@keyframes live-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.2; }
}

.btn { border: none; border-radius: 8px; padding: 8px 18px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.2s, opacity 0.2s; }
.btn-green { background: #22c55e; color: #fff; }
.btn-green:hover { background: #16a34a; }
.btn-red { background: #ef4444; color: #fff; }
.btn-red:hover { background: #dc2626; }
.btn-blue { background: var(--accent); color: #fff; }
.btn-blue:hover { background: #4090e0; }
.btn-gray { background: #374151; color: var(--text-primary); }
.btn-gray:hover { background: #4b5563; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-sm { padding: 4px 10px; font-size: 11px; }

.stats-bar { display: flex; gap: 10px; }
.stat-chip { background: var(--bg-panel); border-radius: 8px; padding: 6px 14px; font-size: 12px; border: 1px solid var(--border); }
.stat-chip span { font-weight: 700; }

/* ── Skeleton Loading ── */
@keyframes shimmer {
    0% { background-position: -400px 0; }
    100% { background-position: 400px 0; }
}
.skeleton {
    background: linear-gradient(90deg, var(--bg-card) 25%, #252830 50%, var(--bg-card) 75%);
    background-size: 800px 100%;
    animation: shimmer 1.5s infinite linear;
    border-radius: 6px;
}
.skeleton-card {
    background: var(--bg-card); border-radius: 8px; padding: 12px; margin-bottom: 8px;
    border: 1px solid var(--border);
}
.skeleton-title { height: 14px; width: 75%; margin-bottom: 10px; }
.skeleton-label { height: 10px; width: 40%; margin-bottom: 8px; }
.skeleton-meta { height: 10px; width: 55%; }

/* ── Micro-Animations ── */
@keyframes card-enter {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes state-pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.02); }
    100% { transform: scale(1); }
}
@keyframes log-line-enter {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
}

.k-card { animation: card-enter 200ms ease-out both; }
.k-card.state-changed { animation: state-pulse 300ms ease-out; }
.log-line { animation: log-line-enter 150ms ease-out; }

/* Filter tab underline slide */
.status-tab {
    position: relative;
}
.status-tab::after {
    content: ''; position: absolute; bottom: -1px; left: 50%; width: 0;
    height: 2px; background: var(--accent); transition: width 0.2s ease, left 0.2s ease;
}
.status-tab.active::after { width: 80%; left: 10%; }

/* prefers-reduced-motion */
@media (prefers-reduced-motion: reduce) {
    .skeleton { animation: none; }
    .k-card { animation: none; }
    .k-card.state-changed { animation: none; }
    .log-line { animation: none; }
    .status-tab::after { transition: none; }
    .toast { transition: none; }
    .slide-panel { transition: none; }
    .slide-overlay { transition: none; }
    .cmd-palette { transition: none; }
    .cmd-palette-overlay { transition: none; }
    .status-dot.running, .status-dot.waiting_approval { animation: none; }
    .top-bar.agent-running::after { animation: none; }
    .k-card.card-in_progress { animation: none; }
    .live-dot { animation: none; }
    .working-dots::after { animation: none; content: '...'; }
}

/* ── Kanban Board ── */
.kanban {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
    margin-bottom: 16px; min-height: 280px;
}
@media (max-width: 1100px) { .kanban { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .kanban { grid-template-columns: 1fr; } }

.kanban-col {
    background: var(--bg-card); border-radius: 12px; padding: 14px; display: flex; flex-direction: column;
    min-height: 200px; max-height: calc(100vh - 260px); overflow-y: auto;
    border: 1px solid var(--border);
}
.kanban-col.col-pending { border-top: 3px solid #3b82f6; }
.kanban-col.col-in_progress { border-top: 3px solid #a78bfa; }
.kanban-col.col-waiting_approval { border-top: 3px solid #f59e0b; }
.kanban-col.col-done { border-top: 3px solid #22c55e; }
.kanban-col.col-failed { border-top: 3px solid #ef4444; }

.col-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid var(--border);
}
.col-title { font-size: 13px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
.col-count {
    font-size: 11px; font-weight: 700; background: var(--bg-panel); color: var(--text-tertiary);
    padding: 2px 8px; border-radius: 10px; min-width: 20px; text-align: center;
}
.col-empty { color: var(--text-tertiary); font-size: 12px; text-align: center; padding: 24px 0; font-style: italic; }

/* Kanban Card — 3-tier design */
.k-card {
    background: var(--bg-panel); border-radius: 8px; padding: 10px 12px; margin-bottom: 8px;
    cursor: pointer; transition: background 0.15s, box-shadow 0.15s, opacity 0.15s, transform 0.15s;
    border: 1px solid var(--border); border-left: 3px solid #374151;
    display: flex; align-items: flex-start; gap: 8px;
}
.k-card:hover { background: var(--hover-overlay); }
.k-card.dragging { opacity: 0.5; transform: scale(0.98); }

/* Drag handle — 6-dot grip */
.drag-handle {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 3px; cursor: grab; padding: 4px 2px; flex-shrink: 0; opacity: 0.3;
    transition: opacity 0.15s; user-select: none; -webkit-user-select: none;
}
.drag-handle:active { cursor: grabbing; }
.k-card:hover .drag-handle { opacity: 0.7; }
.drag-handle-dot-row { display: flex; gap: 3px; }
.drag-handle-dot {
    width: 4px; height: 4px; border-radius: 50%; background: #6b7280;
}

/* Drag-over column highlight */
.kanban-col.drag-over {
    border: 2px dashed var(--accent); background: rgba(88,166,255,0.05);
}
/* Drop insertion line */
.drag-insert-line {
    height: 2px; background: var(--accent); border-radius: 1px; margin: -1px 0;
    pointer-events: none; transition: opacity 0.1s;
}
.k-card.selected { border-color: var(--accent); border-left-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
.k-card.card-pending { border-left-color: #6b7280; }
.k-card.card-waiting_approval { border-left-color: #f59e0b; }
.k-card.card-done { border-left-color: #22c55e; }
.k-card.card-failed { border-left-color: #ef4444; }

/* Card content wrapper (beside drag handle) */
.k-card-content { flex: 1; min-width: 0; }

/* Tier 1: Title */
.k-card-title {
    font-size: 14px; font-weight: 500; color: var(--text-primary); line-height: 1.4;
    word-break: break-word; display: -webkit-box; -webkit-line-clamp: 2;
    -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 6px;
}

/* Tier 2: ID + label pills */
.k-card-tier2 { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 6px; }
.k-card-id { color: var(--text-secondary); font-size: 11px; }

/* Tier 3: priority dot + relative time + actions */
.k-card-tier3 { display: flex; justify-content: space-between; align-items: center; }
.k-card-tier3-left { display: flex; align-items: center; gap: 6px; }
.priority-dot { width: 4px; height: 4px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.priority-dot-0 { background: #6b7280; }
.priority-dot-1 { background: #3b82f6; }
.priority-dot-2 { background: #f59e0b; }
.priority-dot-3 { background: #ef4444; }
.k-card-meta { font-size: 11px; color: var(--text-tertiary); }
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
    background: var(--bg-panel); color: var(--text-tertiary); border: 1px solid var(--border); transition: 0.15s;
}
.label-filter-chip:hover { border-color: #a78bfa; color: #a78bfa; }
.label-filter-chip.active { background: rgba(139,92,246,0.15); color: #a78bfa; border-color: #a78bfa; }

/* Status filter tabs */
.status-filter-bar {
    display: flex; align-items: center; gap: 6px; margin-bottom: 12px;
}
.status-tab {
    font-size: 12px; padding: 6px 14px; border-radius: 8px; cursor: pointer;
    background: var(--bg-card); color: var(--text-tertiary); border: 1px solid transparent; transition: 0.15s;
    display: flex; align-items: center; gap: 6px; font-weight: 600;
}
.status-tab:hover { background: var(--hover-overlay); color: var(--text-secondary); }
.status-tab.active { background: var(--bg-panel); color: var(--text-primary); border-color: var(--accent); }
.status-tab .tab-count {
    font-size: 10px; font-weight: 700; background: #374151; color: var(--text-tertiary);
    padding: 1px 7px; border-radius: 10px; min-width: 18px; text-align: center;
}
.status-tab.active .tab-count { background: rgba(88,166,255,0.2); color: var(--accent); }

/* Search bar */
.search-bar {
    display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
}
.search-bar input {
    background: var(--bg-panel); border: 1px solid var(--border); border-radius: 8px; padding: 8px 14px;
    color: var(--text-primary); font-size: 13px; font-family: inherit; width: 300px;
}
.search-bar input::placeholder { color: var(--text-tertiary); }
.search-bar input:focus { outline: none; border-color: var(--accent); }

/* Add task form */
.add-form { display: none; gap: 8px; margin-bottom: 12px; padding: 14px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border); }
.add-form.visible { display: flex; flex-wrap: wrap; }
.add-form input, .add-form textarea {
    background: var(--bg-panel); border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px;
    color: var(--text-primary); font-size: 13px; font-family: inherit;
}
.add-form input { flex: 1; min-width: 200px; }
.add-form input::placeholder, .add-form textarea::placeholder { color: var(--text-tertiary); }
.add-form input:focus, .add-form textarea:focus { outline: none; border-color: var(--accent); }
.add-form textarea { resize: vertical; min-height: 50px; width: 100%; }
.add-form .form-row { display: flex; gap: 8px; width: 100%; }

/* ── Slide Panel (와이드) ── */
.slide-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 900;
    opacity: 0; pointer-events: none; transition: opacity 200ms cubic-bezier(0.32,0.72,0,1);
}
.slide-overlay.open { opacity: 1; pointer-events: auto; }

.slide-panel {
    position: fixed; top: 0; right: 0; width: 700px; height: 100vh; z-index: 910;
    background: var(--bg-card); border-left: 1px solid var(--border);
    transform: translateX(100%); transition: transform 200ms cubic-bezier(0.32,0.72,0,1);
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
    width: 4px; height: 48px; border-radius: 2px; background: var(--text-tertiary); opacity: 0; transition: opacity 0.2s;
}
.sp-resize:hover::after, .sp-resize.active::after { opacity: 1; background: var(--accent); }
.sp-resize::before {
    content: '\u2261'; position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
    color: var(--text-tertiary); font-size: 16px; opacity: 0; transition: opacity 0.2s;
}
.sp-resize:hover::before, .sp-resize.active::before { opacity: 0; }

.sp-header {
    display: flex; justify-content: space-between; align-items: flex-start;
    padding: 20px 28px 16px; border-bottom: 1px solid var(--border); flex-shrink: 0;
    position: sticky; top: 0; background: var(--bg-card); z-index: 5;
}

/* Sticky action bar at bottom */
.sp-footer {
    display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
    padding: 12px 28px; border-top: 1px solid var(--border); flex-shrink: 0;
    background: var(--bg-card); position: sticky; bottom: 0; z-index: 5;
}
.sp-title-area { flex: 1; }
.sp-title-area h2 { font-size: 18px; color: #fff; margin: 0 0 6px 0; line-height: 1.4; word-break: break-word; }
.sp-title-meta { display: flex; gap: 8px; align-items: center; }
.sp-close {
    background: none; border: none; color: var(--text-tertiary); font-size: 24px; cursor: pointer;
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
    width: 6px; flex-shrink: 0; cursor: col-resize; background: var(--border); position: relative;
    transition: background 0.15s;
}
.sp-divider:hover, .sp-divider.active { background: var(--accent); }
.sp-divider::after {
    content: ''; position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
    width: 2px; height: 32px; border-radius: 1px; background: #444;
}
.sp-divider:hover::after, .sp-divider.active::after { background: #fff; }

@media (max-width: 700px) {
    .sp-content { flex-direction: column; }
    .sp-left { border-right: none; border-bottom: 1px solid var(--border); }
    .sp-right { width: 100% !important; height: 300px; }
    .sp-divider { display: none; }
}

.sp-section { margin-bottom: 20px; }
.sp-section-title {
    font-size: 11px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase;
    letter-spacing: 0.5px; margin-bottom: 8px;
}

/* Collapsible section */
.sp-section-header {
    display: flex; align-items: center; gap: 6px; cursor: pointer;
    margin-bottom: 8px; user-select: none; -webkit-user-select: none;
}
.sp-section-header:hover .sp-section-title { color: var(--text-secondary); }
.sp-section-chevron {
    font-size: 10px; color: var(--text-tertiary); transition: transform 0.15s;
    display: inline-block; width: 14px; text-align: center;
}
.sp-section-header.collapsed .sp-section-chevron { transform: rotate(-90deg); }
.sp-section-body { overflow: hidden; transition: max-height 0.2s ease; }
.sp-section-body.collapsed { max-height: 0 !important; overflow: hidden; }

.sp-meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.sp-meta-item { background: var(--bg-panel); border-radius: 8px; padding: 10px 12px; border: 1px solid var(--border); }
.sp-meta-item .label { font-size: 10px; color: var(--text-tertiary); margin-bottom: 3px; }
.sp-meta-item .value { font-size: 13px; font-weight: 600; color: var(--text-primary); }

.sp-desc {
    background: var(--bg-panel); border-radius: 8px; padding: 14px; color: var(--text-secondary); font-size: 13px;
    line-height: 1.7; word-break: break-word; border: 1px solid var(--border);
}
.sp-desc h1, .sp-desc h2, .sp-desc h3, .sp-desc h4, .sp-desc h5, .sp-desc h6 {
    color: var(--text-primary); margin: 12px 0 6px 0; line-height: 1.4;
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
.sp-desc a { color: var(--accent); text-decoration: none; }
.sp-desc a:hover { text-decoration: underline; }
.sp-desc strong { color: var(--text-primary); }

.time-relative { cursor: default; }

.sp-output {
    background: var(--bg-page); border-radius: 8px; padding: 12px;
    font-family: 'SF Mono', 'Fira Code', monospace; font-size: 11px; line-height: 1.5;
    max-height: 250px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; color: var(--text-secondary);
}

.sp-actions { display: flex; gap: 8px; flex-wrap: wrap; }

/* Approval inside slide panel */
.sp-approval {
    background: var(--bg-panel); border-radius: 10px; padding: 14px;
    border: 2px solid #f59e0b;
}
.sp-approval-title { font-size: 13px; font-weight: 700; color: #f59e0b; margin-bottom: 10px; }
.sp-approval-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.sp-approval .feedback-input {
    flex: 1; min-width: 120px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
    padding: 8px 12px; color: var(--text-primary); font-size: 13px;
}
.sp-approval .feedback-input:focus { outline: none; border-color: #f59e0b; }

/* Task log inside slide panel (right column) */
.sp-log-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 14px 16px 10px; flex-shrink: 0; border-bottom: 1px solid var(--border);
}
.sp-log-header h3 { font-size: 13px; font-weight: 700; color: var(--text-secondary); margin: 0; }
.sp-log-header-actions { display: flex; gap: 6px; align-items: center; }
.sp-log-expand-btn {
    background: none; border: 1px solid var(--border); border-radius: 6px; color: var(--text-tertiary);
    font-size: 14px; width: 28px; height: 28px; cursor: pointer; transition: 0.15s;
    display: flex; align-items: center; justify-content: center;
}
.sp-log-expand-btn:hover { border-color: var(--accent); color: var(--accent); }
.sp-log-area {
    flex: 1; background: var(--bg-page); padding: 12px; overflow-y: auto;
    font-family: 'SF Mono', 'Fira Code', monospace; font-size: 11px; line-height: 1.6;
}
.sp-log-empty { color: var(--text-tertiary); font-style: italic; text-align: center; padding: 40px 12px; font-size: 12px; }

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

/* ── Command Palette (Cmd+K) ── */
.cmd-palette-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 2000;
    opacity: 0; pointer-events: none; transition: opacity 0.15s;
    display: flex; justify-content: center; padding-top: 20vh;
}
.cmd-palette-overlay.open { opacity: 1; pointer-events: auto; }

.cmd-palette {
    width: 100%; max-width: 560px; background: var(--bg-card); border: 1px solid var(--border);
    border-radius: 12px; box-shadow: 0 16px 64px rgba(0,0,0,0.5);
    display: flex; flex-direction: column; max-height: 420px;
    transform: scale(0.96); transition: transform 0.15s;
}
.cmd-palette-overlay.open .cmd-palette { transform: scale(1); }

.cmd-palette-input {
    width: 100%; background: transparent; border: none; border-bottom: 1px solid var(--border);
    padding: 16px 20px; color: var(--text-primary); font-size: 15px; font-family: inherit; outline: none;
}
.cmd-palette-input::placeholder { color: var(--text-tertiary); }

.cmd-palette-results {
    flex: 1; overflow-y: auto; padding: 8px;
}
.cmd-palette-group { padding: 4px 0; }
.cmd-palette-group-title {
    font-size: 10px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase;
    letter-spacing: 0.5px; padding: 6px 12px;
}
.cmd-palette-item {
    display: flex; align-items: center; gap: 10px; padding: 8px 12px;
    border-radius: 8px; cursor: pointer; transition: background 0.1s; color: var(--text-secondary); font-size: 13px;
}
.cmd-palette-item:hover, .cmd-palette-item.active { background: var(--bg-panel); color: #fff; }
.cmd-palette-item .cmd-icon { font-size: 14px; width: 20px; text-align: center; flex-shrink: 0; }
.cmd-palette-item .cmd-label { flex: 1; }
.cmd-palette-item .cmd-hint { font-size: 11px; color: var(--text-tertiary); }
.cmd-palette-empty { color: var(--text-tertiary); font-size: 13px; text-align: center; padding: 24px; font-style: italic; }

/* ── Help Overlay (?) ── */
.help-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 2000;
    opacity: 0; pointer-events: none; transition: opacity 0.15s;
    display: flex; justify-content: center; align-items: center;
}
.help-overlay.open { opacity: 1; pointer-events: auto; }
.help-dialog {
    background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
    padding: 24px 32px; max-width: 480px; width: 100%;
    box-shadow: 0 16px 64px rgba(0,0,0,0.5);
}
.help-dialog h2 { font-size: 16px; color: #fff; margin-bottom: 16px; }
.help-dialog .help-close {
    float: right; background: none; border: none; color: var(--text-tertiary); font-size: 20px; cursor: pointer;
}
.help-dialog .help-close:hover { color: #fff; }
.help-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 6px 0; border-bottom: 1px solid var(--border);
}
.help-row:last-child { border-bottom: none; }
.help-key {
    background: var(--bg-panel); border: 1px solid var(--border); border-radius: 4px;
    padding: 2px 8px; font-size: 12px; font-family: 'SF Mono','Fira Code',monospace;
    color: var(--text-primary); min-width: 24px; text-align: center;
}
.help-desc { font-size: 13px; color: var(--text-secondary); }

/* ── Keyboard Focus Ring ── */
.k-card.kb-focus {
    box-shadow: 0 0 0 2px var(--accent); border-color: var(--accent);
}

/* Toast — stacking, 3-tier */
.toast-container {
    position: fixed; bottom: 24px; right: 24px; z-index: 1000;
    display: flex; flex-direction: column-reverse; gap: 8px; pointer-events: none;
}
.toast {
    background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
    padding: 12px 20px; font-size: 13px; color: var(--text-primary);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4); pointer-events: auto;
    transform: translateX(120%); transition: transform 200ms ease-out, opacity 200ms ease-out;
    opacity: 0;
}
.toast-visible { transform: translateX(0); opacity: 1; }
.toast-exit { transform: translateX(120%); opacity: 0; }
.toast-success { border-left: 3px solid #22c55e; }
.toast-error { border-left: 3px solid #ef4444; }
.toast-info { border-left: 3px solid #3b82f6; }

/* ── Navigation Tabs ── */
.nav-tabs {
    display: flex; gap: 0; margin-bottom: 16px; border-bottom: 1px solid var(--border);
}
.nav-tab {
    padding: 10px 24px; font-size: 14px; font-weight: 600; cursor: pointer;
    color: var(--text-tertiary); border-bottom: 2px solid transparent; transition: 0.15s;
    background: none; border-top: none; border-left: none; border-right: none;
}
.nav-tab:hover { color: var(--text-secondary); }
.nav-tab.active { color: var(--accent); border-bottom-color: var(--accent); }

/* ── Plan Card ── */
.plan-card {
    background: var(--bg-card); border-radius: 12px; padding: 18px 22px;
    border: 1px solid var(--border); cursor: pointer; transition: background 0.15s, border-color 0.15s;
    margin-bottom: 10px;
}
.plan-card:hover { border-color: var(--accent); background: var(--hover-overlay); }
.plan-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.plan-card-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.plan-card-meta { display: flex; gap: 8px; align-items: center; font-size: 12px; color: var(--text-tertiary); }
.plan-card-targets { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.plan-card-progress { margin-top: 10px; }
.plan-card-progress-bar {
    height: 4px; background: var(--bg-panel); border-radius: 2px; overflow: hidden;
}
.plan-card-progress-fill {
    height: 100%; background: var(--accent); border-radius: 2px; transition: width 0.3s;
}

/* ── Target Badge ── */
.target-badge {
    display: inline-block; font-size: 10px; padding: 2px 8px; border-radius: 4px;
    font-weight: 700; background: rgba(88,166,255,0.12); color: var(--accent);
}

/* ── Plan Status Badge ── */
.plan-status { display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; }
.plan-status-draft { background: rgba(107,114,128,0.15); color: #9ca3af; }
.plan-status-decomposing { background: rgba(167,139,250,0.15); color: #a78bfa; }
.plan-status-reviewing { background: rgba(245,158,11,0.15); color: #fbbf24; }
.plan-status-approved { background: rgba(59,130,246,0.15); color: #60a5fa; }
.plan-status-running { background: rgba(88,166,255,0.15); color: var(--accent); }
.plan-status-completed { background: rgba(34,197,94,0.15); color: #22c55e; }
.plan-status-failed { background: rgba(239,68,68,0.15); color: #f87171; }

/* ── Plan Form ── */
.plan-form {
    background: var(--bg-card); border-radius: 12px; padding: 24px; border: 1px solid var(--border);
}
.plan-form h2 { font-size: 18px; color: #fff; margin-bottom: 16px; }
.plan-form-group { margin-bottom: 16px; }
.plan-form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
.plan-form-group input, .plan-form-group textarea {
    width: 100%; background: var(--bg-panel); border: 1px solid var(--border); border-radius: 8px;
    padding: 10px 14px; color: var(--text-primary); font-size: 13px; font-family: inherit; box-sizing: border-box;
}
.plan-form-group input:focus, .plan-form-group textarea:focus { outline: none; border-color: var(--accent); }
.plan-form-group textarea { resize: vertical; min-height: 150px; line-height: 1.6; }

/* Target rows */
.plan-target-rows { margin-bottom: 12px; }
.plan-target-row {
    display: flex; gap: 8px; align-items: center; margin-bottom: 6px;
}
.plan-target-row input { flex: 1; }
.plan-target-row .btn-remove {
    background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 18px; padding: 4px 8px;
}
.plan-target-row .btn-remove:hover { color: #ef4444; }

/* ── Plan Review Layout ── */
.plan-review {
    display: grid; grid-template-columns: 1fr 1fr; gap: 20px; min-height: 400px;
}
@media (max-width: 900px) { .plan-review { grid-template-columns: 1fr; } }

.plan-spec-panel {
    background: var(--bg-card); border-radius: 12px; padding: 20px; border: 1px solid var(--border);
    max-height: calc(100vh - 300px); overflow-y: auto;
}
.plan-spec-panel h3 { font-size: 14px; color: var(--text-secondary); margin-bottom: 12px; }

.plan-tasks-panel {
    background: var(--bg-card); border-radius: 12px; padding: 20px; border: 1px solid var(--border);
    max-height: calc(100vh - 300px); overflow-y: auto;
}
.plan-tasks-panel h3 { font-size: 14px; color: var(--text-secondary); margin-bottom: 12px; }

/* ── Task Flow (Plan Monitor) ── */
.task-flow { display: flex; flex-direction: column; gap: 6px; }
.task-flow-item {
    display: flex; align-items: center; gap: 10px; padding: 10px 14px;
    background: var(--bg-panel); border-radius: 8px; border: 1px solid var(--border);
    cursor: pointer; transition: 0.15s;
}
.task-flow-item:hover { border-color: var(--accent); }
.task-flow-item.active { border-color: var(--accent); background: rgba(88,166,255,0.05); }
.task-flow-icon { font-size: 16px; width: 24px; text-align: center; flex-shrink: 0; }
.task-flow-title { flex: 1; font-size: 13px; color: var(--text-primary); }
.task-flow-target { font-size: 10px; }
.task-flow-time { font-size: 11px; color: var(--text-tertiary); }

/* ── Plan Monitor Layout ── */
.plan-monitor {
    display: grid; grid-template-columns: 1fr 1fr; gap: 20px; min-height: 400px;
}
@media (max-width: 900px) { .plan-monitor { grid-template-columns: 1fr; } }

.plan-monitor-left {
    background: var(--bg-card); border-radius: 12px; padding: 20px; border: 1px solid var(--border);
    max-height: calc(100vh - 300px); overflow-y: auto;
}

.plan-monitor-right {
    background: var(--bg-card); border-radius: 12px; padding: 20px; border: 1px solid var(--border);
    max-height: calc(100vh - 300px); overflow-y: auto; display: flex; flex-direction: column;
}

.plan-progress-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.plan-progress-bar {
    height: 6px; background: var(--bg-panel); border-radius: 3px; overflow: hidden; margin-bottom: 16px;
}
.plan-progress-fill {
    height: 100%; background: linear-gradient(90deg, var(--accent), #a78bfa); border-radius: 3px; transition: width 0.5s;
}

/* Plan detail output area */
.plan-output-area {
    flex: 1; background: var(--bg-page); border-radius: 8px; padding: 14px;
    font-family: 'SF Mono','Fira Code',monospace; font-size: 11px; line-height: 1.6;
    overflow-y: auto; white-space: pre-wrap; word-break: break-all; color: var(--text-secondary);
}
"""

_BODY = """
<div class="container">
    <div class="top-bar">
        <div style="display:flex;align-items:center;gap:12px;">
            <h1 style="cursor:pointer" onclick="navigate('tasks')">Claude Pilot</h1>
            <span id="statusDot" class="status-dot stopped"></span>
            <span id="statusLabel" style="color:#888;font-size:13px;">Stopped</span>
            <span id="workingText" class="working-text" style="display:none;"></span>
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

    <!-- Navigation Tabs -->
    <div class="nav-tabs" id="navTabs">
        <button class="nav-tab active" data-view="tasks" onclick="navigate('tasks')">Quick Tasks</button>
        <button class="nav-tab" data-view="plans" onclick="navigate('plans')">Plans</button>
    </div>

    <!-- Plans View (hidden by default) -->
    <div id="viewPlans" style="display:none;">
        <div id="planViewContent"></div>
    </div>

    <!-- Tasks View -->
    <div id="viewTasks">
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
    </div><!-- /viewTasks -->
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
    <div class="sp-footer" id="spFooter"></div>
</div>

<!-- Command Palette (Cmd+K) -->
<div class="cmd-palette-overlay" id="cmdPaletteOverlay">
    <div class="cmd-palette">
        <input class="cmd-palette-input" id="cmdPaletteInput" placeholder="Search tasks, actions..." autocomplete="off">
        <div class="cmd-palette-results" id="cmdPaletteResults"></div>
    </div>
</div>

<!-- Help Overlay (?) -->
<div class="help-overlay" id="helpOverlay">
    <div class="help-dialog">
        <button class="help-close" onclick="closeHelp()">&times;</button>
        <h2>Keyboard Shortcuts</h2>
        <div class="help-row"><span class="help-desc">Command palette</span><span class="help-key">&#8984;K</span></div>
        <div class="help-row"><span class="help-desc">Show this help</span><span class="help-key">?</span></div>
        <div class="help-row"><span class="help-desc">Navigate cards down</span><span class="help-key">J</span></div>
        <div class="help-row"><span class="help-desc">Navigate cards up</span><span class="help-key">K</span></div>
        <div class="help-row"><span class="help-desc">Open selected card</span><span class="help-key">Enter</span></div>
        <div class="help-row"><span class="help-desc">Close panel / modal</span><span class="help-key">Esc</span></div>
        <div class="help-row"><span class="help-desc">Focus search</span><span class="help-key">/</span></div>
        <div class="help-row"><span class="help-desc">Approve task</span><span class="help-key">A</span></div>
        <div class="help-row"><span class="help-desc">Reject task</span><span class="help-key">R</span></div>
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

let _initialLoad = true;
let _prevTaskStatuses = {};

function renderSkeletonBoard() {
    const board = document.getElementById('kanbanBoard');
    board.style.gridTemplateColumns = `repeat(${COLUMNS.length}, 1fr)`;
    board.innerHTML = COLUMNS.map(col => {
        const skeletons = Array.from({length: 3}, () =>
            `<div class="skeleton-card">
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-label"></div>
                <div class="skeleton skeleton-meta"></div>
            </div>`
        ).join('');
        return `
        <div class="kanban-col col-${col.key}">
            <div class="col-header">
                <span class="col-title">${col.title}</span>
                <span class="col-count">-</span>
            </div>
            ${skeletons}
        </div>`;
    }).join('');
}

function renderKanban(tasks) {
    allTasks = tasks;

    // Skip re-render if data unchanged
    const kanbanKey = tasks.map(t => `${t.id}:${t.status}:${t.priority}:${t.id===selectedTaskId}`).join('|');
    if(kanbanKey === _lastKanbanKey) return;

    // Detect status changes for pulse animation
    const changedIds = new Set();
    if(!_initialLoad) {
        tasks.forEach(t => {
            if(_prevTaskStatuses[t.id] && _prevTaskStatuses[t.id] !== t.status) {
                changedIds.add(t.id);
            }
        });
    }

    _lastKanbanKey = kanbanKey;
    _prevTaskStatuses = {};
    tasks.forEach(t => { _prevTaskStatuses[t.id] = t.status; });

    const board = document.getElementById('kanbanBoard');

    const hasFailed = tasks.some(t => t.status === 'failed');
    const hasCancelled = tasks.some(t => t.status === 'cancelled');
    let cols = [...COLUMNS];
    if(hasFailed) cols.push({key:'failed', title:'Failed', color:'#ef4444'});
    if(hasCancelled) cols.push({key:'cancelled', title:'Cancelled', color:'#6b7280'});

    board.style.gridTemplateColumns = `repeat(${cols.length}, 1fr)`;

    let cardIdx = 0;
    board.innerHTML = cols.map(col => {
        const colTasks = tasks.filter(t => t.status === col.key);
        let cardsHtml;
        if(colTasks.length === 0) {
            cardsHtml = `<div class="col-empty">No tasks</div>`;
        } else {
            cardsHtml = colTasks.map(t => {
                const stagger = _initialLoad ? cardIdx * 30 : 0;
                const changed = changedIds.has(t.id) ? ' state-changed' : '';
                cardIdx++;
                return renderCard(t, stagger, changed);
            }).join('');
        }
        return `
        <div class="kanban-col col-${col.key}" data-status="${col.key}"
             ondragover="onDragOver(event)" ondragleave="onDragLeave(event)" ondrop="onDrop(event)">
            <div class="col-header">
                <span class="col-title">${col.title}</span>
                <span class="col-count">${colTasks.length}</span>
            </div>
            ${cardsHtml}
        </div>`;
    }).join('');

    _initialLoad = false;
}

function renderCard(t, stagger, changed) {
    stagger = stagger || 0;
    changed = changed || '';
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

    const staggerStyle = stagger > 0 ? ` style="animation-delay:${stagger}ms"` : '';
    return `
    <div class="k-card card-${t.status}${sel}${changed}" data-task-id="${t.id}" onclick="selectTask(${t.id})"${staggerStyle}>
        <div class="drag-handle" draggable="true" ondragstart="onDragStart(event,${t.id})" title="Drag to change status">
            <div class="drag-handle-dot-row"><span class="drag-handle-dot"></span><span class="drag-handle-dot"></span></div>
            <div class="drag-handle-dot-row"><span class="drag-handle-dot"></span><span class="drag-handle-dot"></span></div>
            <div class="drag-handle-dot-row"><span class="drag-handle-dot"></span><span class="drag-handle-dot"></span></div>
        </div>
        <div class="k-card-content">
            <div class="k-card-title">${esc(t.title)}</div>
            <div class="k-card-tier2">
                <span class="k-card-id">#${t.id}</span>
                ${t.status === 'in_progress' ? '<span class="live-badge"><span class="live-dot"></span>LIVE</span>' : ''}
                ${labelPills}
            </div>
            <div class="k-card-tier3">
                <div class="k-card-tier3-left">
                    <span class="priority-dot priority-dot-${t.priority}"></span>
                    ${timeHtml}
                </div>
                <div class="k-card-actions">${actions.join('')}</div>
            </div>
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

    // ── Description / Goal (collapsible) ──
    if(t.description) {
        html += sectionHtml('description', 'Description',
            `<div class="sp-desc">${renderMarkdown(t.description)}</div>`);
    }

    // ── Labels ──
    if(t.labels && t.labels.length > 0) {
        html += `<div class="sp-section">
            <div class="sp-section-title">Labels</div>
            <div>${t.labels.map(l => `<span class="label-badge">${esc(l)}</span>`).join(' ')}</div>
        </div>`;
    }

    // ── Meta grid (collapsible) ──
    let detailsContent = '<div class="sp-meta-grid">';
    if(t.started_at)
        detailsContent += `<div class="sp-meta-item"><div class="label">Started</div><div class="value">${fmtTime(t.started_at)}</div></div>`;
    if(t.completed_at)
        detailsContent += `<div class="sp-meta-item"><div class="label">Completed</div><div class="value">${fmtTime(t.completed_at)}</div></div>`;
    if(t.exit_code !== null && t.exit_code !== undefined)
        detailsContent += `<div class="sp-meta-item"><div class="label">Exit Code</div><div class="value">${t.exit_code}</div></div>`;
    if(t.cost_usd)
        detailsContent += `<div class="sp-meta-item"><div class="label">Cost</div><div class="value">$${t.cost_usd.toFixed(4)}</div></div>`;
    if(t.branch_name)
        detailsContent += `<div class="sp-meta-item"><div class="label">Branch</div><div class="value" style="font-size:11px;font-family:monospace">${esc(t.branch_name)}</div></div>`;
    if(t.pr_url)
        detailsContent += `<div class="sp-meta-item"><div class="label">PR</div><div class="value"><a href="${esc(t.pr_url)}" target="_blank" style="color:#3b82f6;text-decoration:none;font-size:11px">#${esc(t.pr_url.split('/').pop())} ${esc(t.title)}</a></div></div>`;
    if(t.rejection_feedback)
        detailsContent += `<div class="sp-meta-item" style="grid-column:1/-1"><div class="label">Rejection Feedback</div><div class="value" style="color:#f87171">${esc(t.rejection_feedback)}</div></div>`;
    detailsContent += '</div>';
    html += sectionHtml('details', 'Details', detailsContent);

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

    // ── Output / Error (collapsible) ──
    if(t.output) {
        html += sectionHtml('logs', 'Output',
            `<div class="sp-output">${esc(t.output)}</div>`);
    } else if(t.error) {
        html += sectionHtml('logs', 'Error',
            `<div class="sp-output" style="color:#ef4444">${esc(t.error)}</div>`);
    }

    left.innerHTML = html;

    // ── Footer Actions (sticky bottom bar) ──
    const footer = document.getElementById('spFooter');
    const actions = [];
    if(t.status === 'waiting_approval') {
        actions.push(`<button class="btn btn-green" onclick="approveTask()">Approve</button>`);
        actions.push(`<button class="btn btn-red" onclick="rejectTask()">Reject</button>`);
    }
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
    footer.innerHTML = actions.join('');
    footer.style.display = actions.length ? 'flex' : 'none';
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

        // Header running effects
        const topBar = document.querySelector('.top-bar');
        const workingText = document.getElementById('workingText');
        const isActive = s.state === 'running' || s.state === 'waiting_approval';
        topBar.classList.toggle('agent-running', isActive);
        if(isActive && s.current_task_id && s.current_task_title) {
            workingText.innerHTML = `<span class="working-task">#${s.current_task_id}</span> ${esc(s.current_task_title)}<span class="working-dots"></span>`;
            workingText.style.display = '';
        } else {
            workingText.style.display = 'none';
        }

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

// ── Command Palette (Cmd+K) ──

let cmdPaletteOpen = false;
let cmdActiveIdx = 0;
let cmdItems = [];

const CMD_ACTIONS = [
    {id:'start',   icon:'\u25B6', label:'Start Agent',          fn:agentStart,   hint:''},
    {id:'stop',    icon:'\u25A0', label:'Stop Agent',           fn:agentStop,    hint:''},
    {id:'add',     icon:'+',      label:'Add Task',             fn:toggleAddForm, hint:''},
    {id:'f-all',   icon:'\u2630', label:'Filter: All',          fn:()=>setStatusFilter('all'),       hint:'Status'},
    {id:'f-pend',  icon:'\u2630', label:'Filter: Pending',      fn:()=>setStatusFilter('pending'),   hint:'Status'},
    {id:'f-run',   icon:'\u2630', label:'Filter: Running',      fn:()=>setStatusFilter('in_progress'),hint:'Status'},
    {id:'f-done',  icon:'\u2630', label:'Filter: Done',         fn:()=>setStatusFilter('done'),      hint:'Status'},
    {id:'f-fail',  icon:'\u2630', label:'Filter: Failed',       fn:()=>setStatusFilter('failed'),    hint:'Status'},
];

function openCmdPalette() {
    cmdPaletteOpen = true;
    const overlay = document.getElementById('cmdPaletteOverlay');
    overlay.classList.add('open');
    const input = document.getElementById('cmdPaletteInput');
    input.value = '';
    input.focus();
    cmdActiveIdx = 0;
    renderCmdResults('');
}

function closeCmdPalette() {
    cmdPaletteOpen = false;
    document.getElementById('cmdPaletteOverlay').classList.remove('open');
}

function renderCmdResults(query) {
    const container = document.getElementById('cmdPaletteResults');
    const q = query.toLowerCase().trim();
    cmdItems = [];
    let html = '';

    // Tasks group
    const matchedTasks = allTasksUnfiltered.filter(t =>
        t.title.toLowerCase().includes(q) || ('#' + t.id).includes(q)
    );
    if(matchedTasks.length > 0) {
        html += `<div class="cmd-palette-group"><div class="cmd-palette-group-title">Tasks</div>`;
        matchedTasks.slice(0, 8).forEach(t => {
            const idx = cmdItems.length;
            cmdItems.push({type:'task', task:t});
            html += `<div class="cmd-palette-item${idx===cmdActiveIdx?' active':''}" data-idx="${idx}" onmouseenter="cmdHover(${idx})" onclick="cmdSelect(${idx})">
                <span class="cmd-icon">#</span><span class="cmd-label">${esc(t.title)}</span><span class="cmd-hint">${STATUS_LABELS[t.status]||t.status}</span>
            </div>`;
        });
        html += `</div>`;
    }

    // Actions group
    const matchedActions = CMD_ACTIONS.filter(a => a.label.toLowerCase().includes(q));
    if(matchedActions.length > 0) {
        html += `<div class="cmd-palette-group"><div class="cmd-palette-group-title">Actions</div>`;
        matchedActions.forEach(a => {
            const idx = cmdItems.length;
            cmdItems.push({type:'action', action:a});
            html += `<div class="cmd-palette-item${idx===cmdActiveIdx?' active':''}" data-idx="${idx}" onmouseenter="cmdHover(${idx})" onclick="cmdSelect(${idx})">
                <span class="cmd-icon">${a.icon}</span><span class="cmd-label">${a.label}</span><span class="cmd-hint">${a.hint}</span>
            </div>`;
        });
        html += `</div>`;
    }

    if(cmdItems.length === 0) {
        html = `<div class="cmd-palette-empty">No results for "${esc(query)}"</div>`;
    }
    container.innerHTML = html;
}

function cmdHover(idx) {
    cmdActiveIdx = idx;
    updateCmdActive();
}

function updateCmdActive() {
    const items = document.querySelectorAll('.cmd-palette-item');
    items.forEach((el, i) => {
        el.classList.toggle('active', i === cmdActiveIdx);
    });
    // Scroll active into view
    const active = items[cmdActiveIdx];
    if(active) active.scrollIntoView({block:'nearest'});
}

function cmdSelect(idx) {
    const item = cmdItems[idx];
    if(!item) return;
    closeCmdPalette();
    if(item.type === 'task') {
        selectTask(item.task.id);
    } else if(item.type === 'action') {
        item.action.fn();
    }
}

document.getElementById('cmdPaletteInput').addEventListener('input', (e) => {
    cmdActiveIdx = 0;
    renderCmdResults(e.target.value);
});

document.getElementById('cmdPaletteInput').addEventListener('keydown', (e) => {
    if(e.key === 'ArrowDown') { e.preventDefault(); cmdActiveIdx = Math.min(cmdActiveIdx + 1, cmdItems.length - 1); updateCmdActive(); }
    else if(e.key === 'ArrowUp') { e.preventDefault(); cmdActiveIdx = Math.max(cmdActiveIdx - 1, 0); updateCmdActive(); }
    else if(e.key === 'Enter') { e.preventDefault(); cmdSelect(cmdActiveIdx); }
    else if(e.key === 'Escape') { closeCmdPalette(); }
});

document.getElementById('cmdPaletteOverlay').addEventListener('click', (e) => {
    if(e.target === e.currentTarget) closeCmdPalette();
});

// ── Help Overlay (?) ──

let helpOpen = false;

function openHelp() {
    helpOpen = true;
    document.getElementById('helpOverlay').classList.add('open');
}

function closeHelp() {
    helpOpen = false;
    document.getElementById('helpOverlay').classList.remove('open');
}

document.getElementById('helpOverlay').addEventListener('click', (e) => {
    if(e.target === e.currentTarget) closeHelp();
});

// ── Keyboard Navigation (J/K/Enter/Escape/?/A/R) ──

let kbFocusIdx = -1;

function getAllCards() {
    return Array.from(document.querySelectorAll('.k-card'));
}

function setKbFocus(idx) {
    const cards = getAllCards();
    // Remove old focus
    cards.forEach(c => c.classList.remove('kb-focus'));
    if(idx < 0 || idx >= cards.length) { kbFocusIdx = -1; return; }
    kbFocusIdx = idx;
    cards[idx].classList.add('kb-focus');
    cards[idx].scrollIntoView({block:'nearest', behavior:'smooth'});
}

function isInputFocused() {
    const el = document.activeElement;
    if(!el) return false;
    const tag = el.tagName.toLowerCase();
    return tag === 'input' || tag === 'textarea' || tag === 'select' || el.isContentEditable;
}

document.addEventListener('keydown', (e) => {
    // Cmd+K / Ctrl+K: Command palette
    if((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if(cmdPaletteOpen) closeCmdPalette(); else openCmdPalette();
        return;
    }

    // If palette is open, let palette handle keys
    if(cmdPaletteOpen) return;

    // Escape: close help, then panel
    if(e.key === 'Escape') {
        if(helpOpen) { closeHelp(); return; }
        closePanel();
        return;
    }

    // Don't handle shortcuts when typing in inputs
    if(isInputFocused()) return;

    const key = e.key.toLowerCase();

    if(key === '?') { e.preventDefault(); if(helpOpen) closeHelp(); else openHelp(); return; }
    if(key === '/') { e.preventDefault(); document.getElementById('searchInput').focus(); return; }

    if(key === 'j') {
        e.preventDefault();
        const cards = getAllCards();
        if(cards.length === 0) return;
        setKbFocus(Math.min(kbFocusIdx + 1, cards.length - 1));
        return;
    }
    if(key === 'k' && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        const cards = getAllCards();
        if(cards.length === 0) return;
        if(kbFocusIdx < 0) { setKbFocus(cards.length - 1); return; }
        setKbFocus(Math.max(kbFocusIdx - 1, 0));
        return;
    }
    if(e.key === 'Enter' && kbFocusIdx >= 0) {
        e.preventDefault();
        const cards = getAllCards();
        if(cards[kbFocusIdx]) cards[kbFocusIdx].click();
        return;
    }
    if(key === 'a') {
        // Approve if waiting_approval panel is open
        const btn = document.querySelector('#approvalPanel .btn-green');
        if(btn) { e.preventDefault(); btn.click(); }
        return;
    }
    if(key === 'r') {
        // Reject if waiting_approval panel is open
        const btn = document.querySelector('#approvalPanel .btn-red');
        if(btn) { e.preventDefault(); btn.click(); }
        return;
    }
});

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

// ── Drag and Drop ──

let dragTaskId = null;

function onDragStart(e, taskId) {
    dragTaskId = taskId;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(taskId));
    const card = e.target.closest('.k-card');
    if(card) {
        requestAnimationFrame(() => card.classList.add('dragging'));
    }
    // Prevent card click
    e.stopPropagation();
}

function onDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    const col = e.target.closest('.kanban-col');
    if(!col) return;
    col.classList.add('drag-over');

    // Show insertion line near cursor
    removeDragInsertLines();
    const cards = Array.from(col.querySelectorAll('.k-card'));
    let inserted = false;
    for(const card of cards) {
        const rect = card.getBoundingClientRect();
        if(e.clientY < rect.top + rect.height / 2) {
            const line = document.createElement('div');
            line.className = 'drag-insert-line';
            card.parentNode.insertBefore(line, card);
            inserted = true;
            break;
        }
    }
    if(!inserted && cards.length > 0) {
        const line = document.createElement('div');
        line.className = 'drag-insert-line';
        const lastCard = cards[cards.length - 1];
        lastCard.parentNode.insertBefore(line, lastCard.nextSibling);
    }
}

function onDragLeave(e) {
    const col = e.target.closest('.kanban-col');
    if(!col) return;
    // Only remove if actually leaving the column
    const related = e.relatedTarget;
    if(related && col.contains(related)) return;
    col.classList.remove('drag-over');
    removeDragInsertLines();
}

function onDrop(e) {
    e.preventDefault();
    const col = e.target.closest('.kanban-col');
    if(!col || !dragTaskId) return;
    col.classList.remove('drag-over');
    removeDragInsertLines();
    // Remove dragging class from all cards
    document.querySelectorAll('.k-card.dragging').forEach(c => c.classList.remove('dragging'));

    const newStatus = col.getAttribute('data-status');
    const task = allTasks.find(t => t.id === dragTaskId);
    if(!task || task.status === newStatus) { dragTaskId = null; return; }

    const oldStatus = task.status;
    // Optimistic UI update
    task.status = newStatus;
    _lastKanbanKey = null; // force re-render
    renderKanban(allTasks);
    if(selectedTaskId === dragTaskId) {
        _lastSlideKey = null;
        renderSlideLeft(task);
    }

    // PATCH API call
    fetch(`/api/tasks/${dragTaskId}`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({status: newStatus})
    }).then(res => {
        if(!res.ok) throw new Error('PATCH failed');
        showToast(`Moved to ${STATUS_LABELS[newStatus] || newStatus}`, 'success');
        loadTasks();
    }).catch(() => {
        // Revert on failure
        task.status = oldStatus;
        _lastKanbanKey = null;
        renderKanban(allTasks);
        showToast('Failed to move task', 'error');
    });

    dragTaskId = null;
}

function removeDragInsertLines() {
    document.querySelectorAll('.drag-insert-line').forEach(l => l.remove());
}

// Clean up dragging state on dragend
document.addEventListener('dragend', () => {
    document.querySelectorAll('.k-card.dragging').forEach(c => c.classList.remove('dragging'));
    document.querySelectorAll('.kanban-col.drag-over').forEach(c => c.classList.remove('drag-over'));
    removeDragInsertLines();
    dragTaskId = null;
});

// ── Collapsible Sections ──

const sectionCollapseState = JSON.parse(localStorage.getItem('sp-sections') || '{}');

function toggleSection(sectionKey) {
    sectionCollapseState[sectionKey] = !sectionCollapseState[sectionKey];
    localStorage.setItem('sp-sections', JSON.stringify(sectionCollapseState));
    const header = document.querySelector(`[data-section="${sectionKey}"]`);
    const body = document.querySelector(`[data-section-body="${sectionKey}"]`);
    if(header && body) {
        header.classList.toggle('collapsed', sectionCollapseState[sectionKey]);
        body.classList.toggle('collapsed', sectionCollapseState[sectionKey]);
    }
}

function sectionHtml(key, title, content) {
    const collapsed = sectionCollapseState[key] ? ' collapsed' : '';
    return `<div class="sp-section">
        <div class="sp-section-header${collapsed}" data-section="${key}" onclick="toggleSection('${key}')">
            <span class="sp-section-chevron">&#x25BC;</span>
            <div class="sp-section-title" style="margin-bottom:0">${title}</div>
        </div>
        <div class="sp-section-body${collapsed}" data-section-body="${key}">${content}</div>
    </div>`;
}

// ── Hash Router ──

let currentView = 'tasks';
let currentPlanId = null;

function navigate(route) {
    if(route === 'tasks') {
        window.location.hash = '#tasks';
    } else if(route === 'plans') {
        window.location.hash = '#plans';
    } else if(route.startsWith('plans/new')) {
        window.location.hash = '#plans/new';
    } else if(route.startsWith('plans/')) {
        window.location.hash = '#' + route;
    }
}

function handleRoute() {
    const hash = window.location.hash.slice(1) || 'tasks';
    const parts = hash.split('/');

    // Update nav tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        const view = tab.getAttribute('data-view');
        tab.classList.toggle('active', hash.startsWith(view));
    });

    if(hash === 'tasks' || hash === '') {
        showView('tasks');
        currentView = 'tasks';
    } else if(hash === 'plans') {
        showView('plans');
        currentView = 'plans';
        renderPlanList();
    } else if(hash === 'plans/new') {
        showView('plans');
        currentView = 'plans';
        renderPlanCreate();
    } else if(parts[0] === 'plans' && parts[1]) {
        showView('plans');
        currentView = 'plans';
        currentPlanId = parseInt(parts[1]);
        loadPlanDetail(currentPlanId);
    }
}

function showView(view) {
    document.getElementById('viewTasks').style.display = view === 'tasks' ? '' : 'none';
    document.getElementById('viewPlans').style.display = view === 'plans' ? '' : 'none';
}

window.addEventListener('hashchange', handleRoute);

// ── Plan List ──

let allPlans = [];

async function loadPlans() {
    try {
        const res = await fetch('/api/plans');
        allPlans = await res.json();
    } catch(e) { console.error('loadPlans', e); }
}

function renderPlanList() {
    const content = document.getElementById('planViewContent');
    content.innerHTML = '<div style="text-align:center;padding:40px;color:#666">Loading plans...</div>';
    loadPlans().then(() => {
        let html = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">';
        html += '<h2 style="color:#fff;font-size:18px;margin:0;">Plans</h2>';
        html += '<button class="btn btn-blue" onclick="navigate(\'plans/new\')">+ New Plan</button>';
        html += '</div>';

        if(allPlans.length === 0) {
            html += '<div style="text-align:center;padding:60px;color:#666;font-style:italic;">No plans yet. Create one to get started.</div>';
        } else {
            // Group by status
            const groups = [
                {label:'Running', statuses:['running','decomposing']},
                {label:'Review', statuses:['reviewing','approved']},
                {label:'Draft', statuses:['draft']},
                {label:'Completed', statuses:['completed']},
                {label:'Failed', statuses:['failed']},
            ];
            for(const g of groups) {
                const plans = allPlans.filter(p => g.statuses.includes(p.status));
                if(plans.length === 0) continue;
                html += `<div style="margin-bottom:16px;">`;
                html += `<div style="font-size:12px;font-weight:700;color:#666;text-transform:uppercase;margin-bottom:8px;">${g.label} (${plans.length})</div>`;
                for(const p of plans) {
                    const targets = Object.keys(p.targets || {});
                    const targetBadges = targets.map(t => `<span class="target-badge">${esc(t)}</span>`).join('');
                    html += `<div class="plan-card" onclick="navigate('plans/${p.id}')">
                        <div class="plan-card-header">
                            <span class="plan-card-title">${esc(p.title)}</span>
                            <span class="plan-status plan-status-${p.status}">${p.status}</span>
                        </div>
                        <div class="plan-card-meta">
                            <span>#${p.id}</span>
                            <span class="time-relative" data-time="${esc(p.updated_at)}" title="${fmtAbsolute(p.updated_at)}">${timeAgo(p.updated_at)}</span>
                        </div>
                        ${targets.length > 0 ? `<div class="plan-card-targets">${targetBadges}</div>` : ''}
                    </div>`;
                }
                html += '</div>';
            }
        }
        content.innerHTML = html;
    });
}

// ── Plan Create ──

let planTargetCount = 1;

function renderPlanCreate() {
    planTargetCount = 1;
    const content = document.getElementById('planViewContent');
    content.innerHTML = `
    <div class="plan-form">
        <h2>New Plan</h2>
        <div class="plan-form-group">
            <label>Title</label>
            <input id="planTitle" placeholder="e.g., User Authentication System">
        </div>
        <div class="plan-form-group">
            <label>Targets (project directories)</label>
            <div class="plan-target-rows" id="planTargetRows">
                <div class="plan-target-row">
                    <input placeholder="Name (e.g., backend)" class="plan-target-name">
                    <input placeholder="Path (e.g., /path/to/project)" class="plan-target-path">
                    <button class="btn-remove" onclick="this.parentElement.remove()">&times;</button>
                </div>
            </div>
            <button class="btn btn-gray btn-sm" onclick="addPlanTargetRow()">+ Add Target</button>
        </div>
        <div class="plan-form-group">
            <label>Specification</label>
            <textarea id="planSpec" placeholder="Describe what you want to build..."></textarea>
        </div>
        <div style="display:flex;gap:8px;">
            <button class="btn btn-blue" onclick="submitPlan()">Create & Decompose</button>
            <button class="btn btn-gray" onclick="navigate('plans')">Cancel</button>
        </div>
    </div>`;
}

function addPlanTargetRow() {
    const rows = document.getElementById('planTargetRows');
    const row = document.createElement('div');
    row.className = 'plan-target-row';
    row.innerHTML = `
        <input placeholder="Name (e.g., frontend)" class="plan-target-name">
        <input placeholder="Path (e.g., /path/to/project)" class="plan-target-path">
        <button class="btn-remove" onclick="this.parentElement.remove()">&times;</button>`;
    rows.appendChild(row);
}

async function submitPlan() {
    const title = document.getElementById('planTitle').value.trim();
    if(!title) { showToast('Title is required', 'error'); return; }

    const spec = document.getElementById('planSpec').value.trim();
    const targets = {};
    document.querySelectorAll('.plan-target-row').forEach(row => {
        const name = row.querySelector('.plan-target-name').value.trim();
        const path = row.querySelector('.plan-target-path').value.trim();
        if(name && path) targets[name] = {project: path};
    });

    try {
        const res = await fetch('/api/plans', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title, spec, targets})
        });
        const plan = await res.json();
        showToast('Plan created', 'success');

        // Auto-decompose
        if(spec) {
            await fetch(`/api/plans/${plan.id}/decompose`, {method: 'POST'});
            showToast('Decomposition started...', 'info');
        }

        navigate(`plans/${plan.id}`);
    } catch(e) {
        showToast('Failed to create plan', 'error');
    }
}

// ── Plan Detail ──

let planPollTimer = null;

async function loadPlanDetail(planId) {
    const content = document.getElementById('planViewContent');
    content.innerHTML = '<div style="text-align:center;padding:40px;color:#666">Loading...</div>';

    try {
        const res = await fetch(`/api/plans/${planId}`);
        if(!res.ok) { content.innerHTML = '<div style="color:#ef4444;padding:40px;text-align:center;">Plan not found</div>'; return; }
        const plan = await res.json();

        if(plan.status === 'reviewing' || plan.status === 'draft' || plan.status === 'approved') {
            renderPlanReview(plan);
        } else {
            renderPlanMonitor(plan);
        }

        // Poll for updates if running/decomposing
        if(planPollTimer) clearInterval(planPollTimer);
        if(['running','decomposing'].includes(plan.status)) {
            planPollTimer = setInterval(() => {
                if(currentView !== 'plans' || !currentPlanId) { clearInterval(planPollTimer); return; }
                loadPlanDetail(planId);
            }, 3000);
        }
    } catch(e) {
        content.innerHTML = '<div style="color:#ef4444;padding:40px;text-align:center;">Failed to load plan</div>';
    }
}

function renderPlanReview(plan) {
    const content = document.getElementById('planViewContent');
    const tasks = plan.tasks || [];
    const targets = Object.keys(plan.targets || {});

    let html = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <div style="display:flex;align-items:center;gap:12px;">
            <button class="btn btn-gray btn-sm" onclick="navigate('plans')">&larr; Back</button>
            <h2 style="color:#fff;font-size:18px;margin:0;">${esc(plan.title)}</h2>
            <span class="plan-status plan-status-${plan.status}">${plan.status}</span>
        </div>
        <div style="display:flex;gap:8px;">`;

    if(plan.status === 'reviewing') {
        html += `<button class="btn btn-green" onclick="approvePlan(${plan.id})">Approve &amp; Run</button>`;
        html += `<button class="btn btn-blue" onclick="redecomposePlan(${plan.id})">Re-decompose</button>`;
    }
    if(['draft','reviewing'].includes(plan.status)) {
        html += `<button class="btn btn-red btn-sm" onclick="deletePlan(${plan.id})">Delete</button>`;
    }
    html += `</div></div>`;

    html += '<div class="plan-review">';

    // Left: spec
    html += `<div class="plan-spec-panel">
        <h3>Specification</h3>
        <div class="sp-desc">${plan.spec ? renderMarkdown(plan.spec) : '<em style="color:#666">No specification provided</em>'}</div>
    </div>`;

    // Right: tasks
    html += `<div class="plan-tasks-panel">
        <h3>Tasks (${tasks.length})</h3>`;

    if(tasks.length === 0) {
        if(plan.status === 'decomposing') {
            html += '<div style="text-align:center;padding:40px;color:#a78bfa;">Decomposing specification into tasks...</div>';
        } else {
            html += '<div style="text-align:center;padding:40px;color:#666;font-style:italic;">No tasks yet</div>';
        }
    } else {
        html += '<div class="task-flow" id="planTaskFlow">';
        tasks.forEach((t, i) => {
            const icon = t.status === 'done' ? '&#x2705;' : t.status === 'in_progress' ? '&#x1F504;' : t.status === 'failed' ? '&#x274C;' : '&#x23F3;';
            html += `<div class="task-flow-item" data-task-id="${t.id}">
                <span class="task-flow-icon">${icon}</span>
                <span class="task-flow-title">${esc(t.title)}</span>
                ${t.target ? `<span class="task-flow-target target-badge">${esc(t.target)}</span>` : ''}
            </div>`;
        });
        html += '</div>';
    }
    html += '</div>';
    html += '</div>'; // /plan-review

    content.innerHTML = html;
}

function renderPlanMonitor(plan) {
    const content = document.getElementById('planViewContent');
    const tasks = plan.tasks || [];
    const doneCount = tasks.filter(t => t.status === 'done').length;
    const failedCount = tasks.filter(t => t.status === 'failed').length;
    const total = tasks.length;
    const pct = total > 0 ? Math.round((doneCount / total) * 100) : 0;

    let html = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <div style="display:flex;align-items:center;gap:12px;">
            <button class="btn btn-gray btn-sm" onclick="navigate('plans')">&larr; Back</button>
            <h2 style="color:#fff;font-size:18px;margin:0;">${esc(plan.title)}</h2>
            <span class="plan-status plan-status-${plan.status}">${plan.status}</span>
        </div>
        <div style="display:flex;gap:8px;">`;

    if(plan.status === 'running') {
        html += `<button class="btn btn-red" onclick="stopPlan(${plan.id})">Stop</button>`;
    }
    html += `</div></div>`;

    // Progress bar
    html += `<div class="plan-progress-header">
        <span style="font-size:13px;color:#fff;">${pct}% complete</span>
        <span style="font-size:12px;color:#666;">${doneCount}/${total} tasks done${failedCount > 0 ? `, ${failedCount} failed` : ''}</span>
    </div>
    <div class="plan-progress-bar"><div class="plan-progress-fill" style="width:${pct}%"></div></div>`;

    html += '<div class="plan-monitor">';

    // Left: task flow
    html += `<div class="plan-monitor-left">
        <h3 style="font-size:14px;color:#888;margin-bottom:12px;">Task Progress</h3>
        <div class="task-flow">`;
    tasks.forEach(t => {
        const icon = t.status === 'done' ? '&#x2705;' : t.status === 'in_progress' ? '&#x1F504;' : t.status === 'failed' ? '&#x274C;' : '&#x23F3;';
        const elapsed = getElapsed(t);
        const costStr = t.cost_usd ? `$${t.cost_usd.toFixed(4)}` : '';
        const meta = [elapsed, costStr].filter(Boolean).join(' · ');
        html += `<div class="task-flow-item${t.status === 'in_progress' ? ' active' : ''}" onclick="showPlanTaskOutput(${t.id})">
            <span class="task-flow-icon">${icon}</span>
            <span class="task-flow-title">${esc(t.title)}</span>
            ${t.target ? `<span class="task-flow-target target-badge">${esc(t.target)}</span>` : ''}
            ${meta ? `<span class="task-flow-time">${meta}</span>` : ''}
        </div>`;
    });
    html += '</div></div>';

    // Right: output area
    html += `<div class="plan-monitor-right">
        <h3 style="font-size:14px;color:#888;margin-bottom:12px;">Task Output</h3>
        <div class="plan-output-area" id="planOutputArea">
            <div style="color:#666;font-style:italic;text-align:center;padding:40px;">Click a task to view its output</div>
        </div>
    </div>`;

    html += '</div>'; // /plan-monitor

    content.innerHTML = html;
}

async function showPlanTaskOutput(taskId) {
    const area = document.getElementById('planOutputArea');
    if(!area) return;
    area.innerHTML = 'Loading...';

    // Highlight active
    document.querySelectorAll('.task-flow-item').forEach(el => {
        el.classList.toggle('active', el.getAttribute('onclick')?.includes(taskId));
    });

    try {
        const res = await fetch(`/api/tasks/${taskId}/logs`);
        const logs = await res.json();
        if(logs.length > 0) {
            area.innerHTML = logs.map(l => {
                const ts = l.timestamp ? fmtTime(l.timestamp) : '';
                return `<div class="log-line"><span class="log-time">${ts}</span> [${l.level}] ${esc(l.message)}</div>`;
            }).join('');
        } else {
            area.innerHTML = '<div style="color:#666;font-style:italic;">No logs for this task</div>';
        }
    } catch(e) {
        area.innerHTML = '<div style="color:#ef4444;">Failed to load logs</div>';
    }
}

// ── Plan Actions ──

async function approvePlan(planId) {
    try {
        await fetch(`/api/plans/${planId}/approve`, {method: 'POST'});
        showToast('Plan approved — execution started', 'success');
        loadPlanDetail(planId);
    } catch(e) { showToast('Failed to approve plan', 'error'); }
}

async function redecomposePlan(planId) {
    try {
        await fetch(`/api/plans/${planId}/decompose`, {method: 'POST'});
        showToast('Re-decomposition started...', 'info');
        loadPlanDetail(planId);
    } catch(e) { showToast('Failed to re-decompose', 'error'); }
}

async function stopPlan(planId) {
    try {
        await fetch(`/api/plans/${planId}/stop`, {method: 'POST'});
        showToast('Plan stopped', 'info');
        loadPlanDetail(planId);
    } catch(e) { showToast('Failed to stop plan', 'error'); }
}

async function deletePlan(planId) {
    if(!confirm('Delete this plan and all its tasks?')) return;
    try {
        await fetch(`/api/plans/${planId}`, {method: 'DELETE'});
        showToast('Plan deleted', 'info');
        navigate('plans');
    } catch(e) { showToast('Failed to delete plan', 'error'); }
}

// ── Init ──
renderSkeletonBoard();
loadTasks();
pollStatus();
setInterval(pollStatus, 3000);
setInterval(refreshTimeAgo, 30000);
ensureSSE();
handleRoute();
"""


def build_dashboard_html() -> str:
    return wrap_html(
        title="Claude Pilot",
        body=_BODY,
        extra_css=_EXTRA_CSS,
        extra_js=_JS,
        include_chartjs=False,
    )
