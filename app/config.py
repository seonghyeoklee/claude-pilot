"""config.yaml → Pydantic 설정"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


class AppConfig(BaseModel):
    target_project: str
    claude_command: str = "claude"
    auto_approve: bool = False
    poll_interval: int = 5
    claude_model: str | None = None
    claude_max_budget: float | None = None
    db_path: str = "data/tasks.db"
    # Gitflow
    gitflow: bool = False  # enable branch-per-task + PR workflow
    branch_prefix: str = "feat"  # branch naming: {prefix}/task-{id}-{slug}
    base_branch: str = "main"  # PR target branch
    auto_merge: bool = False  # auto-merge PR on approval (requires gh CLI)
    # Retry
    max_retries: int = 2  # max retry attempts for failed tasks (0=disable)
    retry_backoff_sec: int = 5  # backoff between retries (doubles each attempt)
    # Context injection
    context_files: list[str] = []  # files relative to target_project to inject into prompt


def load_config(path: Path | None = None) -> AppConfig:
    p = path or _CONFIG_PATH
    with open(p) as f:
        raw = yaml.safe_load(f) or {}
    return AppConfig(**raw)
