from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import desk, journal
from app.config import settings

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Private market desk", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class BriefRequest(BaseModel):
    symbol: str
    timeframes: list[str] | None = None
    stop_distance: float = Field(default=0, ge=0)
    tick_value_per_lot: float = Field(default=0, ge=0)
    entry_note: str = Field(default="", max_length=500)
    save: bool = True


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    st = desk.status()
    return {
        "ok": True,
        "read_only": True,
        "sends_orders": False,
        "connected": st["connected"],
        "engine_configured": st["engine_configured"],
        "error": st["error"],
    }


@app.get("/api/status")
def api_status():
    return desk.status()


@app.get("/api/account")
def api_account():
    st = desk.status()
    if not st["connected"]:
        raise HTTPException(503, st["error"] or "terminal unavailable")
    return st


@app.get("/api/symbols")
def api_symbols(q: str = Query(default="")):
    try:
        return desk.catalog(q)
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/watchlist")
def api_watchlist():
    try:
        return desk.watchlist()
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/market/{symbol}")
def api_market(symbol: str):
    try:
        data = desk.build_market(symbol)
        data["watchlist"] = settings.watch_symbols()
        return data
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/api/briefing")
def api_briefing(req: BriefRequest):
    try:
        payload = desk.build_briefing(
            req.symbol,
            req.stop_distance,
            req.tick_value_per_lot,
            req.timeframes,
            req.entry_note,
        )
        if req.save:
            payload["journal"] = desk.save_brief(payload)
        return payload
    except Exception as extra:
        raise HTTPException(503, str(extra)) from extra


@app.get("/api/history")
def api_history():
    try:
        desk.connect()
        return {"deals": desk.deals(), "journal": journal.recent()}
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/review/{symbol}")
def api_review(symbol: str):
    try:
        return desk.review(symbol)
    except Exception as extra:
        raise HTTPException(503, str(extra)) from extra


def run():
    import threading
    import time
    import urllib.error
    import urllib.request
    import webbrowser

    import uvicorn

    if settings.app_open_browser:
        url = f"http://{settings.app_host}:{settings.app_port}"

        def open_when_ready() -> None:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    with urllib.request.urlopen(url, timeout=1) as response:
                        if 200 <= response.status < 400:
                            webbrowser.open(url)
                            return
                except (OSError, urllib.error.URLError):
                    time.sleep(0.25)

        threading.Thread(target=open_when_ready, daemon=True).start()

    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=False)


if __name__ == "__main__":
    run()
