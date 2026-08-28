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

# Adopted RS-02 entry filters (§72 hypothesis studies). Both apply to
# the LIVE doctrine path only — research tools that pass `active`
# explicitly get unfiltered signals, so future studies keep a clean
# CONTROL. Both fail closed: insufficient history means no entry.
#
# H2b regime (ADOPTED 2026-08-15): stock above its own 200-day SMA.
#   Round-1 study: train +0.415R vs +0.346R, test +0.239R vs +0.229R.
# H4b momentum-quality (ADOPTED 2026-08-16): trailing 12-1 month return
#   >= +10% (skip the reversal-prone last month, Jegadeesh-Titman).
#   Round-2 study vs the H2b baseline: train +0.516R vs +0.415R, test
#   +0.324R vs +0.239R, with a dose-response pattern across thresholds.
REGIME_SMA_LEN = 200
MOM_LOOKBACK = 252              # 12-1 momentum window (CALIBRATE)
MOM_SKIP = 21                   # skip the last month
QUALITY_MIN_MOM = 0.10          # H4b threshold (CALIBRATE)

# H15a FILL-GAP CANCELLATION (ADOPTED 2026-08-23, operator decision).
#
# Signals fire on the close and fill at the NEXT open. If that open has
# already run more than MAX_ENTRY_GAP above the signal close, the order
# is abandoned rather than chased. This is an EXECUTION rule, not a
# prediction: the stop sits at a fixed swing low, so a gapped-up entry
# widens 1R before the trade even starts.
#
# Evidence (H20 holdout, 2006-2020 — disjoint from the 2021-2026 window
# that chose the threshold, so a genuine out-of-sample confirmation):
#   baseline n=376 +0.096R totR +36.10 | filtered n=367 +0.117R totR +42.94
#   Expectancy AND total both improved, so this is not the H5 failure of
#   raising an average by deleting winners. The 2%+ bucket was negative
#   in every window measured: -0.248R, -0.023R, -0.209R.
#
# Honest caveat: the pre-registered shape was a STEADY decline across
# gap sizes; the observed shape is a CLIFF at 2%, with moderate gaps
# fine or better. A threshold effect is a different claim from the one
# registered. Adopted on direction, disjoint-sample confirmation and
# mechanism — NOT on shape. docs/PREREGISTERED.md FWD-2 checks forward
# whether it keeps earning its place.
#
# This is the SINGLE SOURCE for the number: research variants and the
# holdout import it so live doctrine and studies cannot drift apart.
MAX_ENTRY_GAP = 0.02


def entry_limit_price(signal_close: float) -> float:
    """Highest price doctrine will pay at the open for a signal that
    closed at `signal_close`. Live orders go in as limits at this price,
    which is how the backtested cancellation is expressed to a broker."""
    return signal_close * (1.0 + MAX_ENTRY_GAP)


def fill_gap_ok(open_price: float, signal_close: float) -> bool:
    """False when the open gapped beyond doctrine's tolerance. Fails
    closed on a nonsensical close — an unknown gap is not a small one."""
    if not signal_close or signal_close <= 0:
        return False
    return open_price <= entry_limit_price(signal_close)


def above_sma(bars: pd.DataFrame, length: int = REGIME_SMA_LEN) -> bool:
    if len(bars) < length:
        return False
    sma = float(bars["close"].iloc[-length:].mean())
    return float(bars["close"].iloc[-1]) > sma


def mom_12_1(bars: pd.DataFrame) -> float | None:
    """Trailing 12-1 month return; None with insufficient history."""
    if len(bars) < MOM_LOOKBACK + 1:
        return None
    c = bars["close"]
    return float(c.iloc[-MOM_SKIP]) / float(c.iloc[-MOM_LOOKBACK]) - 1.0


def quality_mom(bars: pd.DataFrame, min_mom: float = QUALITY_MIN_MOM) -> bool:
    m = mom_12_1(bars)
    return m is not None and m > min_mom


def rs02_entry_ok(bars: pd.DataFrame) -> bool:
    """The full adopted RS-02 entry doctrine: H2b regime + H4b quality."""
    return above_sma(bars) and quality_mom(bars)


ENTRY_FILTERS = {"RS-02": rs02_entry_ok}


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


