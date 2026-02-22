"""지표 계산 + 주간/월간 집계 + period range helpers"""

from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta

from app.reports.models import ReportSnapshot


def _extract_time(ts_str: str) -> str:
    """Extract HH:MM from ISO timestamp string."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except (ValueError, TypeError):
        return ""


def _calc_hold_minutes(buy_ts: str, sell_ts: str) -> int:
    """Calculate hold duration in minutes between two ISO timestamps."""
    try:
        buy_dt = datetime.fromisoformat(buy_ts.replace("Z", "+00:00"))
        sell_dt = datetime.fromisoformat(sell_ts.replace("Z", "+00:00"))
        return max(0, int((sell_dt - buy_dt).total_seconds() / 60))
    except (ValueError, TypeError):
        return 0


def calculate_daily_metrics(events: list[dict], positions: dict) -> dict:
    """Calculate trading metrics from journal events and positions.

    Supports two trade matching strategies:
    1. force_close events — already contain entry_price (direct P&L)
    2. FIFO matching — buy order + sell order pairs

    Each trade includes: symbol, pnl, buy_price, sell_price, quantity,
    buy_time, sell_time, hold_minutes, reason, return_pct.
    """
    signals = [e for e in events if e.get("event_type") == "signal"]
    orders = [e for e in events if e.get("event_type") == "order" and e.get("success")]
    force_closes = [e for e in events if e.get("event_type") == "force_close" and e.get("success")]

    buys = [o for o in orders if o.get("side", "").lower() == "buy"]
    sells = [o for o in orders if o.get("side", "").lower() == "sell"]

    trades: list[dict] = []

    # Build buy queue (sorted by timestamp, FIFO)
    buy_queue: dict[str, list[dict]] = defaultdict(list)
    for b in sorted(buys, key=lambda x: x.get("timestamp", "")):
        buy_queue[b.get("symbol", "unknown")].append(b)

    # 1) FIFO matching for regular sells FIRST (they consume earliest buys)
    for s in sorted(sells, key=lambda x: x.get("timestamp", "")):
        sym = s.get("symbol", "unknown")
        if not buy_queue[sym]:
            continue
        b = buy_queue[sym].pop(0)
        buy_price = float(b.get("current_price", b.get("price", 0)))
        sell_price = float(s.get("current_price", s.get("price", 0)))
        qty = min(float(b.get("quantity", 0)), float(s.get("quantity", 0)))
        pnl = (sell_price - buy_price) * qty
        return_pct = ((sell_price - buy_price) / buy_price * 100) if buy_price else 0.0

        buy_ts = b.get("timestamp", "")
        sell_ts = s.get("timestamp", "")

        trades.append({
            "symbol": sym, "pnl": pnl,
            "buy_price": buy_price, "sell_price": sell_price, "quantity": qty,
            "buy_time": _extract_time(buy_ts), "sell_time": _extract_time(sell_ts),
            "hold_minutes": _calc_hold_minutes(buy_ts, sell_ts),
            "reason": "signal", "return_pct": round(return_pct, 2),
        })

    # 2) force_close events: use entry_price for P&L, remaining buys for timestamp
    for fc in force_closes:
        sym = fc.get("symbol", "unknown")
        sell_price = float(fc.get("current_price", 0))
        buy_price = float(fc.get("entry_price", 0))
        qty = float(fc.get("quantity", 0))
        pnl = (sell_price - buy_price) * qty
        return_pct = ((sell_price - buy_price) / buy_price * 100) if buy_price else 0.0

        sell_ts = fc.get("timestamp", "")
        buy_ts = ""
        if buy_queue[sym]:
            matched_buy = buy_queue[sym].pop(0)
            buy_ts = matched_buy.get("timestamp", "")

        trades.append({
            "symbol": sym, "pnl": pnl,
            "buy_price": buy_price, "sell_price": sell_price, "quantity": qty,
            "buy_time": _extract_time(buy_ts), "sell_time": _extract_time(sell_ts),
            "hold_minutes": _calc_hold_minutes(buy_ts, sell_ts),
            "reason": "force_close", "return_pct": round(return_pct, 2),
        })

    # Sort trades by sell_time for chronological display
    trades.sort(key=lambda t: t.get("sell_time", ""))

    win_count = sum(1 for t in trades if t["pnl"] > 0)
    loss_count = sum(1 for t in trades if t["pnl"] < 0)
    draw_count = sum(1 for t in trades if t["pnl"] == 0)
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
    symbol_trades: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        symbol_pnl[t["symbol"]] += t["pnl"]
        symbol_trades[t["symbol"]].append(t)

    # Per-symbol aggregation (count, total_invested, avg return)
    symbol_stats: dict[str, dict] = {}
    for sym, sym_trades in symbol_trades.items():
        count = len(sym_trades)
        invested = sum(t["buy_price"] * t["quantity"] for t in sym_trades)
        avg_hold = int(sum(t["hold_minutes"] for t in sym_trades) / count) if count else 0
        total_ret = sum(t["return_pct"] for t in sym_trades) / count if count else 0.0
        symbol_stats[sym] = {
            "count": count, "pnl": symbol_pnl[sym],
            "invested": invested, "avg_hold": avg_hold,
            "return_pct": round(total_ret, 2),
        }

    # Aggregated stats
    total_invested = sum(t["buy_price"] * t["quantity"] for t in trades)
    hold_times = [t["hold_minutes"] for t in trades if t["hold_minutes"] > 0]
    avg_hold_minutes = int(sum(hold_times) / len(hold_times)) if hold_times else 0

    win_pnls = [t["pnl"] for t in trades if t["pnl"] > 0]
    loss_pnls = [t["pnl"] for t in trades if t["pnl"] < 0]
    avg_win = int(sum(win_pnls) / len(win_pnls)) if win_pnls else 0
    avg_loss = int(sum(loss_pnls) / len(loss_pnls)) if loss_pnls else 0

    # Reason breakdown
    signal_trades = [t for t in trades if t["reason"] == "signal"]
    fc_trades = [t for t in trades if t["reason"] == "force_close"]
    reason_breakdown = {
        "signal": {"count": len(signal_trades), "pnl": sum(t["pnl"] for t in signal_trades)},
        "force_close": {"count": len(fc_trades), "pnl": sum(t["pnl"] for t in fc_trades)},
    }

    # Cumulative P&L timeline (for intraday chart)
    cum_pnl_timeline: list[dict] = []
    running = 0.0
    for t in trades:
        running += t["pnl"]
        cum_pnl_timeline.append({"time": t["sell_time"], "cum_pnl": running})

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
        "raw_metrics": {
            "symbol_pnl": dict(symbol_pnl),
            "symbol_stats": symbol_stats,
            "trades": trades,
            "total_invested": total_invested,
            "avg_hold_minutes": avg_hold_minutes,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "draw_count": draw_count,
            "reason_breakdown": reason_breakdown,
            "cum_pnl_timeline": cum_pnl_timeline,
        },
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
