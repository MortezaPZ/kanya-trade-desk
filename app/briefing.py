from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings
from app.labels import fa_pattern, fa_trend


SYSTEM = """You are a cautious market briefing writer for a discretionary trader.
You never place orders. You never promise profit.
Reply with JSON only, keys:
market_fa, risk_fa, watch_fa, fit_fa, english_summary
Use clear Persian in *_fa fields. Be specific to the numbers given.
If timeframes conflict, say so. If data is thin, say unclear.
The input contains market data only. Do not infer account details or position size.
"""


def _frame_line(frame: dict[str, Any]) -> str:
    pats = "، ".join(fa_pattern(p) for p in (frame.get("patterns") or [])) or "بدون الگوی برجسته"
    close = frame.get("close")
    return (
        f"{frame.get('timeframe')}: روند {fa_trend(frame.get('trend'))}، "
        f"ساختار {fa_trend(frame.get('structure'))}، قیمت {close}، {pats}"
    )


def local_brief(payload: dict[str, Any]) -> dict[str, Any]:
    frames = payload.get("frames") or []
    align = payload.get("alignment")
    symbol = payload.get("symbol")
    tick = payload.get("tick") or {}
    pos = payload.get("exposure") or {}
    hint = payload.get("size_hint") or {}
    higher = frames[-1] if frames else {}
    lower = frames[0] if frames else {}

    market = (
        f"نماد {symbol} الان bid {tick.get('bid')} و ask {tick.get('ask')} است. "
        f"تصویر چندتایم‌فریم: {fa_trend(align)}. "
        + " | ".join(_frame_line(f) for f in frames)
    )

    open_count = pos.get("open_count") or 0
    margin_pct = pos.get("used_margin_pct") or 0
    risk = (
        f"موجودی {pos.get('balance')}، اکوئیتی {pos.get('equity')}، "
        f"سود شناور {pos.get('floating_pnl')}، معاملات باز {open_count}، "
        f"حاشیهٔ استفاده‌شده حدود {margin_pct} درصد. "
        f"اگر حد ضرر حدود {hint.get('stop_distance')} باشد، "
        f"برای ریسک {hint.get('risk_pct')} درصد حدود {hint.get('suggested_lots')} لات پیشنهاد می‌شود — فقط راهنما، بدون ارسال سفارش."
    )

    watch_bits = []
    if align == "conflict":
        watch_bits.append("تایم‌فریم‌ها یکی نیستند؛ ورود عجولانه پرریسک است.")
    if higher.get("trend") and lower.get("trend") and higher.get("trend") != lower.get("trend"):
        watch_bits.append(
            f"تایم بالاتر {fa_trend(higher.get('trend'))} است و تایم پایین‌تر {fa_trend(lower.get('trend'))}."
        )
    pats = []
    for f in frames:
        for p in f.get("patterns") or []:
            pats.append(f"{f.get('timeframe')} {fa_pattern(p)}")
    if pats:
        watch_bits.append("الگوهای اخیر: " + "، ".join(pats))
    else:
        watch_bits.append("الگوی کندلی برجسته‌ای روی آخرین کندل‌ها نیست.")
    watch = " ".join(watch_bits)

    if align == "aligned_up":
        fit = "اگر خرید می‌بینید، فقط وقتی با حد ضرر و حجم حساب جور باشد. فروش خلاف این تصویر است."
    elif align == "aligned_down":
        fit = "اگر فروش می‌بینید، فقط وقتی با حد ضرر و حجم حساب جور باشد. خرید خلاف این تصویر است."
    else:
        fit = "الان تصویر یکدست نیست. بهتر است صبر کنید یا حجم را خیلی کوچک نگه دارید. این متن جای شما تصمیم نمی‌گیرد."

    return {
        "market_fa": market,
        "risk_fa": risk,
        "watch_fa": watch,
        "fit_fa": fit,
        "english_summary": f"{symbol} alignment={align}",
        "source": "local_rules",
    }


def engine_market_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep account, positions, user notes, and size calculations on this machine."""
    return {
        "symbol": payload.get("symbol"),
        "tick": payload.get("tick") or {},
        "frames": payload.get("frames") or [],
        "alignment": payload.get("alignment"),
        "atr": payload.get("atr"),
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
            {"role": "user", "content": json.dumps(engine_market_payload(payload), ensure_ascii=False)},
        ],
    }
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            res = client.post(url, json=body, headers=headers)
            res.raise_for_status()
            content = res.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        brief = local_brief(payload)
        brief["source"] = "local_rules_engine_unavailable"
        return brief
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        parsed = local_brief(payload)
        parsed["source"] = "engine_unparsed_fallback"
        return parsed
    if not isinstance(parsed, dict):
        parsed = local_brief(payload)
        parsed["source"] = "engine_unparsed_fallback"
        return parsed
    local = local_brief(payload)
    result = {
        key: parsed.get(key) if isinstance(parsed.get(key), str) else local[key]
        for key in ("market_fa", "watch_fa", "english_summary")
    }
    result["risk_fa"] = local["risk_fa"]
    result["fit_fa"] = local["fit_fa"]
    result["source"] = "engine"
    return result
