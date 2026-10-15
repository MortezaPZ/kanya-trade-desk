# Private market desk

Local, private assistant for MetaTrader 5. Phase 1 is **read-only**: it reads the account and market, then returns a structured briefing. It does not place, change, or close orders.

## What it does

- Reads balance, equity, open positions, and deal history from the local terminal
- Lists symbols available in the terminal and fetches selected market data on demand (metals, energy, indices, FX, crypto, and other instruments)
- Builds a multi-timeframe view: trend, simple structure, candle patterns
- Sends the selected symbol's chart data to the configured AI API and returns a Persian market analysis with conditional scenarios
- Calculates account risk and position-size guidance locally; account details, positions, and entry notes are not sent to the AI provider
- Suggests a position size from equity — advisory only

## What it does not do

- No order send, no auto-entry, no auto-exit
- No public cloud workspace for the trader’s book
- No profit guarantee

## Run locally (Windows, same machine as the terminal)

Open and log in to the broker’s MetaTrader 5 terminal first, then double-click `KanyaTradeDesk.exe` in the Windows app package. It opens the dashboard in the browser automatically and has a simple close button. It does not require a terminal window or a separate Python installation. The `.env` settings and journal are stored under `%APPDATA%\KanyaTradeDesk`. A portable terminal under `runtime\mt5` is optional and is not included in the client package.

For source development, `start.bat` remains available. It creates a local Python environment on first run and opens the dashboard after the server starts.

Or run manually:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m app.main
```

Open `http://127.0.0.1:8787`

The app does not store broker passwords; log in through the broker terminal. It binds only to a loopback address. AI market analysis requires separately billed API access; a chat subscription alone is not an API key. Configure `LLM_PROTOCOL`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, and the authentication headers from the provider's API documentation in the local `.env` file. Until a valid API is configured and responds, the app clearly marks AI analysis as unavailable instead of presenting local rules as AI output. Persian setup and privacy notes: `docs/CLIENT.md`.

## Tests

```
pytest -q
```

## Session continuity

Work in short sessions. Start from `ops/SESSION_START.md`. Before time runs out, follow `ops/SESSION_END.md`. Live state lives in `docs/HANDOFF.md`.
