"""Option scenario pricing. Spec §6.

Black-Scholes theoretical values are estimates and are labeled as such
(spec §6). The grid answers one question: what is the worst modeled loss
per contract if the trade reaches invalidation under stress?
"""
from __future__ import annotations

import math

from .config import ScenarioConfig
from .models import OptionQuote, Right, ScenarioResult, TradeCandidate

_MIN_T = 1.0 / (365.0 * 24.0)   # one hour, in years
_MIN_IV = 0.01


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(right: Right, s: float, k: float, t_years: float,
             sigma: float, r: float = 0.04) -> float:
    """Black-Scholes European price (model estimate)."""
    if s <= 0 or k <= 0:
        raise ValueError("non-positive underlying or strike")
    t = max(t_years, 0.0)
    if t == 0.0 or sigma <= 0.0:
        intrinsic = s - k if right is Right.CALL else k - s
        return max(intrinsic, 0.0)
    sq = sigma * math.sqrt(t)
    d1 = (math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / sq
    d2 = d1 - sq
    if right is Right.CALL:
        return s * norm_cdf(d1) - k * math.exp(-r * t) * norm_cdf(d2)
    return k * math.exp(-r * t) * norm_cdf(-d2) - s * norm_cdf(-d1)


def bs_delta(right: Right, s: float, k: float, t_years: float,
             sigma: float, r: float = 0.04) -> float:
    t = max(t_years, _MIN_T)
    sq = sigma * math.sqrt(t)
    d1 = (math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / sq
    return norm_cdf(d1) if right is Right.CALL else norm_cdf(d1) - 1.0


def scenario_grid(candidate: TradeCandidate, cfg: ScenarioConfig) -> list:
    """Spec §6: Base + Stress A/B/C/D, priced at invalidation.

    Long-premium positions only (baseline strategy, spec §84).
    Returns list[ScenarioResult]; PnL excludes slippage/fees, which the
    sizing layer adds per §7.
    """
    q: OptionQuote = candidate.option
    entry = q.mid + cfg.entry_spread_fraction * q.half_spread

    hold_days = candidate.expected_hold_minutes / (60.0 * cfg.trading_hours_per_day)
    t_base = max((q.dte_days - hold_days) / 365.0, _MIN_T)
    t_overrun = max(
        (q.dte_days - hold_days * cfg.extra_time_decay_mult) / 365.0, _MIN_T
    )

    s_inv = candidate.invalidation_price
    # Adverse overshoot direction depends on position side.
    if q.right is Right.CALL:
        s_stress = s_inv * (1.0 - cfg.invalidation_overshoot_pct)
    else:
        s_stress = s_inv * (1.0 + cfg.invalidation_overshoot_pct)

    iv_adverse = max(q.iv - cfg.adverse_iv_points, _MIN_IV)
    r = cfg.risk_free_rate

    def result(name: str, s: float, iv: float, t: float,
               exit_frac: float, widen: float = 1.0) -> ScenarioResult:
        model = bs_price(q.right, s, q.strike, t, iv, r)
        exit_premium = max(model - exit_frac * widen * q.half_spread, 0.0)
        pnl = (exit_premium - entry) * q.multiplier
        return ScenarioResult(name, s, iv, t, exit_premium, pnl)

    return [
        result("BASE", s_inv, q.iv, t_base, cfg.exit_spread_fraction),
        result("STRESS_A_SLIPPAGE", s_stress, q.iv, t_base, cfg.exit_spread_fraction),
        result("STRESS_B_IV_ADVERSE", s_inv, iv_adverse, t_base, cfg.exit_spread_fraction),
        result("STRESS_C_TIME_DECAY", s_inv, q.iv, t_overrun, cfg.exit_spread_fraction),
        result("STRESS_D_LIQUIDITY", s_inv, q.iv, t_base, 1.0, cfg.spread_widen_mult),
    ]


def worst_case(scenarios: list) -> ScenarioResult:
    return min(scenarios, key=lambda s: s.pnl_per_contract)
