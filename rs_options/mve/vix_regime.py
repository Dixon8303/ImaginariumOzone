"""VIX term structure — volatility regime context (H8, spec §72).

The ratio VIX / VIX3M compares near-term implied volatility to three-month.
Below 1.0 the curve is in CONTANGO (calm: the market prices more risk
further out, the normal state). At or above 1.0 it is in BACKWARDATION —
near-term fear exceeds long-term, which is the market pricing stress NOW.

Why it belongs in a momentum system: breakouts are a bet that a move
continues. Backwardation regimes are exactly when continuation breaks —
correlations converge, trends whipsaw, and the momentum crashes
documented in MARKET_THEORY happen. This is a REGIME reading, not a
signal: it never says what to buy, only whether the environment pays.

Free daily data, no API key: CBOE publishes full history as CSV, with
Yahoo's chart API as fallback. Both are fetched from the operator's
machine (this repo's cloud sessions cannot reach market-data hosts).

    python -m mve.vix_regime            # fetch/refresh, print current state
"""
from __future__ import annotations

import io
import json
import os
import urllib.request

import pandas as pd

CBOE_URL = ("https://cdn.cboe.com/api/global/us_indices/daily_prices/"
            "{symbol}_History.csv")
YAHOO_URL = ("https://query1.finance.yahoo.com/v8/finance/chart/"
             "%5E{symbol}?range=10y&interval=1d")
VIX_PATH = os.path.join("data", "vix_term_structure.csv")
UA = {"User-Agent": "Mozilla/5.0 (research; daily bars)"}

# CALIBRATE — regime boundaries, not validated optima (LAW 12).
BACKWARDATION_AT = 1.00     # ratio >= this: near-term fear exceeds 3-month
DEEP_CONTANGO_AT = 0.90     # ratio <= this: unusually calm


def _fetch_cboe(symbol: str) -> pd.DataFrame:
    req = urllib.request.Request(CBOE_URL.format(symbol=symbol), headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        df = pd.read_csv(io.BytesIO(resp.read()))
    cols = {c.strip().upper(): c for c in df.columns}
    return pd.DataFrame({
        "trade_date": pd.to_datetime(df[cols["DATE"]]).dt.date.astype(str),
        symbol.lower(): pd.to_numeric(df[cols["CLOSE"]], errors="coerce"),
    }).dropna()


def _fetch_yahoo(symbol: str) -> pd.DataFrame:
    req = urllib.request.Request(YAHOO_URL.format(symbol=symbol), headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read())
    result = payload["chart"]["result"][0]
    closes = result["indicators"]["quote"][0]["close"]
    return pd.DataFrame({
        "trade_date": pd.to_datetime(result["timestamp"], unit="s",
                                     utc=True).tz_convert(
            "America/New_York").date.astype(str),
        symbol.lower(): closes,
    }).dropna()


def fetch_term_structure() -> pd.DataFrame:
    """VIX and VIX3M daily closes joined on date, with the ratio.
    CBOE first (authoritative, full history), Yahoo as fallback."""
    frames = {}
    for symbol in ("VIX", "VIX3M"):
        errors = []
        for source, fn in (("cboe", _fetch_cboe), ("yahoo", _fetch_yahoo)):
            try:
                frames[symbol] = fn(symbol)
                break
            except Exception as e:                 # pragma: no cover - network
                errors.append(f"{source}: {e}")
        if symbol not in frames:
            raise SystemExit(f"Could not fetch {symbol} — " + "; ".join(errors))
    df = frames["VIX"].merge(frames["VIX3M"], on="trade_date", how="inner")
    df["ratio"] = df["vix"] / df["vix3m"]
    return df.sort_values("trade_date").reset_index(drop=True)


def save_term_structure(df: pd.DataFrame, path: str = VIX_PATH) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    return path


def load_term_structure(path: str = VIX_PATH) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame(columns=["trade_date", "vix", "vix3m", "ratio"])
    return pd.read_csv(path)


def ratio_on(vix: pd.DataFrame, trade_date: str) -> float | None:
    """Point-in-time ratio: the most recent reading AT OR BEFORE the date.
    None when no reading exists yet — callers must fail closed, never
    assume a calm regime from missing data."""
    if vix.empty:
        return None
    prior = vix[vix["trade_date"] <= trade_date]
    if prior.empty:
        return None
    value = prior["ratio"].iloc[-1]
    return None if pd.isna(value) else float(value)


def regime_label(ratio: float | None) -> str:
    if ratio is None:
        return "UNKNOWN"
    if ratio >= BACKWARDATION_AT:
        return "BACKWARDATION"
    if ratio <= DEEP_CONTANGO_AT:
        return "DEEP_CONTANGO"
    return "CONTANGO"


def calm_regime(vix: pd.DataFrame, trade_date: str,
                max_ratio: float = BACKWARDATION_AT) -> bool:
    """H8 filter: the term structure is below `max_ratio` on this date.
    Fail-closed — an unknown regime blocks, matching how the 200-day
    filter treats insufficient history."""
    ratio = ratio_on(vix, trade_date)
    return ratio is not None and ratio < max_ratio


def summary(vix: pd.DataFrame) -> str:
    if vix.empty:
        return "No VIX data. Run: python -m mve.vix_regime"
    last = vix.iloc[-1]
    ratio = float(last["ratio"])
    lines = [f"VIX TERM STRUCTURE — as of {last['trade_date']}",
             f"  VIX {float(last['vix']):.2f} / VIX3M {float(last['vix3m']):.2f}"
             f"  ratio {ratio:.3f}  -> {regime_label(ratio)}", ""]
    recent = vix.tail(252)
    if len(recent) > 20:
        share = (recent["ratio"] >= BACKWARDATION_AT).mean()
        lines.append(f"  backwardation on {share:.0%} of the last "
                     f"{len(recent)} sessions")
    lines += ["", "Regime context only — H8 is untested until "
              "`python -m mve.hypotheses` judges it (LAW 12/20)."]
    return "\n".join(lines)


if __name__ == "__main__":
    df = fetch_term_structure()
    path = save_term_structure(df)
    print(f"{len(df)} sessions -> {path}\n")
    print(summary(df))
