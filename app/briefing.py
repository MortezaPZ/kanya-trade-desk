from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.config import settings
from app.labels import fa_pattern, fa_trend


SYSTEM = """You are the market-analysis component of a cautious assistant for a discretionary trader.
You analyze only the supplied quote, completed OHLC candles, and calculated technical summaries.
Never place, modify, or close orders. Never promise profit or present a forecast as certainty.
Do not invent news, fundamentals, support/resistance levels, or prices that are not derivable from the supplied data.
Treat the forming candle separately: the supplied candle arrays contain completed candles only; the quote may be newer.
If timeframes conflict or data is insufficient, state that plainly and reduce the strength of the conclusion.
Return one valid JSON object only, with string fields:
market_fa, scenario_fa, watch_fa, english_summary
Write concise, clear Persian in *_fa fields. market_fa summarizes multi-timeframe direction and evidence.
scenario_fa gives conditional bullish and bearish possibilities, their observable confirmation/invalidation conditions,
and says when waiting is more reasonable. Do not issue a bare buy/sell signal or precise entry/stop prices.
watch_fa lists the next chart facts to monitor and important uncertainty. The input contains no account data,
positions, trader notes, or size calculations; do not assume any of them.
"""

_PROTOCOLS = {
    "chat_completions": {"name": "Chat Completions", "path": "/chat/completions"},
    "messages_v1": {"name": "Messages API", "path": "/messages"},
}


def engine_status() -> dict[str, Any]:
    protocol = str(settings.llm_protocol or "").strip().lower()
    result: dict[str, Any] = {
        "configured": False,
        "status": "needs_setup",
        "protocol": None,
        "message_fa": "نوع API، نشانی، کلید و شناسهٔ مدل را در فایل محلی .env تنظیم کنید.",
    }
    if not protocol:
        result["message_fa"] = "نوع API انتخاب نشده؛ تحلیل هوشمند هنوز فعال نیست."
        return result
    if protocol not in _PROTOCOLS:
        result["status"] = "invalid_config"
        result["message_fa"] = "مقدار LLM_PROTOCOL باید chat_completions یا messages_v1 باشد."
        return result

    result["protocol"] = _PROTOCOLS[protocol]["name"]
    missing = []
    if not str(settings.llm_api_key or "").strip():
        missing.append("کلید API")
    if not str(settings.llm_model or "").strip():
        missing.append("شناسهٔ مدل")
    if not str(settings.llm_base_url or "").strip():
        missing.append("نشانی API")
    if not str(settings.llm_auth_header or "").strip():
        missing.append("نام هدر احراز هویت")
    auth_header = str(settings.llm_auth_header or "").strip()
    if auth_header and not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", auth_header):
        result["status"] = "invalid_config"
        result["message_fa"] = "نام هدر احراز هویت معتبر نیست."
        return result
    if any(char in str(settings.llm_auth_prefix or "") for char in "\r\n"):
        result["status"] = "invalid_config"
        result["message_fa"] = "پیشوند کلید API معتبر نیست."
        return result
    version_header = str(settings.llm_version_header or "").strip()
    if version_header and not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", version_header):
        result["status"] = "invalid_config"
        result["message_fa"] = "نام هدر نسخهٔ API معتبر نیست."
        return result
    if protocol == "messages_v1" and (
        not version_header
        or not str(settings.llm_api_version or "").strip()
    ):
        missing.append("نام هدر و نسخهٔ API")
    if version_header and any(char in str(settings.llm_api_version or "") for char in "\r\n"):
        result["status"] = "invalid_config"
        result["message_fa"] = "مقدار نسخهٔ API معتبر نیست."
        return result
    try:
        timeout_seconds = int(settings.llm_timeout_seconds)
    except (TypeError, ValueError):
        timeout_seconds = 0
    if not 1 <= timeout_seconds <= 180:
        result["status"] = "invalid_config"
        result["message_fa"] = "مهلت API باید بین ۱ تا ۱۸۰ ثانیه باشد."
        return result
    try:
        output_tokens = int(settings.llm_max_output_tokens)
    except (TypeError, ValueError):
        output_tokens = 0
    if not 256 <= output_tokens <= 3000:
        result["status"] = "invalid_config"
        result["message_fa"] = "حداکثر توکن پاسخ باید بین ۲۵۶ تا ۳۰۰۰ باشد."
        return result
    if missing:
        result["message_fa"] = "برای فعال‌شدن تحلیل هوشمند، " + " و ".join(missing) + " لازم است."
        return result

    base_url = str(settings.llm_base_url or "").strip()
    try:
        parsed = urlsplit(base_url)
        _ = parsed.port
    except ValueError:
        parsed = None
    if parsed is None:
        result["status"] = "invalid_config"
        result["message_fa"] = "آدرس API معتبر نیست."
        return result
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        parsed.scheme != "https" and not local_http
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        result["status"] = "invalid_config"
        result["message_fa"] = "آدرس API باید HTTPS معتبر باشد؛ فقط سرویس محلی می‌تواند HTTP داشته باشد."
        return result

    result.update({
        "configured": True,
        "status": "ready_to_call",
        "message_fa": "تنظیمات API ثبت شده است؛ اتصال هنگام درخواست تحلیل بررسی می‌شود.",
    })
    return result