# ── H-24 / H-25 (docs/PREREGISTERED.md, registered 2026-08-28 BEFORE
#    this code existed; implemented same day — the registration commit
#    precedes this one, and dated implementation notes there record the
#    two places the frozen prose needed an exact reading). Research
#    setups: in DETECTORS for the backtester, deliberately NOT in
#    ACTIVE_SETUPS — activation is a separate operator decision that
#    only becomes available if the registered study confirms.

# H-24's one genuinely new number, frozen at registration: the break
# must have happened within this many bars before the reclaim close.
RECLAIM_WINDOW = 3


def detect_h24(stock: pd.DataFrame, features: dict) -> dict | None:
    """H-24 — failed-breakdown reclaim, long. Sellers CLOSED the stock
    below its prior 20-day low within the last RECLAIM_WINDOW bars, the
    break attracted no follow-through, and the latest bar closes back
    above the level, on normal volume, with the market not in freefall,
    in an intact long-term trend (H2b; H4b deliberately NOT applied —
    frozen choice, see the registration).

    Level reading (implementation note in PREREGISTERED.md): the 20-day
    low window ENDS before the reclaim window, because a break bar
    inside its own level window can never close below that window's
    minimum low — the level must predate the break to be breakable."""
    close, low = stock["close"], stock["low"]
    need = RS02_BREAKOUT_LOOKBACK + RECLAIM_WINDOW + 1
    if len(close) < max(need, REGIME_SMA_LEN):
        return None
    if not above_sma(stock):                       # H2b, fail-closed
        return None
    level = float(low.iloc[-need:-(RECLAIM_WINDOW + 1)].min())
    break_closes = close.iloc[-(RECLAIM_WINDOW + 1):-1]
    broke = bool((break_closes < level).any())
    reclaimed = float(close.iloc[-1]) > level
    volume_ok = features["rel_volume"] >= 1.0      # "at least normal"
    market_ok = features["bench_return"] >= RS02_BENCH_MIN_RETURN
    if not (broke and reclaimed and volume_ok and market_ok):
        return None
    return _candidate(stock, features, "H-24",
                      rationale=(f"closed below the {RS02_BREAKOUT_LOOKBACK}d "
                                 f"low {level:.2f} within {RECLAIM_WINDOW} "
                                 f"bars, reclaimed at "
                                 f"{float(close.iloc[-1]):.2f} on "
                                 f"{features['rel_volume']:.1f}x volume"))


def detect_h25(stock: pd.DataFrame, features: dict) -> dict | None:
    """H-25 — pullback-and-reclaim, long. Established trend (H2b AND
    H4b, both adopted filters verbatim), at least one of the last
    INVALIDATION_LOOKBACK bars CLOSED below its own rolling 20-day SMA
    (RS01_STRUCTURE_SMA), and the latest bar closes back above it, on
    normal volume, market not in freefall. Introduces no new numeric
    parameter — every threshold is an existing constant reused."""
    close = stock["close"]
    if len(close) < MOM_LOOKBACK + 1:              # H4b horizon, fail-closed
        return None
    if not (above_sma(stock) and quality_mom(stock)):
        return None
    sma20 = close.rolling(RS01_STRUCTURE_SMA).mean()
    pull_closes = close.iloc[-(INVALIDATION_LOOKBACK + 1):-1]
    pull_smas = sma20.iloc[-(INVALIDATION_LOOKBACK + 1):-1]
    pulled_back = bool((pull_closes < pull_smas).any())
    reclaimed = float(close.iloc[-1]) > float(sma20.iloc[-1])
    volume_ok = features["rel_volume"] >= 1.0
    market_ok = features["bench_return"] >= RS02_BENCH_MIN_RETURN
    if not (pulled_back and reclaimed and volume_ok and market_ok):
        return None
    return _candidate(stock, features, "H-25",
                      rationale=(f"pullback closed under the "
                                 f"{RS01_STRUCTURE_SMA}d SMA within "
                                 f"{INVALIDATION_LOOKBACK} bars, reclaimed "
                                 f"at {float(close.iloc[-1]):.2f} on "
                                 f"{features['rel_volume']:.1f}x volume"))


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


DETECTORS = {"RS-01": detect_rs01, "RS-02": detect_rs02,
             "H-24": detect_h24, "H-25": detect_h25}


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
