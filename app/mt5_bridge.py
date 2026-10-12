"""Read-only MetaTrader 5 access. Trade APIs are not used here."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.config import settings

TIMEFRAME_MAP = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
    "W1": 10080,
}


def _mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError("MetaTrader5 package is not installed") from exc
    return mt5


def initialize() -> None:
    mt5 = _mt5()
    kwargs: dict[str, Any] = {}
    if settings.mt5_path:
        kwargs["path"] = settings.mt5_path
    if settings.mt5_login and settings.mt5_password and settings.mt5_server:
        kwargs.update(
            login=int(settings.mt5_login),
            password=settings.mt5_password,
            server=settings.mt5_server,
        )
    ok = mt5.initialize(**kwargs) if kwargs else mt5.initialize()
    if not ok:
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")


def shutdown() -> None:
    try:
        _mt5().shutdown()
    except RuntimeError:
        pass


def account() -> dict[str, Any]:
    mt5 = _mt5()
    info = mt5.account_info()
    if info is None:
        raise RuntimeError(f"account_info failed: {mt5.last_error()}")
    data = info._asdict()
    return {
        "login": data.get("login"),
        "name": data.get("name"),
        "server": data.get("server"),
        "currency": data.get("currency"),
        "balance": data.get("balance"),
        "equity": data.get("equity"),
        "margin": data.get("margin"),
        "margin_free": data.get("margin_free"),
        "profit": data.get("profit"),
        "leverage": data.get("leverage"),
        "trade_allowed": False,
        "read_only": True,
    }


def symbols() -> list[dict[str, Any]]:
    mt5 = _mt5()
    items = mt5.symbols_get()
    if items is None:
        raise RuntimeError(f"symbols_get failed: {mt5.last_error()}")
    out = []
    for s in items:
        if not s.visible:
            continue
        out.append(
            {
                "name": s.name,
                "path": s.path,
                "description": s.description,
                "digits": s.digits,
                "point": s.point,
                "trade_contract_size": s.trade_contract_size,
            }
        )
    return out


def tick(symbol: str) -> dict[str, Any]:
    mt5 = _mt5()
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"symbol_select failed for {symbol}: {mt5.last_error()}")
    t = mt5.symbol_info_tick(symbol)
    if t is None:
        raise RuntimeError(f"tick failed for {symbol}: {mt5.last_error()}")
    return {
        "symbol": symbol,
        "bid": t.bid,
        "ask": t.ask,
        "last": t.last,
        "time": datetime.fromtimestamp(t.time, tz=timezone.utc).isoformat(),
    }


def rates(symbol: str, timeframe: str, count: int = 300) -> list[dict[str, Any]]:
    mt5 = _mt5()
    tf_key = timeframe.upper()
    if tf_key not in TIMEFRAME_MAP:
        raise ValueError(f"unsupported timeframe: {timeframe}")
    tf_const = getattr(_mt5(), f"TIMEFRAME_{tf_key}")
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"symbol_select failed for {symbol}: {mt5.last_error()}")
    raw = mt5.copy_rates_from_pos(symbol, tf_const, 0, count)
    if raw is None:
        raise RuntimeError(f"copy_rates failed for {symbol} {tf_key}: {mt5.last_error()}")
    rows = []
    for row in raw:
        rows.append(
            {
                "time": datetime.fromtimestamp(int(row["time"]), tz=timezone.utc).isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "tick_volume": int(row["tick_volume"]),
            }
        )
    return rows


def positions() -> list[dict[str, Any]]:
    mt5 = _mt5()
    items = mt5.positions_get()
    if items is None:
        return []
    out = []
    for p in items:
        d = p._asdict()
        out.append(
            {
                "ticket": d.get("ticket"),
                "symbol": d.get("symbol"),
                "type": "buy" if d.get("type") == 0 else "sell",
                "volume": d.get("volume"),
                "price_open": d.get("price_open"),
                "price_current": d.get("price_current"),
                "sl": d.get("sl"),
                "tp": d.get("tp"),
                "profit": d.get("profit"),
                "comment": d.get("comment"),
            }
        )
    return out


def deals(limit: int = 50) -> list[dict[str, Any]]:
    mt5 = _mt5()
    from datetime import timedelta

    now = datetime.now()
    items = mt5.history_deals_get(now - timedelta(days=30), now)
    if items is None:
        return []
    out = []
    for d in list(items)[-limit:]:
        row = d._asdict()
        out.append(
            {
                "ticket": row.get("ticket"),
                "symbol": row.get("symbol"),
                "type": row.get("type"),
                "volume": row.get("volume"),
                "price": row.get("price"),
                "profit": row.get("profit"),
                "time": datetime.fromtimestamp(row.get("time", 0), tz=timezone.utc).isoformat(),
            }
        )
    return out
