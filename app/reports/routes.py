"""통합 report router"""

from __future__ import annotations

import asyncio
import logging
from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.database import Database
from app.reports.html_builder import build_report_html
from app.reports.metrics import (
    aggregate_period,
    calculate_daily_metrics,
    get_iso_week_range,
    get_month_range,
)
from app.reports.models import ReportGenerateRequest, ReportSnapshot, ReportType

logger = logging.getLogger(__name__)

report_router = APIRouter()


def _get_db(request: Request) -> Database:
    return request.app.state.db


# ── POST /api/reports/generate ──


@report_router.post("/api/reports/generate")
async def generate_report(
    body: ReportGenerateRequest,
    db: Database = Depends(_get_db),
):
    if body.type == ReportType.DAILY:
        return await _generate_daily(body, db)
    elif body.type == ReportType.WEEKLY:
        return await _generate_weekly(body, db)
    elif body.type == ReportType.MONTHLY:
        return await _generate_monthly(body, db)
    elif body.type == ReportType.MARKET:
        return await _generate_market(body, db)
    raise HTTPException(400, f"Unknown report type: {body.type}")


async def _generate_daily(req: ReportGenerateRequest, db: Database) -> dict:
    target_date = req.date or date.today().isoformat()
    trading_url = req.trading_api_url.rstrip("/")

    # Fetch journal + positions concurrently
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            journal_task = client.get(f"{trading_url}/trading/journal/{target_date}")
            positions_task = client.get(f"{trading_url}/trading/positions")
            journal_resp, positions_resp = await asyncio.gather(journal_task, positions_task)
    except httpx.ConnectError:
        raise HTTPException(502, f"Cannot connect to trading platform at {trading_url}")
    except httpx.RequestError as exc:
        raise HTTPException(502, f"Trading platform request failed: {exc}")

    # Parse journal events
    events: list[dict] = []
    if journal_resp.status_code == 200:
        journal_data = journal_resp.json()
        events = journal_data.get("events") or journal_data.get("trades") or journal_data.get("entries") or []

    # Parse positions
    positions: dict = {}
    if positions_resp.status_code == 200:
        positions = positions_resp.json()

    # Calculate metrics
    metrics = calculate_daily_metrics(events, positions)

    # Compute daily_return_pct from previous snapshot
    recent = await db.list_reports(ReportType.DAILY, limit=2)
    prev = next((s for s in recent if s.period_key != target_date), None)
    if prev and prev.net_asset > 0 and metrics["net_asset"] > 0:
        metrics["daily_return_pct"] = round(
            (metrics["net_asset"] - prev.net_asset) / prev.net_asset * 100, 4
        )

    # Upsert
    snapshot = await db.upsert_report(
        ReportType.DAILY, target_date, metrics,
        period_start=target_date, period_end=target_date, trading_days=1,
    )
    return snapshot.model_dump()


async def _generate_weekly(req: ReportGenerateRequest, db: Database) -> dict:
    target_date = date.fromisoformat(req.date) if req.date else date.today()
    period_key, start, end = get_iso_week_range(target_date)

    # Get daily snapshots in range
    dailies = await db.get_daily_range(start, end)
    if not dailies:
        raise HTTPException(404, f"No daily reports found for week {period_key} ({start} ~ {end})")

    # Aggregate
    metrics = aggregate_period(dailies)

    snapshot = await db.upsert_report(
        ReportType.WEEKLY, period_key, metrics,
        period_start=start, period_end=end, trading_days=len(dailies),
    )
    return snapshot.model_dump()


async def _generate_monthly(req: ReportGenerateRequest, db: Database) -> dict:
    target_date = date.fromisoformat(req.date) if req.date else date.today()
    period_key, start, end = get_month_range(target_date)

    # Get daily snapshots in range
    dailies = await db.get_daily_range(start, end)
    if not dailies:
        raise HTTPException(404, f"No daily reports found for month {period_key} ({start} ~ {end})")

    # Aggregate
    metrics = aggregate_period(dailies)

    snapshot = await db.upsert_report(
        ReportType.MONTHLY, period_key, metrics,
        period_start=start, period_end=end, trading_days=len(dailies),
    )
    return snapshot.model_dump()


async def _generate_market(req: ReportGenerateRequest, db: Database) -> dict:
    target_date = req.date or date.today().isoformat()
    trading_url = req.trading_api_url.rstrip("/")

    market_data: dict = {}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{trading_url}/trading/market/{target_date}")
            if resp.status_code == 200:
                market_data = resp.json()
    except httpx.RequestError:
        logger.warning("Failed to fetch market data for %s", target_date)

    # Also fetch portfolio data for comparison
    net_asset = 0.0
    daily_pnl = 0.0
    daily_return_pct = 0.0
    daily = await db.get_report(ReportType.DAILY, target_date)
    if daily:
        net_asset = daily.net_asset
        daily_pnl = daily.daily_pnl
        daily_return_pct = daily.daily_return_pct

    metrics: dict = {
        "net_asset": net_asset,
        "daily_pnl": daily_pnl,
        "daily_return_pct": daily_return_pct,
        "total_signals": 0,
        "total_orders": 0,
        "buy_count": 0,
        "sell_count": 0,
        "win_count": 0,
        "loss_count": 0,
        "win_rate": 0.0,
        "best_trade_pnl": 0.0,
        "worst_trade_pnl": 0.0,
        "symbols_traded": [],
        "analysis_summary": market_data.get("summary", ""),
        "raw_metrics": {"market_data": market_data},
    }

    snapshot = await db.upsert_report(
        ReportType.MARKET, target_date, metrics,
        period_start=target_date, period_end=target_date, trading_days=1,
    )
    return snapshot.model_dump()


# ── GET /api/reports ──


@report_router.get("/api/reports")
async def list_reports(
    type: str | None = None,
    limit: int = 30,
    db: Database = Depends(_get_db),
):
    report_type = ReportType(type) if type else None
    reports = await db.list_reports(report_type, limit=limit)
    return [r.model_dump() for r in reports]


# ── GET /api/reports/{type}/{period_key} ──


@report_router.get("/api/reports/{report_type}/{period_key}")
async def get_report_json(
    report_type: str,
    period_key: str,
    db: Database = Depends(_get_db),
):
    rt = ReportType(report_type)
    report = await db.get_report(rt, period_key)
    if not report:
        raise HTTPException(404, f"No {report_type} report found for {period_key}")
    return report.model_dump()


# ── GET /api/reports/{type}/{period_key}/html ──


@report_router.get("/api/reports/{report_type}/{period_key}/html")
async def get_report_html(
    report_type: str,
    period_key: str,
    db: Database = Depends(_get_db),
):
    rt = ReportType(report_type)
    report = await db.get_report(rt, period_key)
    if not report:
        raise HTTPException(404, f"No {report_type} report found for {period_key}")

    context: dict = {}
    if rt == ReportType.DAILY:
        # Provide history for cumulative chart
        history = await db.list_reports(ReportType.DAILY, limit=30)
        context["history"] = history

    html = build_report_html(report, context)
    return HTMLResponse(html)
