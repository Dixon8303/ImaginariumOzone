"""Volatility surface skew metrics. Spec §25.

Minimal foundational implementation: 25Δ risk reversal, 25Δ butterfly,
and percentile-based skew-state classification. Curve fitting (SVI etc.)
is a research-stage upgrade.
"""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass

from .models import SkewState


@dataclass(frozen=True)
class StrikeIV:
    delta: float     # signed: calls (0, 1), puts (-1, 0)
    iv: float


@dataclass(frozen=True)
class SurfaceMetrics:
    atm_iv: float
    rr25: float      # IV(25Δ call) − IV(25Δ put)
    bf25: float      # wing avg − ATM


def _interp_iv(points: list, target_abs_delta: float) -> float:
    """Linear interpolation of IV at |delta| within one wing."""
    pts = sorted(((abs(p.delta), p.iv) for p in points))
    if not pts:
        raise ValueError("empty wing")
    xs = [x for x, _ in pts]
    if target_abs_delta <= xs[0]:
        return pts[0][1]
    if target_abs_delta >= xs[-1]:
        return pts[-1][1]
    i = bisect_left(xs, target_abs_delta)
    (x0, y0), (x1, y1) = pts[i - 1], pts[i]
    w = (target_abs_delta - x0) / (x1 - x0)
    return y0 + w * (y1 - y0)


def skew_metrics(chain: list) -> SurfaceMetrics:
    """chain: list[StrikeIV] for one tenor, both wings."""
    calls = [p for p in chain if p.delta > 0]
    puts = [p for p in chain if p.delta < 0]
    if not calls or not puts:
        raise ValueError("need both wings to measure skew")
    iv_c25 = _interp_iv(calls, 0.25)
    iv_p25 = _interp_iv(puts, 0.25)
    atm = (_interp_iv(calls, 0.50) + _interp_iv(puts, 0.50)) / 2.0
    return SurfaceMetrics(
        atm_iv=atm,
        rr25=iv_c25 - iv_p25,
        bf25=(iv_c25 + iv_p25) / 2.0 - atm,
    )


def rr25_percentile(current_rr25: float, history: list) -> float:
    """Percentile of current RR25 against trailing history (spec: 252 sessions)."""
    if not history:
        return 50.0
    below = sum(1 for h in history if h < current_rr25)
    return 100.0 * below / len(history)


def classify_skew(current_rr25: float, history: list,
                  steep_pctile: float = 20.0,
                  extreme_pctile: float = 5.0,
                  call_skew_pctile: float = 90.0) -> SkewState:
    """Percentile thresholds are research parameters (CALIBRATE, spec §25)."""
    p = rr25_percentile(current_rr25, history)
    if p <= extreme_pctile:
        return SkewState.EXTREME_PUT_SKEW
    if p <= steep_pctile:
        return SkewState.STEEP_PUT_SKEW
    if p >= call_skew_pctile and current_rr25 > 0:
        return SkewState.CALL_SKEW
    return SkewState.NORMAL_PUT_SKEW
