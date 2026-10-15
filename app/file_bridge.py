from __future__ import annotations

import csv
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_CANDIDATES = [
    Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal" / "Common" / "Files" / "desk",
    Path(__file__).resolve().parents[1] / "runtime" / "mt5" / "MQL5" / "Files" / "desk",
    Path(__file__).resolve().parents[1] / "runtime" / "mt5" / "Files" / "desk",
]


def _desk_dir() -> Path:
    existing = [p for p in _CANDIDATES if (p / "account.csv").exists()]
    if existing:
        return max(existing, key=lambda p: (p / "account.csv").stat().st_mtime)
    return _CANDIDATES[0]


COMMON = _CANDIDATES[0]
_REQUEST_LOCK = threading.Lock()
_SUPPORTED_TIMEFRAMES = {"M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"}
_SYMBOL_PATTERN = re.compile(r"^[\x20-\x7e]{1,64}$")


def _symbol_file_key(symbol: str) -> str:
    return "".join("_" if char in '<>:\"/\\|?*' else char for char in symbol)


def market_data_stale(symbol: str, timeframes: list[str], max_age_seconds: int = 3) -> bool:
    directory = _desk_dir()
    names = [f"tick_{_symbol_file_key(symbol)}.csv"]
    names.extend(f"rates_{_symbol_file_key(symbol)}_{tf.upper()}.csv" for tf in timeframes)
    now = time.time()
    for name in names:
        path = directory / name
        try:
            if now - path.stat().st_mtime > max_age_seconds:
                return True
        except FileNotFoundError:
            return True
    return False


def request_market(items: list[dict[str, Any]], timeout_seconds: float = 12) -> None:
    """Ask the running MT5 dump script for fresh rates for one or more symbols."""
    if not items:
        return
    request_id = uuid.uuid4().hex
    rows = [request_id]
    for item in items:
        symbol = str(item.get("symbol") or "").strip()
        if not _SYMBOL_PATTERN.fullmatch(symbol) or "|" in symbol:
            raise ValueError("Unsupported symbol name for the MT5 file bridge")
        timeframes = [str(tf).strip().upper() for tf in item.get("timeframes", [])]
        if not timeframes or any(tf not in _SUPPORTED_TIMEFRAMES for tf in timeframes):
            raise ValueError(f"Unsupported timeframes in market request for {symbol}")
        rows.append(f"{symbol}|{','.join(dict.fromkeys(timeframes))}")

    directory = _desk_dir()
    directory.mkdir(parents=True, exist_ok=True)
    request_path = directory / "market_request.txt"
    response_path = directory / f"market_response_{request_id}.txt"
    temporary_path = directory / f"market_request.{request_id}.tmp"
    payload = "\n".join(rows) + "\n"

    with _REQUEST_LOCK:
        temporary_path.write_text(payload, encoding="ascii")
        temporary_path.replace(request_path)
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                response = response_path.read_text(encoding="ascii").strip().split("|")
            except (FileNotFoundError, PermissionError):
                response = []
            if len(response) >= 2 and response[0] == request_id:
                if response[1] == "done":
                    response_path.unlink(missing_ok=True)
                    return
                if response[1] == "error":
                    response_path.unlink(missing_ok=True)
                    raise RuntimeError("MT5 rejected the market data request")
            time.sleep(0.1)
        raise TimeoutError(
            "MT5 did not answer the market data request. Keep the ReadOnlyDesk script running."
        )


def available(max_age_seconds: int = 30) -> bool:
    global COMMON
    COMMON = _desk_dir()
    account = COMMON / "account.csv"
    if not account.exists():
        return False
    age = datetime.now().timestamp() - account.stat().st_mtime
    return age <= max_age_seconds


def _rows(name: str) -> list[list[str]]:
    path = _desk_dir() / name
    if not path.exists():
        return []
    for attempt in range(3):
        try:
            with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
                return [row for row in csv.reader(fh) if row]
        except PermissionError:
            if attempt == 2:
                raise
            time.sleep(0.05)
    return []


