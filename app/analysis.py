from __future__ import annotations

from typing import Any


def _ema(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be > 0")
    k = 2 / (period + 1)
    out: list[float | None] = []
    ema: float | None = None
    for i, v in enumerate(values):
        if i < period - 1:
            out.append(None)
            continue
        if ema is None:
            ema = sum(values[:period]) / period
        else:
            ema = v * k + ema * (1 - k)
        out.append(ema)
    return out


def _swing_points(highs: list[float], lows: list[float], left: int = 2, right: int = 2) -> tuple[list[int], list[int]]:
    sh: list[int] = []
    sl: list[int] = []
    n = len(highs)
    for i in range(left, n - right):
        h_win = highs[i - left : i + right + 1]
        l_win = lows[i - left : i + right + 1]
        if highs[i] == max(h_win):
            sh.append(i)
        if lows[i] == min(l_win):
            sl.append(i)
    return sh, sl


def structure_bias(highs: list[float], lows: list[float]) -> str:
    sh, sl = _swing_points(highs, lows)
    if len(sh) < 2 or len(sl) < 2:
        return "unclear"
    last_highs = [highs[i] for i in sh[-2:]]
    last_lows = [lows[i] for i in sl[-2:]]
    hh = last_highs[1] > last_highs[0]
    hl = last_lows[1] > last_lows[0]
    lh = last_highs[1] < last_highs[0]
    ll = last_lows[1] < last_lows[0]
    if hh and hl:
        return "up"
    if lh and ll:
        return "down"
    return "range"


def candle_patterns(candles: list[dict[str, Any]]) -> list[str]:
    if len(candles) < 2:
        return []
    a, b = candles[-2], candles[-1]
    body_b = abs(b["close"] - b["open"])
    wick_up = b["high"] - max(b["open"], b["close"])
    wick_dn = min(b["open"], b["close"]) - b["low"]
    rng = max(b["high"] - b["low"], 1e-12)
    found: list[str] = []
    if body_b / rng < 0.12:
        found.append("doji")
    if wick_dn > body_b * 2 and wick_up < body_b:
        found.append("pin_bull")
    if wick_up > body_b * 2 and wick_dn < body_b:
        found.append("pin_bear")
    bull_eng = (
        a["close"] < a["open"]
        and b["close"] > b["open"]
        and b["close"] >= a["open"]
        and b["open"] <= a["close"]
    )
    bear_eng = (
        a["close"] > a["open"]
        and b["close"] < b["open"]
        and b["close"] <= a["open"]
        and b["open"] >= a["close"]
    )
    if bull_eng:
        found.append("engulf_bull")
    if bear_eng:
        found.append("engulf_bear")
    return found


def snapshot(candles: list[dict[str, Any]], timeframe: str) -> dict[str, Any]:
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    ema200 = _ema(closes, 200)
    last = candles[-1]
    e20, e50, e200 = ema20[-1], ema50[-1], ema200[-1]
    trend = "unclear"
    if e20 and e50:
        if last["close"] > e20 > e50:
            trend = "up"
        elif last["close"] < e20 < e50:
            trend = "down"
        else:
            trend = "mixed"
    return {
        "timeframe": timeframe,
        "close": last["close"],
        "ema20": e20,
        "ema50": e50,
        "ema200": e200,
        "trend": trend,
        "structure": structure_bias(highs, lows),
        "patterns": candle_patterns(candles),
    }


def align_frames(frames: list[dict[str, Any]]) -> str:
    biases = [f["trend"] for f in frames]
    if biases and all(b == "up" for b in biases):
        return "aligned_up"
    if biases and all(b == "down" for b in biases):
        return "aligned_down"
    return "conflict"
