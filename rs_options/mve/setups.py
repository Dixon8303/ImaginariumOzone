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


def detect_all(stock: pd.DataFrame, features: dict) -> list:
    hits = []
    for detector in (detect_rs01, detect_rs02):
        c = detector(stock, features)
        if c:
            hits.append(c)
    return hits
