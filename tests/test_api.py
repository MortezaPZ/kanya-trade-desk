from fastapi.testclient import TestClient

from app.main import app


def test_briefing_passes_timeframes_and_entry_note(monkeypatch):
    captured = {}

    def build_briefing(symbol, stop_distance, tick_value_per_lot, timeframes, entry_note):
        captured["args"] = (symbol, stop_distance, tick_value_per_lot, timeframes, entry_note)
        return {"symbol": symbol, "briefing": {"source": "local_rules"}}

    monkeypatch.setattr("app.main.desk.build_briefing", build_briefing)
    client = TestClient(app)
    response = client.post(
        "/api/briefing",
        json={
            "symbol": "XAUUSD",
            "timeframes": ["H1", "H4"],
            "stop_distance": 25,
            "tick_value_per_lot": 2,
            "entry_note": "مقاومت شکسته شد",
            "save": False,
        },
    )
    assert response.status_code == 200
    assert captured["args"] == ("XAUUSD", 25, 2, ["H1", "H4"], "مقاومت شکسته شد")


def test_briefing_limits_local_entry_note_length():
    client = TestClient(app)
    response = client.post("/api/briefing", json={"symbol": "XAUUSD", "entry_note": "x" * 501})
    assert response.status_code == 422
