"""Hierarchical relative strength features (spec §13-§16).

Daily-bar bootstrap. All windows are CALIBRATE research parameters and
must be versioned/tested before any production meaning is attached
(§15 "The exact feature definition must be versioned and tested").
"""
from __future__ import annotations

import pandas as pd

RETURN_WINDOW = 10          # CALIBRATE — RS measurement window (bars)
BETA_WINDOW = 60            # CALIBRATE — rolling beta estimation window
PERSISTENCE_LOOKBACK = 20   # CALIBRATE — windows sampled for persistence
PERSISTENCE_STEP = 5        # CALIBRATE — sub-window length


def window_return(close: pd.Series, window: int = RETURN_WINDOW) -> float:
    if len(close) < window + 1:
        return 0.0
    return float(close.iloc[-1] / close.iloc[-(window + 1)] - 1.0)


def rolling_beta(stock_close: pd.Series, bench_close: pd.Series,
                 window: int = BETA_WINDOW) -> float:
    n = min(len(stock_close), len(bench_close))
    if n < window + 1:
        return 1.0
    sr = stock_close.iloc[-n:].pct_change().dropna().iloc[-window:]
    br = bench_close.iloc[-n:].pct_change().dropna().iloc[-window:]
    m = min(len(sr), len(br))
    sr, br = sr.iloc[-m:].reset_index(drop=True), br.iloc[-m:].reset_index(drop=True)
    var = float(br.var())
    if var == 0.0 or m < 10:
        return 1.0
    return float(sr.cov(br) / var)


def rs_persistence(stock_close: pd.Series, bench_close: pd.Series,
                   step: int = PERSISTENCE_STEP,
                   lookback: int = PERSISTENCE_LOOKBACK) -> float:
    """Share of trailing `step`-bar windows where RS_market > 0 (§15)."""
    n = min(len(stock_close), len(bench_close))
    if n < step + 2:
        return 0.0
    wins = 0
    total = 0
    for end in range(n - 1, max(step, n - 1 - lookback), -1):
        s0, s1 = stock_close.iloc[end - step], stock_close.iloc[end]
        b0, b1 = bench_close.iloc[end - step], bench_close.iloc[end]
        if s0 <= 0 or b0 <= 0:
            continue
        total += 1
        if (s1 / s0 - 1.0) > (b1 / b0 - 1.0):
            wins += 1
    return wins / total if total else 0.0


def compute_features(stock: pd.DataFrame, bench: pd.DataFrame,
                     sector: pd.DataFrame | None = None) -> dict:
    """Feature dict from daily bars (oldest first, canonical store schema)."""
    sc, bc = stock["close"], bench["close"]
    beta = rolling_beta(sc, bc)
    stock_ret = window_return(sc)
    bench_ret = window_return(bc)
    features = {
        "stock_return": stock_ret,
        "bench_return": bench_ret,
        "rs_market": stock_ret - bench_ret,
        "beta": beta,
        "rs_beta_adjusted": stock_ret - beta * bench_ret,
        "rs_persistence": rs_persistence(sc, bc),
        "rel_volume": _relative_volume(stock),
    }
    if sector is not None and len(sector):
        sector_ret = window_return(sector["close"])
        features["sector_return"] = sector_ret
        features["rs_sector"] = stock_ret - sector_ret
    else:
        features["sector_return"] = None
        features["rs_sector"] = None
    return features


def _relative_volume(stock: pd.DataFrame, window: int = 20) -> float:
    vol = stock["volume"]
    if len(vol) < window + 1:
        return 1.0
    avg = float(vol.iloc[-(window + 1):-1].mean())
    return float(vol.iloc[-1]) / avg if avg > 0 else 1.0
