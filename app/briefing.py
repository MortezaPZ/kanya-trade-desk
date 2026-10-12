from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings


SYSTEM = """You are a cautious market briefing writer for a discretionary trader.
You never place orders. You never promise profit.
Reply with JSON only, keys:
market_fa, risk_fa, watch_fa, fit_fa, english_summary
Use clear Persian in *_fa fields. Be specific to the numbers given.
If timeframes conflict, say so. If data is thin, say unclear.
"""


def local_brief(payload: dict[str, Any]) -> dict[str, Any]:
    frames = payload.get("frames") or []
    align = payload.get("alignment")
    patterns = []
    for f in frames:
        for p in f.get("patterns") or []:
            patterns.append(f"{f.get('timeframe')}:{p}")
    pos = payload.get("exposure") or {}
    symbol = payload.get("symbol")
    market = (
        f"نماد `{symbol}` — هم‌راستایی تایم‌فریم‌ها: `{align}`. "
        f"روندها: " + "، ".join(f"{f.get('timeframe')}={f.get('trend')}/{f.get('structure')}" for f in frames)
    )
    risk = (
        f"اکوئیتی {pos.get('equity')}، معاملات باز {pos.get('open_count')}، "
        f"سود شناور {pos.get('floating_pnl')}."
    )
    watch = "الگوهای اخیر: " + ("، ".join(patterns) if patterns else "الگوی برجسته‌ای نیست")
    fit = "ورود فقط اگر حد ضرر مشخص باشد و با درصد ریسک تنظیم‌شده جور دربیاید. این متن سفارش نیست."
    return {
        "market_fa": market,
        "risk_fa": risk,
        "watch_fa": watch,
        "fit_fa": fit,
        "english_summary": f"{symbol} alignment={align}",
        "source": "local_rules",
    }


def engine_brief(payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.llm_api_key or not settings.llm_base_url or not settings.llm_model:
        brief = local_brief(payload)
        brief["source"] = "local_rules_no_engine"
        return brief
    body = {
        "model": settings.llm_model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    }
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
        res = client.post(url, json=body, headers=headers)
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = local_brief(payload)
        parsed["engine_raw"] = content
        parsed["source"] = "engine_unparsed_fallback"
        return parsed
    parsed["source"] = "engine"
    return parsed
