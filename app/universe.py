from __future__ import annotations

from typing import Any

GROUPS: dict[str, tuple[str, ...]] = {
    "metals": ("XAU", "GOLD", "XAG", "SILVER"),
    "energy": ("XTI", "XBR", "WTI", "BRENT", "OIL", "USOIL", "UKOIL", "NGAS"),
    "index": ("US30", "US500", "NAS", "USTEC", "GER40", "GER30", "UK100", "JPN225", "DJ30", "SPX"),
    "crypto": ("BTC", "ETH", "SOL", "XRP", "BNB", "ADA", "DOGE"),
    "fx": ("EUR", "GBP", "USD", "JPY", "AUD", "NZD", "CAD", "CHF"),
}


def classify(name: str, path: str = "", description: str = "") -> str:
    blob = f"{name} {path} {description}".upper()
    for group, keys in GROUPS.items():
        if any(k in blob for k in keys):
            return group
    return "other"


def pick_watchlist(symbols: list[dict[str, Any]], preferred: list[str], limit: int = 12) -> list[str]:
    names = [s["name"] for s in symbols]
    upper = {n.upper(): n for n in names}
    chosen: list[str] = []
    for item in preferred:
        hit = upper.get(item.upper())
        if hit and hit not in chosen:
            chosen.append(hit)
    by_group: dict[str, list[str]] = {k: [] for k in GROUPS}
    for s in symbols:
        g = classify(s.get("name", ""), s.get("path", ""), s.get("description", ""))
        if g in by_group:
            by_group[g].append(s["name"])
    for group in ("metals", "energy", "index", "crypto", "fx"):
        for name in by_group[group]:
            if name not in chosen:
                chosen.append(name)
            if len(chosen) >= limit:
                return chosen
    return chosen[:limit]


def search_symbols(symbols: list[dict[str, Any]], query: str, limit: int = 30) -> list[dict[str, Any]]:
    q = query.strip().upper()
    if not q:
        return symbols[:limit]
    scored = []
    for s in symbols:
        name = s.get("name", "").upper()
        desc = (s.get("description") or "").upper()
        if q in name:
            scored.append((0, s))
        elif q in desc:
            scored.append((1, s))
    scored.sort(key=lambda x: (x[0], x[1].get("name", "")))
    return [s for _, s in scored[:limit]]
