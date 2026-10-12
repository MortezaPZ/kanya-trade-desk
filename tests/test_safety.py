from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("order_send", "order_check", "ORDER_FILLING", "positions_close")


def test_bridge_has_no_trade_calls():
    text = (ROOT / "app" / "mt5_bridge.py").read_text(encoding="utf-8")
    for token in FORBIDDEN:
        assert token not in text


def test_docs_keep_engine_generic():
    text = (ROOT / "docs" / "SCOPE.md").read_text(encoding="utf-8").lower()
    assert "analysis engine" in text or "engine api" in text
