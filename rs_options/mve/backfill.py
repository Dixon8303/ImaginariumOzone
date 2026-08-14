"""Historical daily-bar backfill from Stooq (free, no API key). Spec §46.

Stock/ETF daily bars only — historical options chains require a paid
vendor and are NOT fetched here. This backfill enables underlying-signal
backtesting (mve.backtest) and RS feature history.

Run from rs_options/ on a machine with open internet:

    python -m mve.backfill              # full universe, ~5 years
    python -m mve.backfill NVDA SPY     # specific tickers
"""
from __future__ import annotations

import io
import json
import sys
import time
import urllib.request

import pandas as pd

from .store import BAR_COLS, DataStore
from .universe import required_tickers

STOOQ_URL = "https://stooq.com/q/d/l/?s={symbol}&i=d&d1={d1}&d2={d2}"
YAHOO_URL = ("https://query1.finance.yahoo.com/v8/finance/chart/"
             "{ticker}?range={years}y&interval=1d")
DEFAULT_YEARS = 5
DATA_ROOT = "data/parquet"


def stooq_symbol(ticker: str) -> str:
    return f"{ticker.lower()}.us"


def parse_stooq_csv(text: str, ticker: str) -> pd.DataFrame:
    """Stooq CSV (Date,Open,High,Low,Close,Volume) -> canonical bar frame."""
    df = pd.read_csv(io.StringIO(text))
    required = {"Date", "Open", "High", "Low", "Close"}
    if df.empty or not required.issubset(df.columns):
        return pd.DataFrame(columns=BAR_COLS)
    if "Volume" not in df.columns:
        df["Volume"] = 0
    out = pd.DataFrame({
        "ticker": ticker,
        "trade_date": df["Date"],
        "open": df["Open"], "high": df["High"],
        "low": df["Low"], "close": df["Close"],
        "volume": df["Volume"].fillna(0).astype("int64"),
    })
    return out.dropna(subset=["open", "high", "low", "close"])


def parse_yahoo_json(payload: dict, ticker: str) -> pd.DataFrame:
    """Yahoo v8 chart JSON -> canonical bar frame."""
    try:
        result = payload["chart"]["result"][0]
        stamps = result["timestamp"]
        q = result["indicators"]["quote"][0]
    except (KeyError, IndexError, TypeError):
        return pd.DataFrame(columns=BAR_COLS)
    rows = pd.DataFrame({
        "ticker": ticker,
        "trade_date": pd.to_datetime(stamps, unit="s", utc=True)
                        .tz_convert("America/New_York").date.astype(str),
        "open": q["open"], "high": q["high"],
        "low": q["low"], "close": q["close"],
        "volume": pd.Series(q["volume"]).fillna(0).astype("int64"),
    })
    return rows.dropna(subset=["open", "high", "low", "close"])


def fetch_bars(ticker: str, start: str, end: str, pause_s: float = 0.6,
               years: int = DEFAULT_YEARS) -> pd.DataFrame:
    """Stooq first (no key, clean CSV); Yahoo chart API as fallback."""
    url = STOOQ_URL.format(symbol=stooq_symbol(ticker),
                           d1=start.replace("-", ""), d2=end.replace("-", ""))
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        bars = parse_stooq_csv(text, ticker)
    except Exception:
        bars = pd.DataFrame(columns=BAR_COLS)
    if bars.empty:
        req = urllib.request.Request(
            YAHOO_URL.format(ticker=ticker, years=years),
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            bars = parse_yahoo_json(json.loads(resp.read()), ticker)
        bars = bars[(bars["trade_date"] >= start) & (bars["trade_date"] <= end)]
    time.sleep(pause_s)                      # be polite to the free endpoints
    return bars


def backfill(tickers: list | None = None, years: int = DEFAULT_YEARS,
             root: str = DATA_ROOT) -> dict:
    from datetime import date, timedelta
    tickers = tickers or required_tickers()
    end = date.today()
    start = end - timedelta(days=int(years * 365.25))
    store = DataStore(root)
    report = {}
    for t in tickers:
        try:
            bars = fetch_bars(t, str(start), str(end))
            n = store.ingest_bars(bars) if not bars.empty else 0
            report[t] = n
            print(f"{t:<6} {n:>5} bars" + ("  <-- EMPTY, check symbol" if n == 0 else ""))
        except Exception as e:                # keep going; report the failure
            report[t] = 0
            print(f"{t:<6} FAILED: {e}")
    return report


if __name__ == "__main__":
    requested = sys.argv[1:] or None
    print(f"Backfilling {len(requested or required_tickers())} tickers into {DATA_ROOT} ...")
    result = backfill(requested)
    ok = sum(1 for v in result.values() if v > 0)
    print(f"\nDone: {ok}/{len(result)} tickers with data. "
          f"Next: python -m mve.backtest")
