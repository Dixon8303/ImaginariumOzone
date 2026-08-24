"""Micro-account override sizing — an explicit, opt-in bypass of the
validated 1% risk / 5% notional position rules, for paper accounts too
small for those rules to ever fire.

THIS IS NOT DOCTRINE. Every backtest, walk-forward window, holdout, and
robustness figure this project has produced — the +0.117R edge, the
32bp cost break-even, the 0.42 net Sharpe — was measured with
`paper.daily.position_size()` (1% risk, 5% notional cap) as the sizing
rule. Nothing in this module has been measured. It exists because the
math is otherwise absolute: at $500 equity you cannot buy a single
share of most of this universe at 1% risk / 5% cap, let alone at $29.
The choice at that account size is not "smaller doctrine trades" — the
doctrine returns zero shares regardless of ticker or threshold — it is
"one full share, sized by cash on hand, no risk-based sizing at all" or
"no trade". This module is the first option, built only after the
operator was shown the arithmetic and explicitly chose it over leaving
the account inactive.

Three guards keep this from becoming the default:

1. FAILS CLOSED. `RS_MICRO_ACCOUNT_OVERRIDE` must be exactly "YES" or
   the mode never activates — same pattern as `RS_PAPER_ARMED` and
   `HONEYDRIP_ARMED`. Unset, misspelled, or "yes" (wrong case) all mean
   off.
2. EQUITY-GATED. Only engages below `MICRO_EQUITY_THRESHOLD`. Once the
   account is funded past it, standard `position_size()` takes back
   over automatically — there is no separate switch to remember to
   flip off.
3. TAGGED. Every trade placed under this mode is written to the ledger
   with `micro_override: True`. Anything that later reads the paper
   ledger to check performance against the backtest (a future
   walk-forward-vs-paper study, for instance) must filter these out or
   it is comparing two different sizing regimes and calling it one
   result.

What it does NOT touch: options. `paper.options_broker` and
`run_option_cycle` never import this module. A single option contract
needs ~100x this account's equity regardless of position-sizing rules
(`paper/option_costs.py`), so there is no override that makes options
reachable here — only equity shares.

Scope (§87 unchanged): fake money throughout, Alpaca paper endpoint
only. This module changes how many PAPER shares are bought; it has no
path to a live account.
"""
from __future__ import annotations

import os

# Below this, the validated 1%-risk/5%-cap sizing returns 0 shares for
# nearly the entire universe (see docs/RESEARCH_LOG.md 2026-08-23, the
# $29 affordability analysis: $500 is the minimum equity for ONE share
# of the cheapest plausible name in this universe under those rules).
# Above it, standard sizing can at least sometimes fire, so the override
# steps aside rather than fighting doctrine for control.
MICRO_EQUITY_THRESHOLD = 500.0

# Never more than one open micro-sized position at a time. Every micro
# trade already commits a large, undefined fraction of a tiny account —
# stacking several of them adds concentration without adding
# diversification, since each one is still "most of the money" alone.
MICRO_MAX_CONCURRENT = 1

ENV_VAR = "RS_MICRO_ACCOUNT_OVERRIDE"


def micro_override_armed() -> bool:
    """Fails closed: only the literal string 'YES' arms this mode."""
    return os.environ.get(ENV_VAR, "") == "YES"


def micro_override_active(equity: float) -> bool:
    """Armed AND the account is actually small enough to need it. Once
    equity crosses the threshold this returns False even if the env var
    is still set — no separate step to disable it as the account
    grows."""
    return micro_override_armed() and equity < MICRO_EQUITY_THRESHOLD


def micro_position_size(equity: float, close: float) -> int:
    """One share if it is affordable, zero otherwise. Deliberately does
    NOT apply RISK_PCT or MAX_POSITION_PCT — at this equity size those
    rules are exactly what returns zero every time; the override exists
    to skip that math for a single share, not to relax it into a
    fractional cap that still returns zero."""
    if close <= 0 or equity < close:
        return 0
    return 1


def count_open_micro_positions(ledger: dict) -> int:
    return sum(1 for rec in ledger.get("open", {}).values()
              if rec.get("micro_override"))


def micro_trade_warning(ticker: str, equity: float, close: float) -> list:
    """Lines for the report — printed every time the override actually
    places a trade, never silently."""
    frac = (close / equity) if equity > 0 else 1.0
    return [
        f"  MICRO OVERRIDE: {ticker} sized OUTSIDE validated doctrine "
        f"({ENV_VAR}=YES, equity ${equity:,.2f} < "
        f"${MICRO_EQUITY_THRESHOLD:,.0f} threshold).",
        f"    1 share at ${close:.2f} commits ~{frac:.0%} of account "
        "equity to one position — far past the 5% cap every backtest, "
        "holdout, and robustness figure in this project was measured "
        "under. This trade is not evidence about the doctrine.",
    ]


def micro_mode_banner(equity: float) -> str:
    """Printed whenever the mode is ARMED for this equity, whether or
    not a trade fires today — the mode being silently on is itself
    worth surfacing every run."""
    return (f"MICRO OVERRIDE ACTIVE — {ENV_VAR}=YES and equity "
            f"${equity:,.2f} is below the ${MICRO_EQUITY_THRESHOLD:,.0f} "
            "threshold. Entries size to 1 affordable share with NO "
            "risk-based sizing. See paper/micro_sizing.py.")
