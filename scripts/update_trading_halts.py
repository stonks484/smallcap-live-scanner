#!/usr/bin/env python3
"""Fetch official Nasdaq Trader halt/resumption RSS snapshots."""
import json, re, html
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

BASE = "https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts"
OUT = Path("data/trading_halts.json")
HEADERS = {"User-Agent": "Mozilla/5.0 SmallCapLiveScanner/1.0", "Accept": "application/rss+xml, application/xml, text/xml"}

FIELDS = ["Halt Date", "Halt Time", "Issue Symbol", "Issue Name", "Mkt", "Reason Code", "Date", "Resumption Quote Time", "Resumption Trade Time", "Pause Threshold Price"]
ALIASES = {"Halt Date":"halt_date", "Halt Time":"halt_time", "Issue Symbol":"symbol", "Issue Name":"name", "Mkt":"market", "Reason Code":"reason_code", "Date":"resume_date", "Resumption Quote Time":"resume_quote_time", "Resumption Trade Time":"resume_trade_time", "Pause Threshold Price":"pause_price"}

def fetch(url):
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=25) as r:
        return ET.fromstring(r.read())

def text_content(node):
    return html.unescape(" ".join(t.strip() for t in node.itertext() if t.strip()))

def parse_item(item):
    raw = text_content(item)
    # Some feed versions put fields in a pipe-separated title; parse both title and description.
    result = {}
    for field in FIELDS:
        label = r"(?<!Halt )\bDate" if field == "Date" else re.escape(field)
        m = re.search(r"(?:^|\b)" + label + r"\s*[:=]\s*(.*?)(?=\s+(?:" + "|".join(map(re.escape, FIELDS)) + r")\s*[:=]|$)", raw, re.I)
        if m:
            result[ALIASES[field]] = m.group(1).strip(" |;")
    title = item.findtext("title") or ""
    if not result.get("symbol"):
        m = re.search(r"(?:Trading Halt|Trade Halt)\s*[-:]?\s*([A-Z][A-Z0-9.\-/]*)", title, re.I)
        if m: result["symbol"] = m.group(1).upper()
    return result if result.get("symbol") else None

def main():
    now = datetime.now().astimezone()
    today = now.strftime("%m%d%Y")
    urls = [BASE, BASE + "&haltdate=" + today, BASE + "&resumedate=" + today]
    records = {}
    successful_feeds = 0
    for url in urls:
        try:
            root = fetch(url)
            successful_feeds += 1
            for item in root.findall(".//item"):
                row = parse_item(item)
                if not row: continue
                key = (row.get("symbol",""), row.get("halt_date",""), row.get("halt_time",""))
                records[key] = {**records.get(key, {}), **row}
        except Exception as exc:
            print("Feed fetch warning:", url, str(exc))
    rows = list(records.values())
    if successful_feeds == 0:
        raise RuntimeError("All Nasdaq Trader RSS requests failed; refusing to overwrite the last good file")
    rows.sort(key=lambda x: (x.get("halt_date",""), x.get("halt_time","")), reverse=True)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
        "source": "Nasdaq Trader official Trade Halt RSS",
        "timezone": "America/New_York",
        "coverage": "Nasdaq-listed and other-exchange-listed securities; today's halt/resumption history plus current open halts",
        "rows": rows
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, separators=(",",":")) + "\n", encoding="utf-8")
    print("Published", len(rows), "halt records")

if __name__ == "__main__":
    main()
