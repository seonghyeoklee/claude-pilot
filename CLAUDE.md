# CLAUDE.md

## Project Overview

**Claude Pilot** — Claude Code CLI 기반 자율 개발 에이전트 플랫폼

태스크 백로그를 관리하고, `claude -p`로 자동 구현하고, 웹 대시보드에서 진행 상황 모니터링 + 승인/반려하는 시스템.
기존 Claude Code 구독만으로 추가 API 비용 없이 동작.

## Technology Stack

- **Python 3.13+**, FastAPI, Uvicorn
- **aiosqlite**: SQLite 비동기 CRUD
- **sse-starlette**: SSE 실시간 로그 스트림
- **Pydantic v2**: 데이터 모델 + 설정
- **pytest + pytest-asyncio**: 테스트
- **uv**: 패키지 관리

## Project Structure

```
auto-dev-platform/
├── app/
│   ├── main.py           # FastAPI + lifespan (DB + Agent 초기화)
│   ├── config.py          # config.yaml → Pydantic 설정
│   ├── models.py          # Task, AgentStatus, LogEntry 모델
│   ├── database.py        # SQLite async CRUD (aiosqlite)
│   ├── agent.py           # Agent Worker (subprocess claude -p, 로그 스트리밍, 승인 게이트)
│   ├── report_theme.py    # 다크 테마 HTML 래퍼
│   ├── dashboard.py       # 대시보드 HTML 빌더
│   └── api/
│       └── routes.py      # REST API + SSE 로그 스트림
├── config.yaml            # 대상 프로젝트 경로 + 에이전트 설정
├── pyproject.toml
├── tests/
│   ├── test_database.py   # DB CRUD 테스트 (13개)
│   ├── test_agent.py      # Agent Worker 테스트 (14개)
│   └── test_dashboard.py  # 대시보드 HTML 테스트 (15개)
└── CLAUDE.md
```

## Development Commands

### Setup
```bash
uv sync --extra dev
```

### Run Server
```bash
uv run python -m app.main
# → http://localhost:9000/dashboard
```

### Run Tests
```bash
uv run pytest tests/ -v
```

## Configuration

`config.yaml`:
```yaml
target_project: /path/to/your/project   # claude -p가 실행될 프로젝트 경로
claude_command: claude                    # claude CLI 명령
auto_approve: false                       # true면 승인 게이트 건너뜀
poll_interval: 5                          # pending 태스크 폴링 주기 (초)
claude_model: null                        # --model 플래그 (null=기본)
claude_max_budget: null                   # --max-budget-usd 플래그 (null=무제한)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard` | 웹 대시보드 HTML |
| GET | `/health` | 헬스체크 |
| GET | `/api/tasks` | 태스크 목록 (?status=pending 필터 가능) |
| POST | `/api/tasks` | 태스크 생성 (`{title, description?, priority?}`) |
| PATCH | `/api/tasks/{id}` | 태스크 수정 |
| DELETE | `/api/tasks/{id}` | 태스크 삭제 |
| POST | `/api/tasks/{id}/run` | 특정 태스크 즉시 실행 |
| GET | `/api/agent/status` | 에이전트 상태 |
| POST | `/api/agent/start` | 자동 실행 루프 시작 |
| POST | `/api/agent/stop` | 자동 실행 루프 중지 |
| POST | `/api/agent/approve` | 현재 작업 승인 |
| POST | `/api/agent/reject` | 현재 작업 반려 (`{feedback}`) |
| GET | `/api/agent/logs` | SSE 실시간 로그 스트림 |
| GET | `/api/agent/output` | 현재/마지막 태스크 출력 |

## Agent Worker

### Claude CLI 호출
- `claude -p <prompt> --output-format stream-json --verbose --dangerously-skip-permissions`
- `CLAUDECODE` 환경변수 제거 (중첩 실행 허용)
- `cwd`: config의 `target_project`
- 10분 타임아웃

### 실행 플로우
```
pick_next_pending() → execute_task() → approval_gate → mark done/failed → repeat
```

### 승인 게이트
- `auto_approve: false` (기본): claude 완료 후 `waiting_approval` 상태로 대기
- 웹 UI에서 승인 → `done`, 반려 → `pending`으로 복귀 (피드백 포함)
- `auto_approve: true`: 게이트 건너뜀

### 태스크 우선순위
- 0=Low, 1=Medium (기본), 2=High, 3=Urgent
- `pick_next_pending()`: priority DESC, created_at ASC

## Task Status Flow

```
pending → in_progress → waiting_approval → done
                     ↘                  ↗
                      → failed    rejected → pending (재시도)
```

## Critical Rules

- 포트 9000 사용 (quantum-trading-platform 8000과 분리)
- SQLite DB: `data/tasks.db` (자동 생성)
- 로그 버퍼: 최근 1000줄 (deque)
- SSE 클라이언트: 인덱스 기반 새 항목 수신
