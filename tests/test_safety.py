from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("order_send", "order_check", "ORDER_FILLING", "positions_close")


def test_bridge_has_no_trade_calls():
    text = (ROOT / "app" / "mt5_bridge.py").read_text(encoding="utf-8")
    for token in FORBIDDEN:
        assert token not in text


def test_dump_script_is_read_only_and_lists_all_terminal_symbols():
    text = (ROOT / "ea" / "ReadOnlyDesk.mq5").read_text(encoding="utf-8")
    assert "SymbolsTotal(false)" in text
    assert "ProcessMarketRequest" in text
    assert "market_request.txt" in text
    assert 'market_response_"+request_id+".txt' in text
    assert 'request_id+"|"' in text
    for token in ("OrderSend", "OrderCheck", "PositionClose"):
        assert token not in text


def test_private_app_rejects_non_loopback_bind_addresses():
    assert Settings(app_host="127.0.0.1").app_host == "127.0.0.1"
    with pytest.raises(ValidationError):
        Settings(app_host="0.0.0.0")


def test_ui_does_not_inject_dynamic_values_with_inner_html():
    text = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert ".innerHTML" not in text


def test_docs_keep_engine_generic():
    text = (ROOT / "docs" / "SCOPE.md").read_text(encoding="utf-8").lower()
    assert "analysis engine" in text or "engine api" in text
