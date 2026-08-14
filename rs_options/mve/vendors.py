"""Vendor adapters (spec §46 "Build vs Buy": data is bought, not built).

VendorAdapter is the seam where a real consolidated vendor (Polygon,
Theta Data, ORATS, Cboe DataShop, dxFeed) plugs in. Two bootstrap
implementations ship:

  CsvVendor        load normalized CSVs dropped into a directory
  SyntheticVendor  deterministic generated data for tests and dry runs

Both return frames in the canonical store schema.
"""
from __future__ import annotations

import math
import os
from datetime import date, timedelta

import pandas as pd

from rs_options_risk import Right, bs_delta, bs_price

from .store import BAR_COLS, CHAIN_COLS


class CsvVendor:
    """Reads `bars_*.csv` / `chains_*.csv` from a directory, canonical columns."""

    def __init__(self, incoming_dir: str):
        self.incoming_dir = incoming_dir

    def bars(self) -> pd.DataFrame:
        return self._concat("bars_", BAR_COLS)

    def chains(self) -> pd.DataFrame:
        return self._concat("chains_", CHAIN_COLS)

    def _concat(self, prefix: str, cols: list) -> pd.DataFrame:
        frames = []
        if os.path.isdir(self.incoming_dir):
            for f in sorted(os.listdir(self.incoming_dir)):
                if f.startswith(prefix) and f.endswith(".csv"):
                    frames.append(pd.read_csv(os.path.join(self.incoming_dir, f)))
        if not frames:
            return pd.DataFrame(columns=cols)
        return pd.concat(frames, ignore_index=True)[cols]


class SyntheticVendor:
    """Deterministic price paths for tests: trend + two sine components.

    Not a market model — just enough structure that RS features, setup
    detectors, and the chain selector can be exercised end-to-end.
    """

    def __init__(self, start: date, days: int = 120):
        self.start = start
        self.days = days

    def bars(self, ticker: str, base: float = 100.0, drift: float = 0.0005,
             amp: float = 0.02, phase: float = 0.0,
             vol_base: int = 1_000_000) -> pd.DataFrame:
        rows = []
        d = self.start
        added = 0
        i = 0
        while added < self.days:
            if d.weekday() < 5:                     # trading days only
                t = added
                close = base * (1 + drift) ** t * (
                    1 + amp * math.sin(t / 9.0 + phase)
                      + amp / 2 * math.sin(t / 23.0 + phase * 2))
                spread = close * 0.01
                volume = int(vol_base * (1 + 0.5 * math.sin(t / 7.0 + phase)))
                rows.append({
                    "ticker": ticker, "trade_date": str(d),
                    "open": round(close - spread / 4, 4),
                    "high": round(close + spread, 4),
                    "low": round(close - spread, 4),
                    "close": round(close, 4),
                    "volume": volume,
                })
                added += 1
            d += timedelta(days=1)
            i += 1
        return pd.DataFrame(rows, columns=BAR_COLS)

    def chain(self, underlying: str, trade_date: str, spot: float,
              iv: float = 0.30, dte_list: tuple = (7, 14, 30, 45)) -> pd.DataFrame:
        """EOD chain snapshot: calls and puts across a strike ladder, with
        Black-Scholes deltas and a fixed smile (wings +4 vol points)."""
        rows = []
        day = date.fromisoformat(trade_date)
        for dte in dte_list:
            expiry = str(day + timedelta(days=dte))
            for pct in (-0.15, -0.10, -0.05, -0.025, 0.0, 0.025, 0.05, 0.10, 0.15):
                strike = round(spot * (1 + pct), 2)
                strike_iv = iv + 0.04 * abs(pct) / 0.15
                for right in (Right.CALL, Right.PUT):
                    delta = bs_delta(right, spot, strike, dte / 365.0, strike_iv)
                    # Model-consistent quotes: BS value ± a 3% half-spread.
                    mid = max(bs_price(right, spot, strike, dte / 365.0,
                                       strike_iv), 0.05)
                    half = max(mid * 0.03, 0.01)
                    rows.append({
                        "underlying": underlying, "trade_date": trade_date,
                        "expiry": expiry, "strike": strike,
                        "right": right.value,
                        "bid": round(mid - half, 4), "ask": round(mid + half, 4),
                        "volume": 500, "open_interest": 1_000,
                        "iv": round(strike_iv, 4), "delta": round(delta, 4),
                    })
        return pd.DataFrame(rows, columns=CHAIN_COLS)
