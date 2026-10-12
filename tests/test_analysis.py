from app.analysis import align_frames, candle_patterns, snapshot, structure_bias
from app.risk import size_hint


def _candle(o, h, l, c):
    return {"open": o, "high": h, "low": l, "close": c, "tick_volume": 1, "time": "t"}


def test_up_structure():
    highs = [1, 2, 1.5, 3, 2.5, 4, 3.5]
    lows = [0.5, 1.2, 1.0, 2.0, 1.8, 3.0, 2.8]
    assert structure_bias(highs, lows) in {"up", "range", "unclear"}


def test_bull_engulf():
    candles = [_candle(10, 10.2, 9, 9.2), _candle(9.1, 11, 9.0, 10.5)]
    assert "engulf_bull" in candle_patterns(candles)


def test_snapshot_keys():
    candles = [_candle(i, i + 1, i - 1, i + 0.2) for i in range(40, 80)]
    snap = snapshot(candles, "H1")
    assert snap["timeframe"] == "H1"
    assert "trend" in snap


def test_align():
    assert align_frames([{"trend": "up"}, {"trend": "up"}]) == "aligned_up"
    assert align_frames([{"trend": "up"}, {"trend": "down"}]) == "conflict"


def test_size_hint_advisory():
    hint = size_hint(10_000, 1, 10, 1)
    assert hint["sends_order"] is False
    assert hint["suggested_lots"] == 10.0
