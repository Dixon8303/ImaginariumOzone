"""Company fundamentals (H10, spec §72) — SEC EDGAR XBRL, free, no key.

The point-in-time problem is the whole difficulty here. A quarter ending
2026-03-31 is not public knowledge on 2026-03-31 — it is published weeks
later. Using the fiscal period date would leak the future into every
backtest and manufacture an edge that cannot be traded.

EDGAR's companyfacts payload carries a `filed` date on every fact, which
is the date the number actually became public. This module keys
everything on `filed`, so a lookup for date D returns only what a reader
could have known by the close of D.

Metric: trailing profitability (net income over the last four reported
quarters). Mechanism, pre-registered: the profitability factor
(Novy-Marx 2013) says profitable firms outperform, and a breakout in an
unprofitable name is more speculative — more story than earnings, and
more prone to reversal when the story wobbles.

    python -m mve.fundamentals      # fetch/refresh filings for the universe
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from datetime import date

import pandas as pd

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/us-gaap/{tag}.json"
FUNDAMENTALS_DIR = os.path.join("data", "fundamentals")
NET_INCOME_TAGS = ("NetIncomeLoss", "ProfitLoss")
PAUSE_S = 0.2               # SEC asks for <= 10 requests/second
ETF_TICKERS = {"QQQ", "IWM"}   # no filings

# SEC requires a descriptive User-Agent with contact info. This is a
# research tool; identify it honestly rather than spoofing a browser.
UA = {"User-Agent": "ImaginariumOzone RS research (contact via GitHub)",
      "Accept-Encoding": "gzip, deflate"}


RETRIES = 4                 # transient DNS/network failures under load


def _get_with_retry(url: str, retries: int = RETRIES) -> dict:
    """Retry transient failures — a drop mid-universe leaves partial
    coverage, which biases every study that fails closed."""
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as e:
            last = e
            time.sleep(PAUSE_S * (2 ** attempt))
    raise last


def fetch_cik_map() -> dict:
    """{TICKER: cik int} from the SEC's public mapping file."""
    payload = _get_with_retry(TICKER_MAP_URL)
    return {row["ticker"].upper(): int(row["cik_str"])
            for row in payload.values()}


def parse_concept(payload: dict) -> pd.DataFrame:
    """companyconcept JSON -> (filed, period_end, value), point-in-time.

    Keeps only quarterly-ish facts (durations under ~100 days) and dedupes
    on (period_end), preferring the EARLIEST filing that reported it —
    that is when the number first became public.
    """
    rows = []
    for unit_rows in (payload.get("units") or {}).values():
        for r in unit_rows:
            if not r.get("filed") or not r.get("end") or r.get("val") is None:
                continue
            start, end = r.get("start"), r["end"]
            if start:
                span = (date.fromisoformat(end)
                        - date.fromisoformat(start)).days
                if span > 100:            # annual figure, not a quarter
                    continue
            rows.append({"filed": r["filed"], "period_end": end,
                         "value": float(r["val"])})
    if not rows:
        return pd.DataFrame(columns=["filed", "period_end", "value"])
    df = pd.DataFrame(rows).sort_values(["period_end", "filed"])
    df = df.drop_duplicates(subset=["period_end"], keep="first")
    return df.sort_values("filed").reset_index(drop=True)


def fetch_net_income(ticker: str, cik: int) -> pd.DataFrame:
    """First available net-income tag wins; tags vary by filer."""
    last_error = None
    for tag in NET_INCOME_TAGS:
        try:
            df = parse_concept(_get_with_retry(
                FACTS_URL.format(cik=cik, tag=tag)))
            time.sleep(PAUSE_S)
            if not df.empty:
                return df
        except Exception as e:
            last_error = e
            time.sleep(PAUSE_S)
    if last_error:
        raise last_error
    return pd.DataFrame(columns=["filed", "period_end", "value"])


def save_facts(ticker: str, df: pd.DataFrame,
               root: str = FUNDAMENTALS_DIR) -> str:
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, f"{ticker}.csv")
    df.to_csv(path, index=False)
    return path


def load_fundamentals(root: str = FUNDAMENTALS_DIR) -> dict:
    out = {}
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        if name.endswith(".csv"):
            out[name[:-4]] = pd.read_csv(os.path.join(root, name))
    return out


def trailing_net_income(facts: dict, ticker: str,
                        trade_date: str) -> float | None:
    """Sum of the last four quarters PUBLISHED on or before `trade_date`.
    None when fewer than four are known — never guessed at."""
    df = facts.get(ticker)
    if df is None or df.empty:
        return None
    known = df[df["filed"] <= trade_date]
    if len(known) < 4:
        return None
    latest = known.sort_values("period_end").tail(4)
    return float(latest["value"].sum())


def is_profitable(facts: dict, ticker: str, trade_date: str) -> bool:
    """H10 filter: trailing four quarters profitable. Fail-closed — an
    unknown fundamental blocks rather than assuming quality."""
    total = trailing_net_income(facts, ticker, trade_date)
    return total is not None and total > 0


def main() -> None:
    from .universe import UNIVERSE
    tickers = sorted(t for t in UNIVERSE if t not in ETF_TICKERS)
    try:
        cik_map = fetch_cik_map()
    except Exception as e:
        raise SystemExit(f"Could not fetch the SEC ticker map: {e}")
    for t in tickers:
        cik = cik_map.get(t)
        if cik is None:
            print(f"{t:<6} no CIK found — skipped")
            continue
        try:
            df = fetch_net_income(t, cik)
            save_facts(t, df)
            span = (f"{df['filed'].iloc[0]} -> {df['filed'].iloc[-1]}"
                    if not df.empty else "no facts")
            print(f"{t:<6} {len(df):>4} quarters  {span}")
        except Exception as e:
            print(f"{t:<6} FAILED: {e}")
    print(f"\n{len(load_fundamentals())}/{len(tickers)} tickers on disk. "
          "Next: python -m mve.hypotheses")


if __name__ == "__main__":
    main()
