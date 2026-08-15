"""Baseline setup detectors: RS-01 and RS-02 only (spec §17, §87 MVE).

Every numeric threshold is CALIBRATE — a research hypothesis, not a
validated production value (LAW 12). Detectors return a candidate dict or
None; the session runner converts hits into TradeCandidates.
"""
from __future__ import annotations

import pandas as pd

# RS-01 — MARKET WEAKNESS ABSORPTION (CALIBRATE)
RS01_BENCH_MAX_RETURN = -0.01   # benchmark down ≥1% over the RS window
RS01_MIN_RS = 0.02              # stock ≥2% stronger than benchmark
RS01_STRUCTURE_SMA = 20         # stock must hold above this SMA

# RS-02 — RS BREAKOUT (CALIBRATE)
RS02_MIN_PERSISTENCE = 0.65     # share of positive RS windows
RS02_BREAKOUT_LOOKBACK = 20     # prior-high window (excludes latest bar)
RS02_MIN_REL_VOLUME = 1.2       # volume expansion vs 20d average
RS02_BENCH_MIN_RETURN = -0.02   # market not in freefall

INVALIDATION_LOOKBACK = 5       # swing-low window for the stop (CALIBRATE)

# Setups the LIVE scanner runs (spec §60 Level 2 — SETUP KILL).
# RS-01 disabled 2026-08-14: first 5y real-data backtest showed negative
# expectancy (-0.145R over 234 trades, max DD -47R). It remains available
# to the backtester for re-parameterization; re-enable only after a
# revised version shows positive OUT-OF-SAMPLE expectancy (LAW 20).
# RS-02 backtested +0.25R over 160 trades in-sample — stays active
# pending walk-forward validation.
ACTIVE_SETUPS = ("RS-02",)

# H2b regime filter — ADOPTED 2026-08-15 by operator decision after the
# §72 hypothesis study: requiring the stock above its own 200-day SMA
# improved RS-02 on TRAIN (+0.415R vs +0.346R, n=95) AND TEST (+0.239R
# vs +0.229R, n=53); every other variant (52wk-high, SPY-regime) was
# noise. Applies to the LIVE doctrine path only — research tools that
# pass `active` explicitly get unfiltered signals, so future studies
# keep a clean CONTROL. Fail-closed: with fewer than REGIME_SMA_LEN bars
# there is no established regime, so no entry.
REGIME_SMA_LEN = 200


def above_sma(bars: pd.DataFrame, length: int = REGIME_SMA_LEN) -> bool:
    if len(bars) < length:
        return False
    sma = float(bars["close"].iloc[-length:].mean())
    return float(bars["close"].iloc[-1]) > sma


ENTRY_FILTERS = {"RS-02": above_sma}


def detect_rs01(stock: pd.DataFrame, features: dict) -> dict | None:
    close = stock["close"]
    if len(close) < RS01_STRUCTURE_SMA + 1:
        return None
    bench_weak = features["bench_return"] <= RS01_BENCH_MAX_RETURN
    stock_stronger = features["rs_market"] >= RS01_MIN_RS
    sector_ok = features["rs_sector"] is None or features["rs_sector"] > -0.01
    sma = float(close.iloc[-RS01_STRUCTURE_SMA:].mean())
    holds_structure = float(close.iloc[-1]) > sma
    volume_ok = features["rel_volume"] >= 1.0

    if not (bench_weak and stock_stronger and sector_ok
            and holds_structure and volume_ok):
        return None
    return _candidate(stock, features, "RS-01",
                      rationale=(f"benchmark {features['bench_return']:+.1%} while "
                                 f"stock RS {features['rs_market']:+.1%}, "
                                 f"holding above SMA{RS01_STRUCTURE_SMA}"))


def detect_rs02(stock: pd.DataFrame, features: dict) -> dict | None:
    close = stock["close"]
    if len(close) < RS02_BREAKOUT_LOOKBACK + 2:
        return None
    persistent = features["rs_persistence"] >= RS02_MIN_PERSISTENCE
    prior_high = float(stock["high"].iloc[-(RS02_BREAKOUT_LOOKBACK + 1):-1].max())
    breakout = float(close.iloc[-1]) > prior_high
    volume_expands = features["rel_volume"] >= RS02_MIN_REL_VOLUME
    market_ok = features["bench_return"] >= RS02_BENCH_MIN_RETURN
    sector_ok = features["rs_sector"] is None or features["rs_sector"] > -0.01

    if not (persistent and breakout and volume_expands and market_ok and sector_ok):
        return None
    return _candidate(stock, features, "RS-02",
                      rationale=(f"RS persistence {features['rs_persistence']:.0%}, "
                                 f"close {float(close.iloc[-1]):.2f} > "
                                 f"{RS02_BREAKOUT_LOOKBACK}d high {prior_high:.2f}, "
                                 f"rel volume {features['rel_volume']:.1f}x"))


def opportunity_score(features: dict, setup_id: str) -> int:
    """0-10 interpretability score (§32) — CALIBRATE rubric.

    Macro alignment is scored by the session runner (it owns the calendar);
    here macro contributes its 0-2 only when no block exists, which the
    runner enforces upstream. Bootstrap rubric:
      regime proxy (bench not collapsing)          0-2
      technical structure (detector already gated) 2
      relative strength magnitude                  0-2
      RS persistence                               0-2
      liquidity/volume                             0-1
      options structure placeholder                1
    """
    score = 0
    score += 2 if features["bench_return"] > -0.03 else 1
    score += 2                                     # structure: detector-gated
    rs = features["rs_beta_adjusted"]
    score += 2 if rs >= 0.03 else (1 if rs >= 0.01 else 0)
    p = features["rs_persistence"]
    score += 2 if p >= 0.75 else (1 if p >= 0.55 else 0)
    score += 1 if features["rel_volume"] >= 1.2 else 0
    score += 1                                     # long-premium structure fits
    return min(score, 10)


def _candidate(stock: pd.DataFrame, features: dict, setup_id: str,
               rationale: str) -> dict:
    close = float(stock["close"].iloc[-1])
    swing_low = float(stock["low"].iloc[-INVALIDATION_LOOKBACK:].min())
    invalidation = min(swing_low, close * 0.99)
    return {
        "setup_id": setup_id,
        "close": close,
        "invalidation_price": round(invalidation, 2),
        "opportunity_score": opportunity_score(features, setup_id),
        "rationale": rationale,
        "features": features,
    }


DETECTORS = {"RS-01": detect_rs01, "RS-02": detect_rs02}


def detect_all(stock: pd.DataFrame, features: dict,
               active: tuple | None = None) -> list:
    """Run detectors. Default: ACTIVE_SETUPS only (the live doctrine),
    with adopted ENTRY_FILTERS applied as setup entry conditions.
    Research tools (backtester, hypothesis studies) pass `active`
    explicitly and get raw signals — their studies apply filters
    themselves against an unfiltered CONTROL."""
    live = active is None
    hits = []
    for setup_id in (active if active is not None else ACTIVE_SETUPS):
        c = DETECTORS[setup_id](stock, features)
        if not c:
            continue
        if live and setup_id in ENTRY_FILTERS and not ENTRY_FILTERS[setup_id](stock):
            continue
        hits.append(c)
    return hits
