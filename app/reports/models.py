"""리포트 모델 — ReportType, ReportSnapshot, request models"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.models import _now_iso


class ReportType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    MARKET = "market"


class ReportSnapshot(BaseModel):
    id: int = 0
    report_type: ReportType = ReportType.DAILY
    period_key: str  # "2026-02-22" | "2026-W08" | "2026-02"
    net_asset: float = 0.0
    daily_pnl: float = 0.0
    daily_return_pct: float = 0.0
    total_signals: int = 0
    total_orders: int = 0
    buy_count: int = 0
    sell_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    win_rate: float = 0.0
    best_trade_pnl: float = 0.0
    worst_trade_pnl: float = 0.0
    symbols_traded: list[str] = Field(default_factory=list)
    analysis_summary: str = ""
    raw_metrics: dict = Field(default_factory=dict)
    period_start: str = ""  # YYYY-MM-DD
    period_end: str = ""  # YYYY-MM-DD
    trading_days: int = 0
    created_at: str = Field(default_factory=lambda: _now_iso())


class ReportGenerateRequest(BaseModel):
    type: ReportType
    date: str | None = None  # YYYY-MM-DD, defaults to today
    trading_api_url: str = "http://localhost:8000"
