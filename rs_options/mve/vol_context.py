"""Volatility context — IV Rank tracking + the "volatility box" soft gate.

Sosnoff-style principle adapted for a LONG-premium engine: high IV Rank
means premium is rich, which is a headwind when *buying* options. So the
gate penalizes entries into rich IV instead of rewarding them. (Premium
selling in high IV is a different structure family and stays prohibited
until short-structure margin adapters are validated — spec §8.)

Fail-open by design at the soft-gate level, fail-honest in telemetry:
with insufficient history the gate applies NO penalty and labels itself
"uncalibrated" — it never guesses. Activates automatically as EOD chain
snapshots accumulate. All thresholds CALIBRATE (spec §23, §34, §72
Experiment I).
"""
from __future__ import annotations

import os

import pandas as pd

# CALIBRATE — research placeholders, not validated values
IV_HISTORY_WINDOW = 252        # trailing sessions for rank/percentile
MIN_SESSIONS = 20              # below this the gate is inactive ("uncalibrated")
RICH_IV_RANK = 60.0            # rank above this → +1 penalty (rich premium)
EXTREME_IV_RANK = 80.0         # rank above this → +2 penalty (§34 "Extreme IV")
ATM_DELTA_BAND = (0.40, 0.60)  # calls considered "at the money" for the proxy
ATM_DTE_BAND = (14, 60)        # preferred tenor for the ATM IV proxy


def atm_iv_from_chain(chain: pd.DataFrame) -> float | None:
    """Daily ATM IV proxy: median IV of near-the-money calls in the
    preferred tenor; falls back to all calls if the band is empty."""
    if chain is None or chain.empty:
        return None
    calls = chain[chain["right"] == "call"]
    if calls.empty:
        return None
    band = calls[calls["delta"].between(*ATM_DELTA_BAND)]
    if "dte" in calls.columns:
        tenor = band[band["dte"].between(*ATM_DTE_BAND)]
        if not tenor.empty:
            band = tenor
    if band.empty:
        band = calls
    return float(band["iv"].median())


class IVHistory:
    """Per-underlying daily ATM-IV series, parquet-backed, idempotent."""

    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def record(self, underlying: str, trade_date: str, atm_iv: float) -> None:
        path = self._path(underlying)
        row = pd.DataFrame([{"trade_date": trade_date, "atm_iv": float(atm_iv)}])
        if os.path.exists(path):
            row = pd.concat([pd.read_parquet(path), row])
        row = (row.drop_duplicates(subset=["trade_date"], keep="last")
                  .sort_values("trade_date"))
        row.to_parquet(path, index=False)

    def series(self, underlying: str, before: str | None = None) -> pd.Series:
        """ATM IV series, oldest first. `before` (exclusive) keeps the
        computation point-in-time — today's own reading never ranks itself."""
        path = self._path(underlying)
        if not os.path.exists(path):
            return pd.Series(dtype=float)
        df = pd.read_parquet(path)
        if before:
            df = df[df["trade_date"] < before]
        return df.sort_values("trade_date")["atm_iv"].tail(IV_HISTORY_WINDOW)

    def _path(self, underlying: str) -> str:
        return os.path.join(self.root, f"{underlying}.parquet")


def iv_rank(history: pd.Series, current: float) -> float | None:
    """(current − min) / (max − min) over the trailing window, in percent.
    None when history is too short — the gate must not guess (LAW 18)."""
    if len(history) < MIN_SESSIONS:
        return None
    lo, hi = float(history.min()), float(history.max())
    if hi <= lo:
        return 50.0
    return max(0.0, min(100.0, 100.0 * (current - lo) / (hi - lo)))


def iv_percentile(history: pd.Series, current: float) -> float | None:
    """Share of trailing sessions with IV below current, in percent.
    Stored alongside rank — they are not interchangeable (spec §23)."""
    if len(history) < MIN_SESSIONS:
        return None
    return 100.0 * float((history < current).sum()) / len(history)


def volatility_penalty(rank: float | None) -> tuple:
    """The volatility-box soft gate for long premium (§34).

    Returns (penalty, label). Uncalibrated → (0, "uncalibrated"): no
    penalty, honest label, activates automatically as history accumulates.
    """
    if rank is None:
        return 0, "uncalibrated"
    if rank >= EXTREME_IV_RANK:
        return 2, "extreme_iv"
    if rank >= RICH_IV_RANK:
        return 1, "rich_iv"
    return 0, "normal_iv"
