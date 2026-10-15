from app.journal import compare


def test_compare_without_brief():
    out = compare(None, [], "XAUUSD")
    assert out["has_brief"] is False
    assert "مشاوره" in out["note_fa"]


def test_compare_with_deal():
    brief = {"alignment": "aligned_up", "entry_note": "شکست مقاومت در H1"}
    deals = [{"symbol": "XAUUSD", "profit": 12.5, "volume": 0.1, "price": 2400}]
    out = compare(brief, deals, "XAUUSD")
    assert out["has_brief"] is True
    assert out["last_deal"]["profit"] == 12.5
    assert out["entry_note"] == "شکست مقاومت در H1"
