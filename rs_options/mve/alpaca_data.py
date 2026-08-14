"""Alpaca Market Data fetcher (free IEX feed). Spec §46 vendor seam.

Reads APCA_API_KEY_ID / APCA_API_SECRET_KEY from the environment — keys
never appear in code or files. Daily bars extend the existing store;
minute bars land in an intraday store for the shorter-horizon research
track (§38 latency class still applies: intraday ≠ speed-competitive).

Run from rs_options/ on a machine with the keys set:

    python -m mve.alpaca_data                # daily bars, full universe
    python -m mve.alpaca_data --minute NVDA  # minute bars, one ticker
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request

import pandas as pd

from .store import BAR_COLS, DataStore
from .universe import required_tickers

DATA_URL = "https://data.alpaca.markets/v2/stocks/{symbol}/bars"
DATA_ROOT = "data/parquet"
MINUTE_DAYS = 60          # CALIBRATE — intraday research window
DAILY_YEARS = 5


def _headers() -> dict:
    key = os.environ.get("APCA_API_KEY_ID")
    secret = os.environ.get("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise SystemExit(
            "APCA_API_KEY_ID / APCA_API_SECRET_KEY not set. "
            "Add them to ~/.zshrc as described in the setup steps.")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}


def parse_alpaca_bars(payload: dict, ticker: str,
                      intraday: bool = False) -> pd.DataFrame:
    """Alpaca v2 bars JSON -> canonical frame (plus `ts` when intraday)."""
    bars = payload.get("bars") or []
    if not bars:
        cols = BAR_COLS + (["ts"] if intraday else [])
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(bars)
    ts = pd.to_datetime(df["t"], utc=True)
    out = pd.DataFrame({
        "ticker": ticker,
        "trade_date": ts.dt.tz_convert("America/New_York").dt.date.astype(str),
        "open": df["o"], "high": df["h"], "low": df["l"], "close": df["c"],
        "volume": df["v"].astype("int64"),
    })
    if intraday:
        out["ts"] = df["t"]
    return out


def fetch_bars(ticker: str, timeframe: str, start: str, end: str,
               pause_s: float = 0.35) -> pd.DataFrame:
    """Paginated fetch; free tier uses the IEX feed."""
    frames = []
    token = None
    intraday = timeframe != "1Day"
    while True:
        params = {"timeframe": timeframe, "start": start, "end": end,
                  "limit": 10_000, "feed": "iex", "adjustment": "split"}
        if token:
            params["page_token"] = token
        url = DATA_URL.format(symbol=ticker) + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=_headers())
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())
        frames.append(parse_alpaca_bars(payload, ticker, intraday=intraday))
        token = payload.get("next_page_token")
        time.sleep(pause_s)
        if not token:
            break
    if not frames:
        return pd.DataFrame(columns=BAR_COLS)
    return pd.concat(frames, ignore_index=True)


class IntradayStore:
    """Minute bars, parquet per ticker/day. Idempotent on (ticker, ts)."""

    def __init__(self, root: str):
        self.root = os.path.join(root, "intraday")
        os.makedirs(self.root, exist_ok=True)

    def ingest(self, df: pd.DataFrame) -> int:
        written = 0
        for (ticker, day), part in df.groupby(["ticker", "trade_date"]):
            d = os.path.join(self.root, str(ticker))
            os.makedirs(d, exist_ok=True)
            path = os.path.join(d, f"{day}.parquet")
            if os.path.exists(path):
                part = pd.concat([pd.read_parquet(path), part])
            part = part.drop_duplicates(subset=["ticker", "ts"], keep="last")
            part.sort_values("ts").to_parquet(path, index=False)
            written += len(part)
        return written

    def bars(self, ticker: str, day: str) -> pd.DataFrame:
        path = os.path.join(self.root, ticker, f"{day}.parquet")
        if not os.path.exists(path):
            return pd.DataFrame(columns=BAR_COLS + ["ts"])
        return pd.read_parquet(path)

    def days(self, ticker: str) -> list:
        d = os.path.join(self.root, ticker)
        if not os.path.isdir(d):
            return []
        return sorted(f[:-8] for f in os.listdir(d) if f.endswith(".parquet"))


def main() -> None:
    from datetime import date, timedelta
    args = sys.argv[1:]
    store = DataStore(DATA_ROOT)
    end = str(date.today())

    if args and args[0] == "--minute":
        tickers = args[1:] or required_tickers()
        start = str(date.today() - timedelta(days=MINUTE_DAYS))
        intraday = IntradayStore(DATA_ROOT)
        for t in tickers:
            try:
                bars = fetch_bars(t, "1Min", start, end)
                n = intraday.ingest(bars) if not bars.empty else 0
                print(f"{t:<6} {n:>7} minute bars")
            except Exception as e:
                print(f"{t:<6} FAILED: {e}")
        return

    start = str(date.today() - timedelta(days=int(DAILY_YEARS * 365.25)))
    for t in (args or required_tickers()):
        try:
            bars = fetch_bars(t, "1Day", start, end)
            n = store.ingest_bars(bars[BAR_COLS]) if not bars.empty else 0
            print(f"{t:<6} {n:>5} daily bars")
        except Exception as e:
            print(f"{t:<6} FAILED: {e}")


if __name__ == "__main__":
    main()
