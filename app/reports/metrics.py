"""지표 계산 + 주간/월간 집계 + period range helpers"""

from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta

from app.reports.models import ReportSnapshot


def calculate_daily_metrics(events: list[dict], positions: dict) -> dict:
    """Calculate trading metrics from journal events and positions.

    Supports two trade matching strategies:
    1. force_close events — already contain entry_price (direct P&L)
    2. FIFO matching — buy order + sell order pairs
    """
    signals = [e for e in events if e.get("event_type") == "signal"]
    orders = [e for e in events if e.get("event_type") == "order" and e.get("success")]
    force_closes = [e for e in events if e.get("event_type") == "force_close" and e.get("success")]

    buys = [o for o in orders if o.get("side", "").lower() == "buy"]
    sells = [o for o in orders if o.get("side", "").lower() == "sell"]

    trades: list[dict] = []

    # 1) force_close events: entry_price already provided
    for fc in force_closes:
        sym = fc.get("symbol", "unknown")
        sell_price = float(fc.get("current_price", 0))
        buy_price = float(fc.get("entry_price", 0))
        qty = float(fc.get("quantity", 0))
        pnl = (sell_price - buy_price) * qty
        trades.append({"symbol": sym, "pnl": pnl, "buy_price": buy_price, "sell_price": sell_price, "quantity": qty})

    # 2) FIFO matching for regular order sell events
    buy_queue: dict[str, list[dict]] = defaultdict(list)
    # Exclude symbols already handled by force_close
    fc_symbols_ts = {(fc.get("symbol"), fc.get("timestamp")) for fc in force_closes}
    for b in sorted(buys, key=lambda x: x.get("timestamp", "")):
        sym = b.get("symbol", "unknown")
        buy_queue[sym].append(b)

    for s in sorted(sells, key=lambda x: x.get("timestamp", "")):
        sym = s.get("symbol", "unknown")
        if not buy_queue[sym]:
            continue
        b = buy_queue[sym].pop(0)
        buy_price = float(b.get("current_price", b.get("price", 0)))
        sell_price = float(s.get("current_price", s.get("price", 0)))
        qty = min(float(b.get("quantity", 0)), float(s.get("quantity", 0)))
        pnl = (sell_price - buy_price) * qty
        trades.append({"symbol": sym, "pnl": pnl, "buy_price": buy_price, "sell_price": sell_price, "quantity": qty})

    win_count = sum(1 for t in trades if t["pnl"] > 0)
    loss_count = sum(1 for t in trades if t["pnl"] < 0)
    total_matched = win_count + loss_count
    win_rate = (win_count / total_matched * 100) if total_matched > 0 else 0.0

    pnl_values = [t["pnl"] for t in trades]
    best_trade_pnl = max(pnl_values) if pnl_values else 0.0
    worst_trade_pnl = min(pnl_values) if pnl_values else 0.0
    daily_pnl = sum(pnl_values)

    all_executed = orders + force_closes
    symbols_traded = sorted(set(e.get("symbol", "unknown") for e in all_executed)) if all_executed else []

    # Net asset from positions
    net_asset = 0.0
    for market in ("domestic", "us"):
        mkt = positions.get(market, {})
        summary = mkt.get("summary", {})
        net_asset += float(summary.get("net_asset", 0))

    # Per-symbol P&L breakdown
    symbol_pnl: dict[str, float] = defaultdict(float)
    for t in trades:
        symbol_pnl[t["symbol"]] += t["pnl"]

    return {
        "net_asset": net_asset,
        "daily_pnl": daily_pnl,
        "daily_return_pct": 0.0,  # computed with prev snapshot by caller
        "total_signals": len(signals),
        "total_orders": len(orders) + len(force_closes),
        "buy_count": len(buys),
        "sell_count": len(sells) + len(force_closes),
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round(win_rate, 2),
        "best_trade_pnl": round(best_trade_pnl, 2),
        "worst_trade_pnl": round(worst_trade_pnl, 2),
        "symbols_traded": symbols_traded,
        "raw_metrics": {"symbol_pnl": dict(symbol_pnl), "trades": trades},
    }


