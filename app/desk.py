from __future__ import annotations

from typing import Any

from app.analysis import align_frames, atr_like, snapshot
from app.briefing import engine_brief, engine_status
from app.config import settings
from app import file_bridge, journal, mt5_bridge
from app.mt5_bridge import TIMEFRAME_MAP
from app.risk import exposure, normalize_lots, size_hint
from app.universe import classify, pick_watchlist, search_symbols


_ready = False
_api = mt5_bridge


def engine_configured() -> bool:
    return engine_status()["configured"]


def connect() -> None:
    global _ready, _api
    if _ready and _api is mt5_bridge and mt5_bridge.connected():
        return
    if _ready and _api is file_bridge and file_bridge.available():
        return

    errors: list[str] = []
    try:
        mt5_bridge.initialize()
        mt5_bridge.account()
        _api = mt5_bridge
        _ready = True
        return
    except Exception as exc:
        errors.append(str(exc))

    if file_bridge.available():
        try:
            file_bridge.account()
            _api = file_bridge
            _ready = True
            return
        except Exception as exc:
            errors.append(str(exc))

    _ready = False
    detail = " | ".join(errors)
    raise RuntimeError(
        "Could not read a logged-in MetaTrader 5 terminal. Open and log in to MT5, then refresh the desk. "
        + (f"({detail})" if detail else "")
    )


def status() -> dict[str, Any]:
    engine = engine_status()
    try:
        connect()
        acc = _api.account()
        pos = _api.positions()
        return {
            "connected": True,
            "read_only": True,
            "sends_orders": False,
            "engine_configured": engine["configured"],
            "engine_status": engine["status"],
            "engine_protocol": engine["protocol"],
            "engine_message_fa": engine["message_fa"],
            "account": acc,
            "positions": pos,
            "exposure": exposure(acc, pos),
            "error": None,
        }
    except Exception as exc:
        return {
            "connected": False,
            "read_only": True,
            "sends_orders": False,
            "engine_configured": engine["configured"],
            "engine_status": engine["status"],
            "engine_protocol": engine["protocol"],
            "engine_message_fa": engine["message_fa"],
            "account": None,
            "positions": [],
            "exposure": {},
            "error": str(exc),
        }


def build_market(
    symbol: str,
    timeframes: list[str] | None = None,
    refresh_file_data: bool = True,
    include_analysis_candles: bool = False,
) -> dict[str, Any]:
    connect()
    symbol = symbol.strip()
    if not symbol:
        raise ValueError("A symbol is required")
    tfs = [tf.strip().upper() for tf in (timeframes or settings.timeframes())]
    if not tfs:
        raise ValueError("At least one timeframe is required")
    tfs = list(dict.fromkeys(tfs))
    unsupported = [tf for tf in tfs if tf not in TIMEFRAME_MAP]
    if unsupported:
        raise ValueError(f"Unsupported timeframe: {unsupported[0]}")
    spec = _api.symbol_spec(symbol)
    symbol = str(spec.get("name") or symbol)
    if _api is file_bridge and refresh_file_data:
        file_bridge.request_market([{"symbol": symbol, "timeframes": tfs}])
    candles = {tf: _api.rates(symbol, tf) for tf in tfs}
    frames = [snapshot(candles[tf], tf) for tf in tfs]
    sample = candles.get("H1") or next(iter(candles.values()))
    atr = atr_like(sample)
    tick_size = float(spec.get("trade_tick_size") or spec.get("point") or 0)
    tick_value = float(spec.get("trade_tick_value") or 0)
    stop_ticks = atr / tick_size if tick_size else 0.0
    result = {
        "symbol": spec.get("name") or symbol.upper(),
        "spec": spec,
        "tick": _api.tick(symbol),
        "frames": frames,
        "alignment": align_frames(frames),
        "atr": atr,
        "stop_ticks": stop_ticks,
        "tick_value_per_lot": tick_value,
    }
    if include_analysis_candles:
        result["analysis_candles"] = {
            tf: [
                {key: candle[key] for key in ("time", "open", "high", "low", "close")}
                for candle in (candles[tf][:-1] if len(candles[tf]) > 1 else candles[tf])[-40:]
            ]
            for tf in tfs
        }
    return result


