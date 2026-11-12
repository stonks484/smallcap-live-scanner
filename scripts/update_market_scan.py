#!/usr/bin/env python3
"""Build a transparent, delayed-free-data candidate snapshot for GitHub Pages."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
OUT = Path("data/market_scan.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SmallCapLiveScanner/1.0; +https://github.com/stonks484/smallcap-live-scanner)",
    "Accept": "application/json",
}


def get_json(url: str) -> dict:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=25) as response:
        return json.load(response)


def fetch_screener(name: str) -> list[dict]:
    params = urlencode({"scrIds": name, "count": 250, "formatted": "false", "lang": "en-US", "region": "US"})
    payload = get_json(f"{BASE}?{params}")
    result = payload.get("finance", {}).get("result") or []
    if not result:
        raise RuntimeError(f"Yahoo Finance returned no screener result for {name}")
    return result[0].get("quotes") or []


def main() -> None:
    tickers: dict[str, dict] = {}
    # Yahoo's small-cap screen is capped at 250 results; downstream ranking is by daily move.
    for screen in ("small_cap_gainers",):
        for row in fetch_screener(screen):
            symbol = str(row.get("symbol") or "").strip().upper()
            if symbol and symbol.replace("-", "").replace(".", "").isalnum():
                tickers[symbol] = row

    rows = []
    for symbol, q in tickers.items():
        price = q.get("regularMarketPrice")
        change = q.get("regularMarketChangePercent")
        volume = q.get("regularMarketVolume")
        cap = q.get("marketCap")
        if not all(isinstance(x, (int, float)) for x in (price, change, volume)):
            continue
        if price <= 0 or price > 50 or volume < 50_000 or change < 3:
            continue
        if cap is None or cap < 10_000_000 or cap > 2_000_000_000:
            continue
        rows.append({
            "ticker": symbol,
            "price": round(price, 4),
            "change_pct": round(change, 2),
            "volume": int(volume),
            "market_cap": int(cap) if isinstance(cap, (int, float)) else None,
            "exchange": q.get("exchangeName") or q.get("fullExchangeName") or "",
            "source": "Yahoo Finance public screener",
            "volume_source": "Yahoo Finance public screener",
        })

    if not rows:
        raise RuntimeError("No valid candidates were returned; leaving the last published snapshot unchanged")
    rows.sort(key=lambda r: (r["change_pct"], r["volume"]), reverse=True)
    rows = rows[:50]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = {
        "schema_version": 1,
        "generated_at_utc": now,
        "source": "Yahoo Finance public small-cap screener",
        "source_url": "https://finance.yahoo.com/screener/predefined/small_cap_gainers",
        "refresh_interval_minutes": 15,
        "data_note": "Free public data; may be delayed or end-of-day. Not a real-time consolidated feed. Volume is reported market volume, not buy volume.",
        "filters": {"price_max": 50, "volume_min": 50000, "change_pct_min": 3, "market_cap_min": 10000000, "market_cap_max": 2000000000},
        "count": len(rows),
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Published {len(rows)} candidate rows at {now}")


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, URLError, TimeoutError, ValueError, RuntimeError) as exc:
        print(f"Market scan update failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
