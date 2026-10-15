from app.universe import classify, pick_watchlist, search_symbols


def test_classify_metals_before_usd():
    assert classify("XAUUSD") == "metals"
    assert classify("BTCUSD") == "crypto"
    assert classify("EURUSD") == "fx"


def test_pick_prefers_requested_then_fills_groups():
    symbols = [
        {"name": "EURUSD", "path": "Forex", "description": "Euro"},
        {"name": "XAUUSD", "path": "Metals", "description": "Gold"},
        {"name": "BTCUSD", "path": "Crypto", "description": "Bitcoin"},
        {"name": "XTIUSD", "path": "Energy", "description": "Oil"},
    ]
    out = pick_watchlist(symbols, ["XAUUSD"], limit=4)
    assert out[0] == "XAUUSD"
    assert "BTCUSD" in out


def test_search():
    symbols = [{"name": "XAUUSD", "description": "Gold"}, {"name": "EURUSD", "description": "Euro"}]
    hits = search_symbols(symbols, "gold")
    assert hits[0]["name"] == "XAUUSD"
