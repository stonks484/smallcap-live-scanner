# Small-Cap Live Scanner

A mobile-friendly dashboard for scanning NASDAQ/NYSE small-cap stocks that are up at least 15%, with volume, RVOL, news/catalyst headlines and a transparent momentum composite score.

## Run locally

```bash
pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`.

Without a market-data key the app uses DEMO_MODE. For live provider data, set `MASSIVE_API_KEY` and `DEMO_MODE=false` in your deployment environment.

## Deploy on Render

Create a new Blueprint/Web Service from this repository. `render.yaml` supplies the build and start commands. Add `MASSIVE_API_KEY` as a secret environment variable in Render.

## Quant score

The MVP uses:

`Composite = 0.30 Momentum + 0.25 Volume + 0.15 Breakout + 0.15 VWAP + 0.15 Catalyst`

This is a heuristic ranking signal, not a trained model, investment advice, or a guarantee of future returns.

## Production roadmap

- Real-time streaming feed rather than periodic snapshots
- Exchange-verified NASDAQ/NYSE universe and market-cap cache
- Historical intraday database
- SEC filing and press-release ingestion
- Trained and calibrated continuation/reversal models
- Push alerts
- User accounts and watchlists
- Backtesting and model performance monitoring
