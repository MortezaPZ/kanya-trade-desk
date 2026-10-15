from app.analysis import atr_like
import json

from app import briefing
from app.briefing import engine_market_payload, local_brief


def test_local_brief_persian_and_no_order():
    payload = {
        "symbol": "XAUUSD",
        "alignment": "aligned_up",
        "tick": {"bid": 2400, "ask": 2400.3},
        "frames": [
            {"timeframe": "H1", "trend": "up", "structure": "up", "close": 2400, "patterns": ["pin_bull"]},
            {"timeframe": "H4", "trend": "up", "structure": "up", "close": 2390, "patterns": []},
        ],
        "exposure": {"balance": 1000, "equity": 1000, "floating_pnl": 0, "open_count": 0, "used_margin_pct": 0},
        "size_hint": {"stop_distance": 20, "risk_pct": 1, "suggested_lots": 0.1},
    }
    brief = local_brief(payload)
    assert "صعودی" in brief["market_fa"]
    assert "ارسال سفارش" in brief["risk_fa"]
    assert brief["source"] == "local_rules"


def test_atr_positive():
    candles = [
        {"open": 10, "high": 12, "low": 9, "close": 11},
        {"open": 11, "high": 13, "low": 10, "close": 12},
        {"open": 12, "high": 14, "low": 11, "close": 13},
    ]
    assert atr_like(candles) > 0


def test_engine_market_payload_excludes_account_and_trade_details():
    payload = {
        "symbol": "XAUUSD",
        "tick": {"bid": 2400, "ask": 2400.3},
        "frames": [],
        "alignment": "aligned_up",
        "atr": 3.5,
        "exposure": {"equity": 1000},
        "positions": [{"ticket": 123}],
        "size_hint": {"suggested_lots": 0.1},
        "entry_note": "private note",
    }
    assert engine_market_payload(payload) == {
        "symbol": "XAUUSD",
        "tick": payload["tick"],
        "frames": [],
        "alignment": "aligned_up",
        "atr": 3.5,
    }


def test_engine_brief_sends_market_only_and_keeps_risk_local(monkeypatch):
    payload = {
        "symbol": "XAUUSD",
        "alignment": "aligned_up",
        "tick": {"bid": 2400, "ask": 2400.3},
        "frames": [],
        "atr": 3.5,
        "exposure": {"balance": 1000, "equity": 900, "open_count": 2, "used_margin_pct": 10},
        "positions": [{"ticket": 123, "symbol": "XAUUSD"}],
        "size_hint": {"stop_distance": 20, "risk_pct": 1, "suggested_lots": 0.1},
        "entry_note": "private note",
    }
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": json.dumps({
                "market_fa": "تحلیل بازار",
                "watch_fa": "مراقب باشید",
                "risk_fa": "متن ساختگی ریسک",
                "fit_fa": "متن ساختگی تناسب",
                "english_summary": "summary",
            })}}]}

    class Client:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, _url, json, headers):
            captured["body"] = json
            captured["headers"] = headers
            return Response()

    monkeypatch.setattr(briefing.settings, "llm_api_key", "test-key")
    monkeypatch.setattr(briefing.settings, "llm_base_url", "https://engine.example/v1")
    monkeypatch.setattr(briefing.settings, "llm_model", "test-model")
    monkeypatch.setattr(briefing.httpx, "Client", Client)

    result = briefing.engine_brief(payload)
    sent = json.loads(captured["body"]["messages"][1]["content"])
    assert set(sent) == {"symbol", "tick", "frames", "alignment", "atr"}
    assert "positions" not in sent and "exposure" not in sent and "entry_note" not in sent
    assert result["risk_fa"] == local_brief(payload)["risk_fa"]
    assert result["fit_fa"] == local_brief(payload)["fit_fa"]
    assert result["source"] == "engine"
