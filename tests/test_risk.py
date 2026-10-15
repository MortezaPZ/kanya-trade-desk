from app.risk import normalize_lots, size_hint


def test_size_hint_is_advisory():
    hint = size_hint(1_000, 1, 100, 1)
    assert hint["suggested_lots"] == 0.1
    assert hint["sends_order"] is False


def test_normalize_lots_rounds_down_to_protect_risk():
    assert normalize_lots(0.029, 0.01, 0.01) == (0.02, False)


def test_normalize_lots_returns_zero_when_minimum_exceeds_risk():
    assert normalize_lots(0.009, 0.01, 0.01) == (0.0, True)


def test_normalize_lots_applies_broker_maximum():
    assert normalize_lots(2.0, 0.01, 0.01, 0.25) == (0.25, False)
