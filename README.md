# Claude Pilot

**Self-driving development agent platform powered by Claude Code CLI.**

Create tasks, let Claude execute them autonomously, review results, and ship code — all from a real-time web dashboard.

![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-267%20passed-brightgreen)

---

## What is Claude Pilot?

Claude Pilot turns [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) into a managed, autonomous development agent. Instead of running `claude` manually in your terminal, you:

1. **Create tasks** describing what you want built or fixed
2. **Start the agent** — it picks up tasks by priority and executes them
3. **Review & approve** results before they ship (or enable auto-approve)
4. **Watch it all happen** in a real-time dark-themed dashboard

No additional API costs — uses your existing Claude Code subscription.

---

## Features

- **Task Board** — Kanban-style board with drag-and-drop, priority levels, labels, search
- **Autonomous Execution** — Agent picks highest-priority pending task and runs `claude -p`
- **Approval Gate** — Pause after execution for human review; approve or reject with feedback
- **Gitflow Integration** — Auto branch creation, PR via `gh`, CodeRabbit review handling, auto-merge
- **Plan Decomposition** — Input a spec, Claude breaks it into ordered tasks across multiple projects
- **Context Chaining** — Prior task outputs are injected into subsequent task prompts
- **Real-time Logs** — SSE-based live log streaming with level filtering
- **Cost Tracking** — Per-task USD cost from Claude API usage
- **Retry Logic** — Configurable auto-retry with exponential backoff on failure
- **Dark Theme** — Full dark UI with animations, skeleton loading, reduced-motion support

