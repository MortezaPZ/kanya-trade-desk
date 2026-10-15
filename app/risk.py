from __future__ import annotations

from typing import Any


def exposure(account: dict[str, Any], positions: list[dict[str, Any]]) -> dict[str, Any]:
    equity = float(account.get("equity") or 0)
    balance = float(account.get("balance") or 0)
    floating = float(account.get("profit") or 0)
    by_symbol: dict[str, float] = {}
    for p in positions:
        by_symbol[p["symbol"]] = by_symbol.get(p["symbol"], 0.0) + float(p.get("profit") or 0)
    return {
        "equity": equity,
        "balance": balance,
        "floating_pnl": floating,
        "open_count": len(positions),
        "profit_by_symbol": by_symbol,
        "used_margin_pct": _pct(account.get("margin"), equity),
        "floating_pct": _pct(floating, equity),
    }


def size_hint(equity: float, risk_pct: float, stop_distance: float, tick_value_per_lot: float) -> dict[str, Any]:
    risk_money = max(equity, 0) * (risk_pct / 100)
    if stop_distance <= 0 or tick_value_per_lot <= 0:
        lots = 0.0
    else:
        lots = risk_money / (stop_distance * tick_value_per_lot)
    return {
        "risk_pct": risk_pct,
        "risk_money": round(risk_money, 2),
        "suggested_lots": round(max(lots, 0), 6),
        "stop_distance": stop_distance,
        "tick_value_per_lot": tick_value_per_lot,
        "advisory_only": True,
        "sends_order": False,
    }


def normalize_lots(
    lots: float,
    volume_min: float,
    volume_step: float,
    volume_max: float = 0,
) -> tuple[float, bool]:
    """Round down to broker limits; never increase size to meet the minimum lot."""
    if lots <= 0 or volume_step <= 0 or volume_min <= 0:
        return 0.0, False
    capped = min(lots, volume_max) if volume_max > 0 else lots
    steps = int((capped + 1e-12) / volume_step)
    rounded = round(steps * volume_step, 6)
    if rounded + 1e-9 < volume_min:
        return 0.0, True
    return rounded, False


def _pct(part: Any, whole: float) -> float:
    try:
        p = float(part or 0)
    except (TypeError, ValueError):
        return 0.0
    if whole <= 0:
        return 0.0
    return round(100 * p / whole, 2)