def aggregate_period(daily_snapshots: list[ReportSnapshot]) -> dict:
    """Aggregate daily snapshots into a period summary (weekly/monthly).

    daily_snapshots should be ordered by period_key ASC (oldest first).
    """
    if not daily_snapshots:
        return {
            "net_asset": 0.0,
            "daily_pnl": 0.0,
            "daily_return_pct": 0.0,
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
            "raw_metrics": {"daily_breakdown": []},
        }

    # Net asset = last day's value
    net_asset = daily_snapshots[-1].net_asset

    # P&L = sum
    total_pnl = sum(s.daily_pnl for s in daily_snapshots)

    # Cumulative return = product of (1 + r/100) - 1
    cumulative = 1.0
    for s in daily_snapshots:
        cumulative *= (1 + s.daily_return_pct / 100)
    cumulative_return = round((cumulative - 1) * 100, 4)

    # Sum counts
    total_signals = sum(s.total_signals for s in daily_snapshots)
    total_orders = sum(s.total_orders for s in daily_snapshots)
    buy_count = sum(s.buy_count for s in daily_snapshots)
    sell_count = sum(s.sell_count for s in daily_snapshots)
    win_count = sum(s.win_count for s in daily_snapshots)
    loss_count = sum(s.loss_count for s in daily_snapshots)
    total_matched = win_count + loss_count
    win_rate = round((win_count / total_matched * 100), 2) if total_matched > 0 else 0.0

    # Best/worst across all days
    best_vals = [s.best_trade_pnl for s in daily_snapshots if s.best_trade_pnl != 0]
    worst_vals = [s.worst_trade_pnl for s in daily_snapshots if s.worst_trade_pnl != 0]
    best_trade_pnl = max(best_vals) if best_vals else 0.0
    worst_trade_pnl = min(worst_vals) if worst_vals else 0.0

    # Unique symbols
    all_symbols: set[str] = set()
    for s in daily_snapshots:
        all_symbols.update(s.symbols_traded)

    # Daily breakdown for raw_metrics
    daily_breakdown = []
    for s in daily_snapshots:
        daily_breakdown.append({
            "date": s.period_key,
            "pnl": s.daily_pnl,
            "return_pct": s.daily_return_pct,
            "net_asset": s.net_asset,
            "orders": s.total_orders,
            "win": s.win_count,
            "loss": s.loss_count,
        })

    return {
        "net_asset": net_asset,
        "daily_pnl": total_pnl,
        "daily_return_pct": cumulative_return,
        "total_signals": total_signals,
        "total_orders": total_orders,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": win_rate,
        "best_trade_pnl": best_trade_pnl,
        "worst_trade_pnl": worst_trade_pnl,
        "symbols_traded": sorted(all_symbols),
        "raw_metrics": {"daily_breakdown": daily_breakdown},
    }


def get_iso_week_range(d: date) -> tuple[str, str, str]:
    """Return (period_key, start_date, end_date) for ISO week containing d.

    Returns: ("2026-W08", "2026-02-16", "2026-02-22")
    Week starts Monday, ends Sunday.
    """
    iso_year, iso_week, _ = d.isocalendar()
    period_key = f"{iso_year}-W{iso_week:02d}"
    # Monday of that week
    start = datetime.strptime(f"{iso_year}-W{iso_week:02d}-1", "%G-W%V-%u").date()
    end = start + timedelta(days=6)  # Sunday
    return period_key, start.isoformat(), end.isoformat()


def get_month_range(d: date) -> tuple[str, str, str]:
    """Return (period_key, start_date, end_date) for the month containing d.

    Returns: ("2026-02", "2026-02-01", "2026-02-28")
    """
    period_key = d.strftime("%Y-%m")
    start = d.replace(day=1)
    _, last_day = calendar.monthrange(d.year, d.month)
    end = d.replace(day=last_day)
    return period_key, start.isoformat(), end.isoformat()
