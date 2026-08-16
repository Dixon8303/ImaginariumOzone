"""Open-position exit rules (playbook "Position management", spec §39, §69).

WHY THIS MODULE EXISTS — evidence, not theory.

The operator's realized Robinhood history through 2026-08-14 (116 closing
trades on the individual account) reads:

    win rate            65%   (73 wins / 39 losses)
    average win        $21.75
    average loss       $56.14   -> win/loss ratio 0.39
    net realized      -$625.37
    net EXCLUDING positions held to expiration:  +$292.63

Eight long-premium positions were held into expiration and settled at zero,
for -$918 combined — 147% of the entire net loss. The hit rate was never the
problem. The losses were unbounded in time: winners were cut at a third the
size of losers, and losers were held until the contract itself expired.

The exit rules below were previously prose in robinhood_copilot_playbook.md,
which meant they were advisory — a step an operator (or an agent) could skip
under pressure, which is exactly when they matter. Here they are deterministic
and testable. `evaluate_exit` is a pure function: same inputs, same verdict,
no discretion.

This module decides ONLY whether to exit. It never sizes, never picks a
contract, and never places an order. Execution stays human-confirmed (§67).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

# CALIBRATE — research thresholds, not validated optima (LAW 12).
MIN_DTE_HOLD = 5           # exit at or below this DTE; never ride the final week
GAMMA_RISK_DTE = 10        # advisory: decay accelerates below this


class ExitAction(str, Enum):
    HOLD = "HOLD"
    EXIT = "EXIT"


@dataclass(frozen=True)
class OpenPosition:
    """A live long-call position, as recorded at entry in executions.jsonl."""
    ticker: str
    contract: str
    quantity: int
    entry_price: float          # per-contract premium paid
    expiry: date
    invalidation_price: float   # underlying level that voids the setup


@dataclass(frozen=True)
class ExitVerdict:
    action: ExitAction
    reasons: tuple
    dte: int
    underlying_price: float

    @property
    def must_exit(self) -> bool:
        return self.action is ExitAction.EXIT


def evaluate_exit(position: OpenPosition, underlying_price: float,
                  as_of: date, min_dte: int = MIN_DTE_HOLD) -> ExitVerdict:
    """Decide HOLD or EXIT for one open position.

    Two independent triggers, either sufficient:

    DTE_FLOOR      at or below `min_dte` days to expiry. This is the rule the
                   -$918 of expirations violated. Time decay is not a view
                   that can come good; a long call at 0 DTE is worth zero
                   regardless of how right the thesis was.
    INVALIDATION   the underlying has broken the level that defined the
                   setup. The reason for the trade is gone, so the trade goes.

    Reasons accumulate — a position can trip both, and the caller should see
    both rather than only the first.
    """
    dte = (position.expiry - as_of).days
    reasons = []

    if dte <= min_dte:
        reasons.append(f"DTE_FLOOR: {dte}d remaining <= {min_dte}d floor")
    if underlying_price <= position.invalidation_price:
        reasons.append(
            f"INVALIDATION: underlying {underlying_price:.2f} <= "
            f"{position.invalidation_price:.2f}")

    action = ExitAction.EXIT if reasons else ExitAction.HOLD
    if not reasons and dte <= GAMMA_RISK_DTE:
        reasons.append(f"ADVISORY: {dte}d to expiry, decay accelerating")

    return ExitVerdict(action=action, reasons=tuple(reasons), dte=dte,
                       underlying_price=underlying_price)


def entry_dte_is_coherent(dte_at_entry: float, min_dte: int = MIN_DTE_HOLD,
                          min_hold_days: int = 2) -> bool:
    """Guard against entering a contract the exit rule kills immediately.

    A position opened at 7 DTE with a 5-day exit floor has two days to work.
    Anything tighter is a trade the rules close before the thesis can play
    out — pure friction. Used to sanity-check chain_select.DTE_RANGE against
    MIN_DTE_HOLD rather than letting the two drift apart silently.
    """
    return dte_at_entry - min_dte >= min_hold_days


def format_exit_report(verdicts: list) -> str:
    """Operator-facing summary of a position-management pass."""
    if not verdicts:
        return "No open positions."
    exits = [(p, v) for p, v in verdicts if v.must_exit]
    lines = [f"POSITION REVIEW — {len(verdicts)} open, {len(exits)} to exit", ""]
    for position, verdict in verdicts:
        lines.append(f"{verdict.action.value:5s} {position.contract} "
                     f"x{position.quantity}  ({verdict.dte}d, underlying "
                     f"{verdict.underlying_price:.2f})")
        for reason in verdict.reasons:
            lines.append(f"        {reason}")
    if exits:
        lines += ["", "Exits are limit-at-mid, day only (§38). "
                      "Execution requires the operator's word."]
    return "\n".join(lines)
