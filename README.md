# Small-Cap Live Scanner + Paper Trader

A mobile-first small-cap research dashboard for NASDAQ/NYSE discovery, TradingView charts/screener, technical analysis, local watchlists, presets, notifications and a paper-trade journal.

## Current dashboard

- TradingView Top Movers widget with a bounded mobile viewport
- TradingView Market Screener in an independently scrollable area
- Custom ticker analysis with saved settings and local presets
- TradingView Advanced Chart
- TradingView Symbol Info quote widget
- TradingView Technical Analysis widget
- Symbol-specific TradingView news timeline
- Yahoo Finance and StockTitan research links
- LONG / SHORT workflow with transparent entry/stop/target methodology
- Local ticker watchlist and notification centre
- Local paper-trade journal with P/L, win rate, best trade and JSON export
- Responsive phone/tablet/desktop layout

## Important data limitation

The GitHub Pages dashboard is intentionally static. TradingView widgets run in cross-origin iframes, so the page cannot legally/reliably read their internal screener rows or OHLCV values with JavaScript. The dashboard therefore does **not** fabricate live prices, probabilities or trade levels.

The numerical quant engine should only be enabled when a permitted browser-readable/server-side OHLCV source is connected. The existing FastAPI backend supports an optional market-data provider through environment variables for local/server deployments.

As of September 2026, Massive's free Stocks Basic plan is EOD rather than real-time and does not include snapshot, trades or quotes. Do not describe the free tier as real-time. For genuine intraday scanner/alerting, a data plan that explicitly permits the required real-time endpoints is required.

## GitHub Pages

The root `index.html` launches `static/dashboard.html`. Enable GitHub Pages from the repository's `main` branch and root folder. The dashboard needs no API key to display the TradingView widgets and local tools.

## Local FastAPI app

```bash
pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Open `http://127.0.0.1:8000` for the scanner and `http://127.0.0.1:8000/paper` for the paper trader.

Without a market-data key the backend uses DEMO_MODE. For a supported provider, configure the environment variables described in `.env.example`.

## Paper trader

The simulator is separate from broker execution. It cannot submit live orders.

Default controls include a $1,000 starting paper balance, 1% risk budget per trade, 10% maximum position size, 3% maximum daily loss, stop-loss/take-profit monitoring, trade history and an emergency kill switch.

## Quant methodology

The project uses transparent concepts rather than pretending to have a magical prediction model:

- Momentum / price velocity
- Relative volume
- VWAP location
- Breakout/retest structure
- Volatility / ATR
- Support and resistance
- Catalyst quality
- Position sizing from risk and stop distance

A score is a ranking heuristic, not a probability of profit and not investment advice.

## Trading 212

No live Trading 212 execution is connected. Never put a Trading 212 secret/API key into the repository or chat. Broker execution should only be added after the scanner and paper strategy have been validated and the current Trading 212 API contract has been verified.

## Roadmap to a true real-time scanner

1. Connect a permitted real-time OHLCV provider through the FastAPI/server layer.
2. Build the exchange-verified small-cap universe and market-cap/liquidity filters.
3. Add 1m/5m/15m momentum, RVOL, VWAP and ATR calculations.
4. Add SEC/press-release catalyst ingestion and dilution/offering/reverse-split risk flags.
5. Add historical storage and a backtester for score calibration.
6. Add server-side alerts and push notifications.
7. Validate the strategy in the paper trader before considering any broker connection.
