# Small-Cap Live Scanner + AI Paper Trader

A mobile-friendly dashboard for scanning US small-cap stocks with momentum, relative volume, news/catalyst scoring and a transparent composite score. V1 now includes a separate paper-trading dashboard and hard risk controls.

## Run locally

```bash
pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Open `http://127.0.0.1:8000` for the scanner and `http://127.0.0.1:8000/paper` for the paper trader.

Without a market-data key the app uses DEMO_MODE. For live provider data, set `MASSIVE_API_KEY` and `DEMO_MODE=false` in your deployment environment.

## Paper trading V1

The simulator is deliberately separate from any broker integration. It cannot submit live orders.

Default controls:

- Starting paper balance: `$1,000`
- Risk budget: `1%` of equity per trade
- Maximum position: `10%` of equity
- Maximum daily loss: `3%`
- Automatic stop-loss / take-profit monitoring on scanner refresh
- Manual kill switch
- Trade history and equity snapshot

The paper engine sizes positions from the stop distance rather than simply allocating a fixed cash amount.

## Quant score

`Composite = 0.30 Momentum + 0.25 Volume + 0.15 Breakout + 0.15 VWAP + 0.15 Catalyst`

The catalyst layer currently uses a transparent keyword classifier. It is intentionally not presented as a trained predictive model. The score is a ranking heuristic, not investment advice or a guarantee of future returns.

## API endpoints

- `GET /api/stocks` — current scanner candidates
- `GET /api/paper` — paper account state
- `POST /api/paper/buy` — simulated long entry
- `POST /api/paper/sell` — simulated exit
- `POST /api/paper/reset` — reset simulator
- `POST /api/paper/kill-switch` — disable paper trading

## Trading 212 integration status

**Not connected in V1.** Do not add a Trading 212 API secret to this repository or to chat.

Trading 212 currently offers a Public API for eligible Invest and Stocks & Shares ISA accounts, with configurable permissions and support for live market, limit, stop and stop-limit orders. API keys can be restricted by IP and should be treated as sensitive credentials. We will only implement broker execution after the scanner and paper strategy have been tested and the exact current API contract is verified.

## Production roadmap

1. Exchange-verified small-cap universe and market-cap cache
2. Real-time market data rather than periodic snapshots
3. SEC filings + press-release ingestion
4. Better dilution / offering / reverse-split detection
5. Historical database and backtester
6. Calibrated continuation/reversal model
7. Trading 212 read-only connection
8. Trading 212 paper/demo validation where supported
9. Restricted live API execution with hard limits and an emergency stop
