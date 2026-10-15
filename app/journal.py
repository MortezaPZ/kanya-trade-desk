from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1] / "data" / "runtime"
FILE = ROOT / "journal.jsonl"


def append(entry: dict[str, Any]) -> dict[str, Any]:
    ROOT.mkdir(parents=True, exist_ok=True)
    row = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        **entry,
    }
    with FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def recent(limit: int = 40) -> list[dict[str, Any]]:
    if not FILE.exists():
        return []
    lines = FILE.read_text(encoding="utf-8").splitlines()
    out: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(out))


def last_for_symbol(symbol: str) -> dict[str, Any] | None:
    target = symbol.upper()
    for row in recent(80):
        if str(row.get("symbol", "")).upper() == target:
            return row
    return None


def compare(brief: dict[str, Any] | None, deals: list[dict[str, Any]], symbol: str) -> dict[str, Any]:
    symbol_deals = [d for d in deals if str(d.get("symbol", "")).upper() == symbol.upper()]
    last_deal = symbol_deals[-1] if symbol_deals else None
    if not brief:
        return {
            "has_brief": False,
            "last_deal": last_deal,
            "entry_note": None,
            "note_fa": "برای این نماد هنوز مشاوره‌ای ذخیره نشده.",
        }
    from app.labels import fa_trend

    align = brief.get("alignment")
    note = "مشاورهٔ ذخیره‌شده با آخرین معامله کنار هم است. این مقایسه سفارش نیست."
    if last_deal and align in {"aligned_down", "aligned_up"}:
        note = (
            f"آخرین مشاوره هم‌راستایی «{fa_trend(align)}» بود. "
            f"آخرین معامله سود/زیان {last_deal.get('profit')} نشان می‌دهد."
        )
    return {
        "has_brief": True,
        "brief": brief,
        "last_deal": last_deal,
        "entry_note": brief.get("entry_note") or None,
        "note_fa": note,
    }