def build_briefing(
    symbol: str,
    stop_distance: float = 0,
    tick_value_per_lot: float = 0,
    timeframes: list[str] | None = None,
    entry_note: str = "",
) -> dict[str, Any]:
    connect()
    acc = _api.account()
    pos = _api.positions()
    market = build_market(symbol, timeframes, include_analysis_candles=True)
    stop = stop_distance if stop_distance > 0 else float(market["stop_ticks"] or 0)
    tick_val = tick_value_per_lot if tick_value_per_lot > 0 else float(market["tick_value_per_lot"] or 0)
    hint = size_hint(float(acc.get("equity") or 0), settings.risk_per_trade_pct, stop, tick_val)
    volume_min = float(market["spec"].get("volume_min") or 0)
    volume_step = float(market["spec"].get("volume_step") or 0)
    hint["volume_spec_missing"] = volume_min <= 0 or volume_step <= 0
    hint["suggested_lots"], hint["minimum_lot_exceeds_risk"] = normalize_lots(
        float(hint["suggested_lots"]),
        volume_min,
        volume_step,
        float(market["spec"].get("volume_max") or 0),
    )
    payload = {
        **market,
        "exposure": exposure(acc, pos),
        "positions": pos,
        "size_hint": hint,
        "entry_note": str(entry_note or "").strip(),
    }
    payload["briefing"] = engine_brief(payload)
    payload.pop("analysis_candles", None)
    return payload


def watchlist() -> dict[str, Any]:
    connect()
    symbols = _api.symbols()
    names = pick_watchlist(symbols, settings.watch_symbols())
    request_error = None
    if _api is file_bridge:
        try:
            file_bridge.request_market([{"symbol": name, "timeframes": ["H1", "H4"]} for name in names])
        except Exception as exc:
            request_error = str(exc)
    cards = []
    for name in names:
        spec = next((s for s in symbols if s["name"] == name), {})
        group = classify(name, spec.get("path", ""), spec.get("description", ""))
        try:
            if request_error:
                raise RuntimeError(request_error)
            view = build_market(name, ["H1", "H4"], refresh_file_data=False)
            cards.append(
                {
                    "symbol": view["symbol"],
                    "group": group,
                    "alignment": view["alignment"],
                    "tick": view["tick"],
                    "frames": view["frames"],
                    "error": None,
                }
            )
        except Exception as exc:
            cards.append(
                {
                    "symbol": name,
                    "group": group,
                    "alignment": None,
                    "tick": None,
                    "frames": [],
                    "error": str(exc),
                }
            )
    return {"symbols": names, "cards": cards, "catalog_count": len(symbols)}


def catalog(query: str = "") -> dict[str, Any]:
    connect()
    items = _api.symbols()
    found = search_symbols(items, query)
    for s in found:
        s["group"] = classify(s.get("name", ""), s.get("path", ""), s.get("description", ""))
    return {"count": len(items), "matches": found}


def deals() -> list[dict[str, Any]]:
    connect()
    return _api.deals()


def review(symbol: str) -> dict[str, Any]:
    connect()
    deals = _api.deals()
    brief = journal.last_for_symbol(symbol)
    return journal.compare(brief, deals, symbol)


def save_brief(payload: dict[str, Any]) -> dict[str, Any]:
    brief = payload.get("briefing") or {}
    return journal.append(
        {
            "symbol": payload.get("symbol"),
            "alignment": payload.get("alignment"),
            "market_fa": brief.get("market_fa"),
            "risk_fa": brief.get("risk_fa"),
            "watch_fa": brief.get("watch_fa"),
            "fit_fa": brief.get("fit_fa"),
            "source": brief.get("source"),
            "entry_note": payload.get("entry_note", ""),
        }
    )
