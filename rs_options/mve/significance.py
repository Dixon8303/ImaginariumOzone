"""Statistical significance of a track record — t-stats and streak math.

Adopted 2026-08-28 from an operator-supplied day-trading dossier (see
docs/RESEARCH_LOG.md for the full adopt/adapt/reject assessment). Two
METHODS survived that assessment; both are standard statistics, adopted
because they fill real gaps this project had:

1. **The t-statistic of a Sharpe ratio**: t ≈ Sharpe x sqrt(years).
   A track record is evidence in proportion to BOTH its quality and its
   length, and this one number says how much. Computed honestly it is
   sobering in both directions: the 15-year holdout at Sharpe 0.52
   earns t ≈ 2.0 — the entire 20-year evidence base is just barely
   conventionally significant — and a FORWARD track at the same Sharpe
   needs ~16 years to reach t = 2 on its own. The forward paper track's
   real jobs are therefore execution verification and DISconfirmation,
   not independent proof; anyone waiting for the live record to "prove
   the edge" is waiting for 2042.

2. **Loss-streak expectations**: at any honest win rate, long losing
   streaks are near-certain over normal samples, and knowing the number
   in advance is what separates "expected variance" from "the system
   broke." At RS-02's measured 52% win rate, over ~40 trades a 2-loss
   streak is a certainty, 3 losses ~94%, 4 losses ~70%. The streak
   probability here is computed EXACTLY (dynamic programming over run
   lengths), not by the rule-of-thumb approximation.
"""
from __future__ import annotations

import math

T_SIGNIFICANT = 2.0             # the conventional ~95% two-sided bar


def t_stat(sharpe: float | None, years: float) -> float | None:
    """t ≈ Sharpe x sqrt(years). None when Sharpe is undefined or the
    span is degenerate."""
    if sharpe is None or years <= 0:
        return None
    return sharpe * math.sqrt(years)


def years_to_t(sharpe: float | None, t: float = T_SIGNIFICANT) -> float | None:
    """Years of track record needed for a given Sharpe to reach t.
    None for undefined or non-positive Sharpe — a zero-or-negative
    Sharpe never gets there, and returning a number would lie."""
    if sharpe is None or sharpe <= 0:
        return None
    return (t / sharpe) ** 2


def p_loss_streak(win_rate: float, streak: int, n_trades: int) -> float:
    """Exact probability of at least one run of `streak` consecutive
    losses somewhere in `n_trades` independent trades at `win_rate`.

    Dynamic programming over the current consecutive-loss count; the
    run-of-k state is absorbing. Exact, so the doc examples reproduce
    to the digit (50% win rate, 100 trades: k=4 -> 0.973, k=5 -> 0.810,
    k=6 -> 0.546)."""
    if not 0.0 <= win_rate <= 1.0:
        raise ValueError("win_rate must be in [0, 1]")
    if streak < 1 or n_trades < streak:
        return 0.0
    q = 1.0 - win_rate
    probs = [1.0] + [0.0] * (streak - 1)
    hit = 0.0
    for _ in range(n_trades):
        new = [0.0] * streak
        new[0] = sum(probs) * win_rate
        for i in range(streak - 1):
            new[i + 1] += probs[i] * q
        hit += probs[streak - 1] * q
        probs = new
    return hit


def streak_table(win_rate: float, n_trades: int,
                 streaks: tuple = (2, 3, 4, 5, 6)) -> dict:
    return {k: round(p_loss_streak(win_rate, k, n_trades), 3)
            for k in streaks}


def forward_track_line(n_closed: int, win_rate: float | None = None) -> str:
    """One honest sentence for the paper report about what the forward
    sample can and cannot say. Kept blunt on purpose: a good early run
    is the most dangerous moment for discipline."""
    if n_closed < 50:
        base = (f"  significance: n={n_closed} forward trades proves "
                "nothing either way (t-stat territory starts around "
                "n=50; see mve/significance.py). The forward track's "
                "job is verifying execution matches the backtest, not "
                "re-proving the edge.")
    else:
        base = (f"  significance: n={n_closed} — enough to start "
                "comparing realized expectancy against the backtest's, "
                "still far from standalone statistical proof "
                "(a Sharpe-0.5 edge needs ~16 YEARS for t=2).")
    if win_rate is not None and n_closed >= 4:
        p4 = p_loss_streak(win_rate, 4, max(n_closed, 40))
        base += (f" Expect losing streaks: at {win_rate:.0%} wins, a "
                 f"4-loss run has ~{p4:.0%} odds over "
                 f"{max(n_closed, 40)} trades — variance, not breakage.")
    return base
