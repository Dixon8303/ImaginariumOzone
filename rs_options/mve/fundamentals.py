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

import gzip
import json
import os
import time
import urllib.request
from datetime import date, timedelta

import pandas as pd

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/us-gaap/{tag}.json"
FUNDAMENTALS_DIR = os.path.join("data", "fundamentals")
NET_INCOME_TAGS = ("NetIncomeLoss", "ProfitLoss")
PAUSE_S = 0.2               # SEC asks for <= 10 requests/second
ETF_TICKERS = {"QQQ", "IWM"}   # no filings

# The SEC's fair-access policy REQUIRES a User-Agent carrying a real
# contact address, and returns 403 without one. The address is read from
# SEC_CONTACT_EMAIL rather than hard-coded: an email is the operator's to
# give, and it does not belong in a public repository.
def _ua() -> dict:
    email = os.environ.get("SEC_CONTACT_EMAIL", "").strip()
    if not email or "@" not in email:
        raise SystemExit(
            "SEC_CONTACT_EMAIL is not set. The SEC requires a contact "
            "address in the request header and returns 403 without one.\n"
            "Add to ~/.zshrc, then open a new Terminal:\n"
            '  export SEC_CONTACT_EMAIL="you@example.com"')
    return {"User-Agent": f"ImaginariumOzone RS research {email}",
            "Accept-Encoding": "gzip, deflate"}


RETRIES = 4                 # transient DNS/network failures under load


def _decode(resp) -> dict:
    """SEC honours our Accept-Encoding and returns gzip; urllib does NOT
    decompress automatically, so the raw bytes start 1f 8b and json
    chokes. Decompress explicitly rather than dropping compression —
    these payloads are large and the SEC asks callers to accept gzip."""
    raw = resp.read()
    if resp.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw)


def _get_with_retry(url: str, retries: int = RETRIES) -> dict:
    """Retry transient failures — a drop mid-universe leaves partial
    coverage, which biases every study that fails closed. A decode error
    is deterministic, so it is raised immediately instead of retried."""
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=_ua())
            with urllib.request.urlopen(req, timeout=30) as resp:
                return _decode(resp)
        except (UnicodeDecodeError, json.JSONDecodeError, gzip.BadGzipFile):
            raise                       # retrying cannot fix a bad payload
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


# Buffer around the estimated next filing — CALIBRATE, not validated.
# Widened rather than narrowed on purpose: the cadence estimate below is
# already an approximation, and the failure mode this guards against
# (holding long premium through an unpriced IV event) is asymmetric —
# missing a real earnings date costs a skipped trade; treating a
# earnings-adjacent trade as safe costs a crushed position.
EARNINGS_WINDOW_BUFFER_DAYS = 5


def next_expected_filing_window(facts: dict, ticker: str,
                                trade_date: str,
                                buffer_days: int = EARNINGS_WINDOW_BUFFER_DAYS
                                ) -> tuple | None:
    """Estimate an earnings-adjacent blackout window from this ticker's
    OWN filing cadence — the median gap between past `filed` dates,
    projected forward from the most recent one.

    This is a PROXY for the next earnings date, not the date itself: a
    10-Q/10-K filing usually lands within days of the earnings release
    but is a different event, and no forward earnings-calendar feed is
    wired into this project (that is real, undone work — see
    docs/RESEARCH_LOG.md). Reported and used as an estimate everywhere
    it appears, never presented as a known date.

    Returns None when fewer than two filings are known for this ticker
    as of `trade_date` — cadence is unknowable from a single data point,
    and this must fail toward NOT gating rather than guessing at a
    window (an ETF like QQQ/IWM, with no filings at all, always returns
    None here — correctly, since single-company earnings risk does not
    apply to it).
    """
    df = facts.get(ticker)
    if df is None or df.empty:
        return None
    known = df[df["filed"] <= trade_date]
    filed_dates = sorted(set(known["filed"]))
    if len(filed_dates) < 2:
        return None
    gaps = sorted(
        (date.fromisoformat(b) - date.fromisoformat(a)).days
        for a, b in zip(filed_dates, filed_dates[1:]))
    median_gap = gaps[len(gaps) // 2]
    last_filed = date.fromisoformat(filed_dates[-1])
    next_expected = last_filed + timedelta(days=median_gap)
    start = next_expected - timedelta(days=buffer_days)
    end = next_expected + timedelta(days=buffer_days)
    return (start.isoformat(), end.isoformat())


def overlaps_earnings_window(entry_date: date, expiry: date,
                             window: tuple | None) -> bool:
    """Whether a position held from `entry_date` through `expiry` would
    span the estimated blackout `window`. `window=None` (cadence
    unknown) always returns False — an unknown estimate must not gate a
    trade, the same fail-toward-inaction rule as the IV-rank penalty
    ('unknown -> no penalty, reported as uncalibrated')."""
    if window is None:
        return False
    start, end = date.fromisoformat(window[0]), date.fromisoformat(window[1])
    return start <= expiry and end >= entry_date


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