---

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- [GitHub CLI](https://cli.github.com/) (`gh`) — required only for gitflow features

### Install

```bash
git clone https://github.com/seonghyeoklee/claude-pilot.git
cd claude-pilot
uv sync --extra dev
```

### Configure

Edit `config.yaml`:

```yaml
target_project: /path/to/your/project   # where claude -p runs
claude_command: claude
auto_approve: false                      # true = skip human review
poll_interval: 5                         # seconds between task polling

# Gitflow (optional)
gitflow: false
branch_prefix: feat
base_branch: main
auto_merge: true

# Retry on failure
max_retries: 2
retry_backoff_sec: 5

# Files injected into every prompt as context
context_files:
  - CLAUDE.md
  - pyproject.toml
```

### Run

```bash
uv run python -m app.main
```

Open **http://localhost:9000/dashboard**

---

## Usage

### Quick Tasks

Create a task from the dashboard or via API:

```bash
curl -X POST http://localhost:9000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Fix login validation bug", "priority": 2}'
```

Start the agent loop:

```bash
curl -X POST http://localhost:9000/api/agent/start
```

The agent will:
1. Pick the highest-priority pending task
2. Load context files from your project
3. Execute via `claude -p` with the task description
4. Stream logs to the dashboard in real-time
5. Wait for your approval (or auto-approve if configured)

### Plans

Plans let you decompose a large specification into ordered tasks:

```bash
# 1. Create a plan with spec and target projects
curl -X POST http://localhost:9000/api/plans \
  -H "Content-Type: application/json" \
  -d '{
    "title": "User Authentication System",
    "spec": "Build JWT-based auth with login, signup, password reset, and email verification.",
    "targets": {
      "backend": {"project": "/path/to/backend", "context_files": ["CLAUDE.md"]},
      "frontend": {"project": "/path/to/frontend", "context_files": ["CLAUDE.md"]}
    }
  }'

# 2. Decompose — Claude analyzes projects and creates tasks
curl -X POST http://localhost:9000/api/plans/1/decompose

# 3. Review tasks in the dashboard, reorder if needed

# 4. Approve and execute
curl -X POST http://localhost:9000/api/plans/1/approve
```

Each task runs in its target project directory with prior task outputs available as context.

---

## Dashboard

### Navigation

| View | URL Hash | Description |
|------|----------|-------------|
| Quick Tasks | `#tasks` | Kanban board for manual tasks |
| Plans | `#plans` | Plan list, create, review, monitor |

### Task Board

The kanban board shows tasks in columns by status:

- **Pending** — queued for execution
- **In Progress** — currently running (live log streaming)
- **Waiting Approval** — execution complete, awaiting review
- **Done** / **Failed** — completed or errored

Click a card to open the **slide panel** with task details, execution output, and approval controls.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Cmd+K` | Command palette |
| `j` / `k` | Navigate cards |
| `Enter` | Open selected card |
| `/` | Focus search |
| `a` | Approve (when waiting) |
| `r` | Reject (when waiting) |
| `?` | Help dialog |

---

## API Reference

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tasks` | List tasks (`?status=`, `?label=`, `?q=`) |
| `POST` | `/api/tasks` | Create task |
| `PATCH` | `/api/tasks/{id}` | Update task |
| `DELETE` | `/api/tasks/{id}` | Delete task |
| `GET` | `/api/tasks/{id}/logs` | Get persisted task logs |
| `POST` | `/api/tasks/{id}/retry` | Reset failed task to pending |
| `POST` | `/api/tasks/{id}/run` | Execute single task (background) |

### Agent

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/agent/status` | Agent state + stats |
| `POST` | `/api/agent/start` | Start auto-loop (`{min_priority?}`) |
| `POST` | `/api/agent/stop` | Stop auto-loop |
| `POST` | `/api/agent/approve` | Approve current task |
| `POST` | `/api/agent/reject` | Reject with feedback (`{feedback}`) |
| `GET` | `/api/agent/logs` | SSE log stream (`?after=`) |
| `GET` | `/api/agent/output` | Current task output |

### Plans

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/plans` | Create plan |
| `GET` | `/api/plans` | List plans (`?status=`) |
| `GET` | `/api/plans/{id}` | Get plan with tasks |
| `PATCH` | `/api/plans/{id}` | Update plan |
| `DELETE` | `/api/plans/{id}` | Delete plan |
| `POST` | `/api/plans/{id}/decompose` | Start spec decomposition |
| `POST` | `/api/plans/{id}/approve` | Approve and start execution |
| `POST` | `/api/plans/{id}/stop` | Stop running plan |
| `POST` | `/api/plans/{id}/tasks/reorder` | Reorder tasks (`{task_ids}`) |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Web Dashboard                       │
│           (Kanban + Logs + Plans)                    │
│              SSE ↑        REST ↕                     │
├─────────────────────────────────────────────────────┤
│                  FastAPI Server                       │
│              http://localhost:9000                    │
├──────────┬──────────────────┬────────────────────────┤
│ Database │   Agent Worker   │    Plan Engine         │
│ (SQLite) │                  │                        │
│          │  ┌────────────┐  │  ┌──────────────────┐  │
│  tasks   │  │ Pick task  │  │  │ Decompose spec   │  │
│  plans   │  │     ↓      │  │  │      ↓           │  │
│  logs    │  │ Inject ctx │  │  │ Create tasks     │  │
│          │  │     ↓      │  │  │      ↓           │  │
│          │  │ claude -p  │  │  │ Execute ordered  │  │
│          │  │     ↓      │  │  │ (cwd per target) │  │
│          │  │ Approval?  │  │  │      ↓           │  │
│          │  │   ↓    ↓   │  │  │ Chain context    │  │
│          │  │  Done Retry │  │  └──────────────────┘  │
│          │  └────────────┘  │                        │
├──────────┴──────────────────┴────────────────────────┤
│              Claude Code CLI (claude -p)              │
│         (subprocess per task, stream-json)            │
├─────────────────────────────────────────────────────┤
│            Target Project(s) filesystem              │
└─────────────────────────────────────────────────────┘
```

### Task Lifecycle

```
pending → in_progress → waiting_approval → done
                ↓               ↓
              failed ←── rejected (back to pending)
```

### Gitflow (when enabled)

```
1. Create branch: feat/task-{id}-{slug}
2. Claude executes task in branch
3. Commit → Push → gh pr create
4. Wait for CodeRabbit review (up to 10min)
5. Address actionable review comments (2 rounds max)
6. On approval → gh pr merge → delete branch
```

---

## Project Structure

```
claude-pilot/
├── app/
│   ├── main.py           # FastAPI entry point + lifespan
│   ├── config.py          # YAML + Pydantic config loader
│   ├── models.py          # Task, Plan, Agent, Log models
│   ├── agent.py           # Agent worker (execution engine)
│   ├── database.py        # SQLite async CRUD (aiosqlite)
│   ├── dashboard.py       # Dashboard HTML/CSS/JS builder
│   ├── report_theme.py    # Shared dark theme CSS
│   └── api/
│       └── routes.py      # REST API endpoints
├── tests/
│   ├── test_agent.py      # Agent execution tests (31)
│   ├── test_dashboard.py  # Dashboard UI tests (186)
│   └── test_database.py   # Database CRUD tests (50)
├── config.yaml            # Runtime configuration
├── pyproject.toml         # Dependencies (uv)
└── CLAUDE.md              # Project rules for Claude
```

---

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_agent.py -v
uv run pytest tests/test_database.py -v
uv run pytest tests/test_dashboard.py -v
```

267 tests covering database CRUD, agent execution logic, approval flow, retry behavior, plan decomposition, and dashboard UI rendering.

---

## Configuration Reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `target_project` | `string` | `""` | Project directory for `claude -p` execution |
| `claude_command` | `string` | `"claude"` | Path to Claude Code CLI binary |
| `auto_approve` | `bool` | `false` | Skip human approval after execution |
| `poll_interval` | `int` | `5` | Seconds between pending task checks |
| `claude_model` | `string?` | `null` | Override Claude model (e.g., `claude-sonnet-4-5-20250929`) |
| `claude_max_budget` | `float?` | `null` | Max USD spend per task |
| `gitflow` | `bool` | `false` | Enable branch + PR workflow |
| `branch_prefix` | `string` | `"feat"` | Git branch prefix |
| `base_branch` | `string` | `"main"` | PR target branch |
| `auto_merge` | `bool` | `true` | Auto-merge PR on approval |
| `max_retries` | `int` | `2` | Retry attempts on failure |
| `retry_backoff_sec` | `int` | `5` | Initial retry backoff (doubles each attempt) |
| `context_files` | `list[str]` | `["CLAUDE.md"]` | Files injected into every prompt |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.13+ |
| Web | FastAPI + Uvicorn |
| Database | SQLite (aiosqlite) |
| Frontend | Vanilla JS + CSS (single-file, no build step) |
| Real-time | Server-Sent Events (SSE) |
| Config | YAML + Pydantic v2 |
| Testing | pytest + pytest-asyncio |
| Package Manager | uv |

---

## License

MIT
