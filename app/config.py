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


def load_config(path: Path | None = None) -> AppConfig:
    p = path or _CONFIG_PATH
    with open(p) as f:
        raw = yaml.safe_load(f) or {}
    return AppConfig(**raw)