def _endpoint(protocol: str) -> str:
    base_url = str(settings.llm_base_url or "").strip().rstrip("/")
    path = _PROTOCOLS[protocol]["path"]
    if base_url.lower().endswith(path):
        return base_url
    suffix = path if base_url.lower().endswith("/v1") else "/v1" + path
    return base_url + suffix


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
    """Only the minimum market chart data needed for analysis leaves this machine."""
    return {
        "symbol": payload.get("symbol"),
        "tick": payload.get("tick") or {},
        "frames": payload.get("frames") or [],
        "completed_candles": payload.get("analysis_candles") or {},
        "alignment": payload.get("alignment"),
        "atr": payload.get("atr"),
    }


def _request(protocol: str, market: dict[str, Any]) -> str:
    content = json.dumps(market, ensure_ascii=False, allow_nan=False)
    protocol = str(protocol).strip().lower()
    api_key = settings.llm_api_key.strip()
    auth_header = settings.llm_auth_header.strip()
    if not auth_header or any(char in auth_header for char in "\r\n:"):
        raise ValueError("invalid authentication header name")
    auth_value = f"{settings.llm_auth_prefix.strip()} {api_key}".strip()
    if any(char in auth_value for char in "\r\n"):
        raise ValueError("invalid authentication header value")
    headers = {auth_header: auth_value, "Content-Type": "application/json"}
    if settings.llm_version_header.strip():
        version_header = settings.llm_version_header.strip()
        version_value = settings.llm_api_version.strip()
        if not version_value or any(char in version_header for char in "\r\n:") or any(char in version_value for char in "\r\n"):
            raise ValueError("invalid API version header")
        headers[version_header] = version_value

    if protocol == "chat_completions":
        body = {
            "model": settings.llm_model.strip(),
            "temperature": 0.2,
            "max_completion_tokens": min(3000, max(256, int(settings.llm_max_output_tokens))),
            "response_format": {"type": "json_object"},
            "store": False,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": content},
            ],
        }
    else:
        body = {
            "model": settings.llm_model.strip(),
            "max_tokens": min(3000, max(256, int(settings.llm_max_output_tokens))),
            "temperature": 0.2,
            "system": SYSTEM,
            "messages": [{"role": "user", "content": content}],
        }

    with httpx.Client(timeout=settings.llm_timeout_seconds, follow_redirects=False) as client:
        response = client.post(_endpoint(protocol), json=body, headers=headers)
        response.raise_for_status()
        data = response.json()

    if protocol == "chat_completions":
        content = data["choices"][0]["message"]["content"]
    else:
        blocks = data["content"]
        content = "\n".join(block["text"] for block in blocks if block.get("type") == "text")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("empty model response")
    return content.strip()


def _unavailable_brief(payload: dict[str, Any], source: str, message_fa: str) -> dict[str, Any]:
    brief = local_brief(payload)
    brief.update({
        "market_fa": "تحلیل هوشمند انجام نشد؛ " + message_fa,
        "scenario_fa": "تا زمان برقراری API، سناریوی معاملاتی تولید نشده است.",
        "watch_fa": "اطلاعات خام نمودار و شاخص‌های محلی در صفحه موجود است؛ این متن جای تحلیل AI نیست.",
        "engine_message_fa": message_fa,
        "protocol": engine_status()["protocol"],
        "source": source,
    })
    return brief


def _parse_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:].lstrip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("model response is not an object")
    return parsed


def engine_brief(payload: dict[str, Any]) -> dict[str, Any]:
    status = engine_status()
    if not status["configured"]:
        return _unavailable_brief(payload, "engine_not_configured", status["message_fa"])

    protocol = str(settings.llm_protocol).strip().lower()
    try:
        parsed = _parse_json(_request(protocol, engine_market_payload(payload)))
    except httpx.TimeoutException:
        return _unavailable_brief(payload, "engine_timeout", "مهلت پاسخ API تمام شد.")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            message = "کلید API نامعتبر است یا دسترسی این مدل فعال نیست."
        elif exc.response.status_code == 429:
            message = "سقف مصرف یا محدودیت درخواست API رسیده است."
        elif exc.response.status_code >= 500:
            message = "سرویس API موقتاً پاسخ‌گو نیست."
        else:
            message = "درخواست API پذیرفته نشد؛ مدل و تنظیمات را بررسی کنید."
        return _unavailable_brief(payload, "engine_request_failed", message)
    except httpx.RequestError:
        return _unavailable_brief(payload, "engine_unreachable", "به سرویس API وصل نشد.")
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        return _unavailable_brief(payload, "engine_invalid_response", "پاسخ API قابل‌استفاده نبود.")

    local = local_brief(payload)
    result = {
        key: parsed.get(key, "")[:1600] if isinstance(parsed.get(key), str) else ""
        for key in ("market_fa", "scenario_fa", "watch_fa", "english_summary")
    }
    if not result["market_fa"] or not result["scenario_fa"] or not result["watch_fa"]:
        return _unavailable_brief(payload, "engine_invalid_response", "پاسخ API ناقص بود.")
    result["risk_fa"] = local["risk_fa"]
    result["fit_fa"] = local["fit_fa"]
    result["protocol"] = status["protocol"]
    result["source"] = "engine"
    return result
