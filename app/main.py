from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.analysis import align_frames, snapshot
from app.briefing import engine_brief
from app.config import settings
from app import mt5_bridge
from app.risk import exposure, size_hint

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Private market desk", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class BriefRequest(BaseModel):
    symbol: str
    timeframes: list[str] | None = None
    stop_distance: float = Field(default=0, ge=0)
    tick_value_per_lot: float = Field(default=1, gt=0)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True, "read_only": True, "sends_orders": False}


@app.get("/api/account")
def api_account():
    try:
        mt5_bridge.initialize()
        acc = mt5_bridge.account()
        pos = mt5_bridge.positions()
        return {"account": acc, "positions": pos, "exposure": exposure(acc, pos)}
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/symbols")
def api_symbols():
    try:
        mt5_bridge.initialize()
        return {"symbols": mt5_bridge.symbols()}
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/market/{symbol}")
def api_market(symbol: str):
    try:
        mt5_bridge.initialize()
        tfs = settings.timeframes()
        frames = []
        for tf in tfs:
            candles = mt5_bridge.rates(symbol, tf)
            frames.append(snapshot(candles, tf))
        return {
            "symbol": symbol.upper(),
            "tick": mt5_bridge.tick(symbol),
            "frames": frames,
            "alignment": align_frames(frames),
            "watchlist": settings.watch_symbols(),
        }
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/api/briefing")
def api_briefing(req: BriefRequest):
    try:
        mt5_bridge.initialize()
        acc = mt5_bridge.account()
        pos = mt5_bridge.positions()
        tfs = req.timeframes or settings.timeframes()
        frames = [snapshot(mt5_bridge.rates(req.symbol, tf), tf) for tf in tfs]
        payload = {
            "symbol": req.symbol.upper(),
            "tick": mt5_bridge.tick(req.symbol),
            "frames": frames,
            "alignment": align_frames(frames),
            "exposure": exposure(acc, pos),
            "positions": pos,
            "size_hint": size_hint(
                float(acc.get("equity") or 0),
                settings.risk_per_trade_pct,
                req.stop_distance,
                req.tick_value_per_lot,
            ),
        }
        payload["briefing"] = engine_brief(payload)
        return payload
    except Exception as extra:
        raise HTTPException(503, str(extra)) from extra


@app.get("/api/history")
def api_history():
    try:
        mt5_bridge.initialize()
        return {"deals": mt5_bridge.deals()}
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


def run():
    import uvicorn

    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=False)


if __name__ == "__main__":
    run()