def _kv(name: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in _rows(name):
        if len(row) >= 2:
            out[row[0]] = row[1]
    return out


def _num(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except ValueError:
        return default


def _iso(value: str) -> str:
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue
    return value


def account() -> dict[str, Any]:
    d = _kv("account.csv")
    if "login" not in d:
        raise RuntimeError("file bridge has no account dump; attach ReadOnlyDesk to a chart")
    return {
        "login": int(_num(d.get("login"))),
        "name": d.get("name"),
        "server": d.get("server"),
        "currency": d.get("currency"),
        "balance": _num(d.get("balance")),
        "equity": _num(d.get("equity")),
        "margin": _num(d.get("margin")),
        "margin_free": _num(d.get("margin_free")),
        "profit": _num(d.get("profit")),
        "leverage": int(_num(d.get("leverage"))),
        "trade_allowed": False,
        "read_only": True,
        "backend": "file",
    }


def positions() -> list[dict[str, Any]]:
    rows = _rows("positions.csv")
    if len(rows) < 2:
        return []
    header = rows[0]
    out = []
    for row in rows[1:]:
        item = dict(zip(header, row))
        out.append(
            {
                "ticket": item.get("ticket"),
                "symbol": item.get("symbol"),
                "type": item.get("type"),
                "volume": _num(item.get("volume")),
                "price_open": _num(item.get("price_open")),
                "price_current": _num(item.get("price_current")),
                "sl": _num(item.get("sl")),
                "tp": _num(item.get("tp")),
                "profit": _num(item.get("profit")),
                "comment": item.get("comment"),
            }
        )
    return out


def deals(limit: int = 50) -> list[dict[str, Any]]:
    rows = _rows("deals.csv")
    if len(rows) < 2:
        return []
    header = rows[0]
    out = []
    for row in rows[1:][-limit:]:
        item = dict(zip(header, row))
        out.append(
            {
                "ticket": item.get("ticket"),
                "symbol": item.get("symbol"),
                "type": item.get("type"),
                "volume": _num(item.get("volume")),
                "price": _num(item.get("price")),
                "profit": _num(item.get("profit")),
                "time": _iso(item.get("time") or ""),
            }
        )
    return out


def symbols() -> list[dict[str, Any]]:
    rows = _rows("symbols.csv")
    if len(rows) < 2:
        return []
    header = rows[0]
    out = []
    for row in rows[1:]:
        item = dict(zip(header, row))
        out.append(
            {
                "name": item.get("name"),
                "path": item.get("path"),
                "description": item.get("description"),
                "digits": int(_num(item.get("digits"))),
                "point": _num(item.get("point")),
                "trade_contract_size": _num(item.get("trade_contract_size")),
                "trade_tick_size": _num(item.get("tick_size")),
                "trade_tick_value": _num(item.get("tick_value")),
                "volume_min": _num(item.get("volume_min")),
                "volume_step": _num(item.get("volume_step")),
                "volume_max": _num(item.get("volume_max")),
                "visible": bool(_num(item.get("visible"))),
            }
        )
    return out


def symbol_spec(symbol: str) -> dict[str, Any]:
    rows = _rows("symbols.csv")
    if len(rows) < 2:
        raise RuntimeError("MT5 symbol catalog is not available")
    header = rows[0]
    for row in rows[1:]:
        item = dict(zip(header, row))
        if (item.get("name") or "").upper() == symbol.upper():
            return {
                "name": item.get("name"),
                "path": item.get("path"),
                "description": item.get("description"),
                "digits": int(_num(item.get("digits"))),
                "point": _num(item.get("point")),
                "trade_tick_size": _num(item.get("tick_size")),
                "trade_tick_value": _num(item.get("tick_value")),
                "trade_contract_size": _num(item.get("trade_contract_size")),
                "volume_min": _num(item.get("volume_min")),
                "volume_step": _num(item.get("volume_step")),
                "volume_max": _num(item.get("volume_max")),
            }
    raise RuntimeError(f"No contract specification found for {symbol}")


def tick(symbol: str) -> dict[str, Any]:
    rows = _rows(f"tick_{_symbol_file_key(symbol)}.csv")
    if len(rows) >= 2:
        header, row = rows[0], rows[1]
        item = dict(zip(header, row))
        return {
            "symbol": symbol,
            "bid": _num(item.get("bid")),
            "ask": _num(item.get("ask")),
            "last": _num(item.get("last")),
            "time": _iso(item.get("time") or ""),
        }
    raise RuntimeError(f"no tick dump for {symbol}")


def rates(symbol: str, timeframe: str, count: int = 300) -> list[dict[str, Any]]:
    rows = _rows(f"rates_{_symbol_file_key(symbol)}_{timeframe.upper()}.csv")
    if len(rows) < 2:
        raise RuntimeError(f"no rates dump for {symbol} {timeframe}")
    header = rows[0]
    out = []
    for row in rows[1:][-count:]:
        item = dict(zip(header, row))
        out.append(
            {
                "time": _iso(item.get("time") or ""),
                "open": _num(item.get("open")),
                "high": _num(item.get("high")),
                "low": _num(item.get("low")),
                "close": _num(item.get("close")),
                "tick_volume": int(_num(item.get("tick_volume"))),
            }
        )
    return out
