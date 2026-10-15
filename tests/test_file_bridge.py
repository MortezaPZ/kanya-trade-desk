from pathlib import Path

import pytest

from app import file_bridge


def _use_desk(monkeypatch, tmp_path: Path) -> Path:
    (tmp_path / "account.csv").write_text("login,1\n", encoding="ascii")
    monkeypatch.setattr(file_bridge, "_CANDIDATES", [tmp_path])
    return tmp_path


def test_request_market_waits_for_matching_terminal_response(monkeypatch, tmp_path):
    desk = _use_desk(monkeypatch, tmp_path)

    def terminal_poll(_delay):
        request = (desk / "market_request.txt").read_text(encoding="ascii").splitlines()
        assert request[1:] == ["NAS100.cash|H1,H4", "BTCUSD|M15"]
        response = desk / f"market_response_{request[0]}.txt"
        response.write_text(f"{request[0]}|done\n", encoding="ascii")

    monkeypatch.setattr(file_bridge.time, "sleep", terminal_poll)
    file_bridge.request_market(
        [
            {"symbol": "NAS100.cash", "timeframes": ["H1", "H4", "H1"]},
            {"symbol": "BTCUSD", "timeframes": ["M15"]},
        ],
        timeout_seconds=1,
    )


def test_request_market_rejects_framing_delimiter_in_symbol(monkeypatch, tmp_path):
    _use_desk(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="Unsupported symbol"):
        file_bridge.request_market([{"symbol": "bad|symbol", "timeframes": ["H1"]}])


def test_market_data_stale_checks_every_requested_file(monkeypatch, tmp_path):
    desk = _use_desk(monkeypatch, tmp_path)
    for name in ("tick_NAS100.cash.csv", "rates_NAS100.cash_H1.csv", "rates_NAS100.cash_H4.csv"):
        (desk / name).write_text("ready", encoding="ascii")
    assert file_bridge.market_data_stale("NAS100.cash", ["H1", "H4"]) is False
    (desk / "rates_NAS100.cash_H4.csv").unlink()
    assert file_bridge.market_data_stale("NAS100.cash", ["H1", "H4"]) is True


def test_symbol_spec_does_not_invent_contract_defaults(monkeypatch, tmp_path):
    desk = _use_desk(monkeypatch, tmp_path)
    (desk / "symbols.csv").write_text(
        "name,path,description,digits,point,trade_contract_size,tick_size,tick_value,volume_min,volume_step,volume_max\n"
        "XAUUSD,Metals,Gold,2,0.01,100,0.01,1,0.01,0.01,100\n",
        encoding="ascii",
    )
    assert file_bridge.symbol_spec("XAUUSD")["volume_max"] == 100
    with pytest.raises(RuntimeError, match="No contract specification"):
        file_bridge.symbol_spec("UNKNOWN")


def test_symbol_catalog_includes_symbols_not_yet_visible(monkeypatch, tmp_path):
    desk = _use_desk(monkeypatch, tmp_path)
    (desk / "symbols.csv").write_text(
        "name,path,description,digits,point,trade_contract_size,tick_size,tick_value,volume_min,volume_step,volume_max,visible\n"
        "NAS100.cash,Indices,Nasdaq,1,0.1,1,0.1,1,0.1,0.1,100,0\n",
        encoding="ascii",
    )
    assert [row["name"] for row in file_bridge.symbols()] == ["NAS100.cash"]
