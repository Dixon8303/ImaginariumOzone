"""Option selection from EOD chain snapshots (spec §18-§19, §27).

Long calls only (long-premium MVE, §87). Filters are CALIBRATE research
parameters; delta band is the §19 research range, not a validated optimum.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from rs_options_risk import OptionQuote, Right

# Min DTE raised 2026-08-15: the exit study moved the hold to 15 trading
# days (~21 calendar), and an option must comfortably outlive its hold
# (playbook still force-closes at DTE <= 5). Mechanical consistency, not
# a fitted parameter.
DTE_RANGE = (21, 60)          # CALIBRATE research window (§19/§24 buckets)
DELTA_RANGE = (0.40, 0.80)    # §19 initial research range
DELTA_TARGET = 0.60           # tie-break preference inside the band
MAX_SPREAD_PCT = 0.10         # §27 initial spread rule
MIN_OPEN_INTEREST = 100       # CALIBRATE
MIN_VOLUME = 10               # CALIBRATE


def select_call(chain: pd.DataFrame, as_of: str) -> OptionQuote | None:
    """Best liquid call in the research delta band, else None."""
    if chain.empty:
        return None
    df = chain[chain["right"] == Right.CALL.value].copy()
    if df.empty:
        return None

    today = date.fromisoformat(as_of)
    df["dte"] = df["expiry"].map(lambda e: (date.fromisoformat(str(e)) - today).days)
    df["mid"] = (df["bid"] + df["ask"]) / 2.0
    df["spread_pct"] = (df["ask"] - df["bid"]) / df["mid"].where(df["mid"] > 0)

    eligible = df[
        df["dte"].between(*DTE_RANGE)
        & df["delta"].between(*DELTA_RANGE)
        & (df["spread_pct"] <= MAX_SPREAD_PCT)
        & (df["open_interest"] >= MIN_OPEN_INTEREST)
        & (df["volume"] >= MIN_VOLUME)
        & (df["bid"] > 0)
    ]
    if eligible.empty:
        return None

    best = eligible.iloc[(eligible["delta"] - DELTA_TARGET).abs().argsort()].iloc[0]
    return OptionQuote(
        right=Right.CALL,
        strike=float(best["strike"]),
        dte_days=float(best["dte"]),
        bid=float(best["bid"]),
        ask=float(best["ask"]),
        iv=float(best["iv"]),
    )
