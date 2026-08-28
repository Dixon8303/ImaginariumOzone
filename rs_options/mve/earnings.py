"""Earnings announcement dates — H5 data layer (Alpha Vantage).

Fetches each stock's historical reported dates from Alpha Vantage's
EARNINGS endpoint into data/earnings/<ticker>.csv. The API key comes
from the ALPHAVANTAGE_API_KEY environment variable ONLY — never a file.

Free-tier limits: ~25 requests/day, 5/minute. Since the H-23 adoption
(2026-08-28) the universe holds 36 stocks (ETFs have no earnings), so a
FULL fresh fetch no longer fits in one free-tier day — it takes two.
That is already handled, not a problem: the fetch sleeps between calls
and skips tickers on disk, so a rate-limited run simply gets rerun
tomorrow and picks up where it stopped.

    python -m mve.earnings              # fetch missing tickers
    python -m mve.earnings --refresh    # re-fetch everything
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.request
from datetime import date

from .universe import UNIVERSE

URL = ("https://www.alphavantage.co/query?function=EARNINGS"
       "&symbol={symbol}&apikey={key}")
EARNINGS_DIR = os.path.join("data", "earnings")
ETF_TICKERS = {"QQQ", "IWM"}            # no earnings
PAUSE_S = 15.0                          # free tier: 5 calls/minute


def stock_tickers() -> list:
    return sorted(t for t in UNIVERSE if t not in ETF_TICKERS)


def _key() -> str:
    key = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not key:
        raise SystemExit(
            "ALPHAVANTAGE_API_KEY not set. Add to ~/.zshrc:\n"
            '  export ALPHAVANTAGE_API_KEY="your key here"\n'
            "then open a new Terminal window.")
    return key


def parse_earnings(payload: dict) -> list:
    """Alpha Vantage EARNINGS JSON -> sorted reported dates (ISO strings)."""
    if "quarterlyEarnings" not in payload:
        note = payload.get("Note") or payload.get("Information") \
            or payload.get("Error Message") or "unexpected response"
        raise ValueError(str(note)[:200])
    dates = {q.get("reportedDate") for q in payload["quarterlyEarnings"]}
    return sorted(d for d in dates if d)


def save_dates(ticker: str, dates: list, root: str = EARNINGS_DIR) -> str:
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, f"{ticker}.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["reported_date"])
        w.writerows([d] for d in dates)
    return path


def load_earnings(root: str = EARNINGS_DIR) -> dict:
    """{ticker: sorted list of datetime.date}. Empty dict if no data."""
    out = {}
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        if not name.endswith(".csv"):
            continue
        with open(os.path.join(root, name), newline="") as f:
            rows = list(csv.reader(f))
        out[name[:-4]] = sorted(
            date.fromisoformat(r[0]) for r in rows[1:] if r and r[0])
    return out


def fetch(ticker: str, key: str) -> list:
    req = urllib.request.Request(URL.format(symbol=ticker, key=key))
    with urllib.request.urlopen(req, timeout=30) as resp:
        return parse_earnings(json.loads(resp.read()))


def main() -> None:
    refresh = "--refresh" in sys.argv
    key = _key()
    have = load_earnings()
    for t in stock_tickers():
        if t in have and not refresh:
            print(f"{t:<6} {len(have[t]):>3} dates (on disk, skipped)")
            continue
        try:
            dates = fetch(t, key)
            save_dates(t, dates)
            print(f"{t:<6} {len(dates):>3} earnings dates")
        except Exception as e:
            print(f"{t:<6} FAILED: {e}")
        time.sleep(PAUSE_S)
    total = load_earnings()
    print(f"\n{len(total)}/{len(stock_tickers())} stock tickers on disk. "
          "Next: python -m mve.hypotheses")


if __name__ == "__main__":
    main()
