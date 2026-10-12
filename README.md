# Private market desk

Local, private assistant for MetaTrader 5. Phase 1 is **read-only**: it reads the account and market, then returns a structured briefing. It does not place, change, or close orders.

## What it does

- Reads balance, equity, open positions, and deal history from the local terminal
- Snapshots any symbol the broker exposes (metals, energy, indices, FX, crypto)
- Builds a multi-timeframe view: trend, simple structure, candle patterns
- Returns a short briefing: market, risk note, what to watch
- Suggests a position size from equity — advisory only

## What it does not do

- No order send, no auto-entry, no auto-exit
- No public cloud workspace for the trader’s book
- No profit guarantee

## Run locally (Windows, same machine as the terminal)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m app.main
```

Open `http://127.0.0.1:8787`

Fill `.env` with terminal login (or leave login blank if the terminal is already open). Put the analysis-engine key in `.env` only.

## Tests

```
pytest -q
```

## Session continuity

Work in short sessions. Start from `ops/SESSION_START.md`. Before time runs out, follow `ops/SESSION_END.md`. Live state lives in `docs/HANDOFF.md`.
