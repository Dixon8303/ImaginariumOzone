"""News attention (H9, spec §72) — Alpaca news API, free with APCA keys.

What is measured, and what is NOT.

MEASURED: attention — how many stories mention the ticker, versus its own
normal rate. This is mechanical, point-in-time, and needs no language
model to be reproducible five years from now.

NOT measured: sentiment. Scoring headlines as good or bad with a keyword
list produces a number that looks rigorous and is mostly noise, and one
that cannot be reproduced consistently across a rewrite. If sentiment
gets tested later it should be a separate, honestly-labelled hypothesis.

Pre-registered mechanism (stated before the data): the metaorder story
says breakouts driven by quiet institutional accumulation continue,
while the attention literature (Barber & Odean 2008) says retail buying
concentrated in high-attention names underperforms afterwards. Both
point the same way here: a breakout arriving in a burst of coverage is
more crowded and more likely to fade. So the filter SKIPS high-attention
signals — and if the data says the opposite, that is a finding, not a
reason to flip the story afterwards.

    python -m mve.news              # fetch/refresh daily article counts
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

import pandas as pd

from .alpaca_data import _headers
from .universe import UNIVERSE

NEWS_URL = "https://data.alpaca.markets/v1beta1/news"
NEWS_DIR = os.path.join("data", "news")
HISTORY_YEARS = 6
PAUSE_S = 0.35

# CALIBRATE — attention windows, not validated optima (LAW 12).
RECENT_DAYS = 5             # "how loud is it right now"
BASELINE_DAYS = 60          # "how loud is it normally"
MIN_BASELINE_ARTICLES = 5   # below this the ratio is not meaningful


def parse_news(payload: dict, ticker: str) -> pd.DataFrame:
    """Alpaca news JSON -> one row per day with an article count."""
    items = payload.get("news") or []
    if not items:
        return pd.DataFrame(columns=["trade_date", "articles"])
    days = [str(pd.Timestamp(i["created_at"]).tz_convert(
        "America/New_York").date()) for i in items if i.get("created_at")]
    counts = pd.Series(days).value_counts().sort_index()
    return pd.DataFrame({"trade_date": counts.index,
                         "articles": counts.values})


def fetch_counts(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Paginated fetch of daily article counts for one ticker."""
    frames, token = [], None
    while True:
        params = {"symbols": ticker, "start": start, "end": end,
                  "limit": 50, "sort": "asc"}
        if token:
            params["page_token"] = token
        req = urllib.request.Request(
            NEWS_URL + "?" + urllib.parse.urlencode(params),
            headers=_headers())
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())
        frames.append(parse_news(payload, ticker))
        token = payload.get("next_page_token")
        time.sleep(PAUSE_S)
        if not token:
            break
    if not frames:
        return pd.DataFrame(columns=["trade_date", "articles"])
    out = pd.concat(frames, ignore_index=True)
    if out.empty:
        return out
    return (out.groupby("trade_date", as_index=False)["articles"].sum()
               .sort_values("trade_date").reset_index(drop=True))


def save_counts(ticker: str, df: pd.DataFrame,
                root: str = NEWS_DIR) -> str:
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, f"{ticker}.csv")
    df.to_csv(path, index=False)
    return path


def load_news(root: str = NEWS_DIR) -> dict:
    """{ticker: DataFrame(trade_date, articles)}."""
    out = {}
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        if name.endswith(".csv"):
            out[name[:-4]] = pd.read_csv(os.path.join(root, name))
    return out


def attention_ratio(news: dict, ticker: str, trade_date: str) -> float | None:
    """Recent article rate divided by the ticker's own baseline rate.
    Point-in-time: only days strictly at or before `trade_date` count.
    None when there is not enough history to judge."""
    df = news.get(ticker)
    if df is None or df.empty:
        return None
    prior = df[df["trade_date"] <= trade_date]
    if prior.empty:
        return None
    d = date.fromisoformat(trade_date)
    recent_from = str(d - timedelta(days=RECENT_DAYS))
    base_from = str(d - timedelta(days=BASELINE_DAYS))
    recent = prior[prior["trade_date"] > recent_from]["articles"].sum()
    baseline = prior[(prior["trade_date"] > base_from)
                     & (prior["trade_date"] <= recent_from)]["articles"].sum()
    if baseline < MIN_BASELINE_ARTICLES:
        return None
    recent_rate = recent / RECENT_DAYS
    baseline_rate = baseline / (BASELINE_DAYS - RECENT_DAYS)
    if baseline_rate <= 0:
        return None
    return float(recent_rate / baseline_rate)


def quiet_attention(news: dict, ticker: str, trade_date: str,
                    max_ratio: float) -> bool:
    """H9 filter: coverage is NOT unusually elevated. Fail-closed — an
    unmeasurable ratio blocks rather than assuming quiet."""
    ratio = attention_ratio(news, ticker, trade_date)
    return ratio is not None and ratio < max_ratio


def main() -> None:
    end = date.today()
    start = end - timedelta(days=int(HISTORY_YEARS * 365.25))
    tickers = sorted(UNIVERSE)
    for t in tickers:
        try:
            df = fetch_counts(t, str(start), str(end))
            save_counts(t, df)
            total = int(df["articles"].sum()) if not df.empty else 0
            print(f"{t:<6} {len(df):>5} days, {total:>6} articles")
        except Exception as e:
            print(f"{t:<6} FAILED: {e}")
    print(f"\n{len(load_news())}/{len(tickers)} tickers on disk. "
          "Next: python -m mve.hypotheses")


if __name__ == "__main__":
    main()
