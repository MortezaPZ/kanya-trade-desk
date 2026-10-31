# Local MetaTrader 5 Market Desk

A Windows dashboard for reviewing account activity and market data through a local MetaTrader 5 terminal.

## Overview

The app runs on the same machine as the broker terminal. It reads account balances, open positions, deal history, and available symbols, then builds a multi-timeframe market view. Optional AI analysis uses only chart data for the selected symbol and returns a Persian summary with conditional scenarios.

Risk and position-size guidance is calculated locally and is advisory. Account balances, positions, and entry notes are not sent to the AI provider.

## Safety and limitations

- Read-only: the app cannot place, modify, or close orders.
- Broker credentials stay in the broker terminal; the app does not store broker passwords.
- The web dashboard binds to the local loopback address.
- AI analysis requires a separately configured and billed API. Selected chart data is sent to that provider.
- Market analysis is informational and does not guarantee profit.
- Until a valid AI API responds, the app marks analysis as unavailable rather than presenting local rules as AI output.

## Run on Windows

1. Open the broker's MetaTrader 5 terminal and sign in.
2. Launch KanyaTradeDesk.exe from the Windows release package.
3. Open the dashboard at http://127.0.0.1:8787 if it does not open automatically.

The application stores its local settings and journal under the current user's %APPDATA%\KanyaTradeDesk directory. A portable MT5 terminal is optional and is not included.

## Develop from source

The start.bat script creates a local Python environment on first run and starts the dashboard. To run the steps manually:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    copy .env.example .env
    python -m app.main

Configure LLM_PROTOCOL, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, and the authentication headers in the local .env file using the selected provider's API documentation.

## Documentation

Persian installation, usage, and privacy instructions are available in the [Persian user guide](docs/USER-GUIDE-FA.md).

## Tests

    pytest -q