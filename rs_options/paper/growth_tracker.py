"""Account growth tracking — reporting only, never sizing (§72 adjacent).

Operator asked for a "growth/recovery module" to take a small paper
account to a larger one in daily increments. Two corrections were made
before writing this, both recorded in `docs/RESEARCH_LOG.md`
2026-08-24:

1. **"Daily" does not match this system.** RS-02 fires roughly 25
   signals a year across the whole universe — about one trade every 10
   trading days. On most days the honest report is "no signal, no
   trade, no change." This module records an equity snapshot every run
   so the resulting curve shows that shape honestly: long flat
   stretches punctuated by moves, not a smooth daily ramp.
2. **"Recovery" was scoped down to tracking, not resizing.** The
   operator explicitly chose the non-martingale option: position sizing
   never increases after a loss to make it back faster. This module
   therefore touches NOTHING about how much is risked per trade — it
   only reads the account's equity history and reports on it. All
   sizing logic lives in `paper.daily.position_size` (doctrine) and
   `paper.micro_sizing` (the sub-$500 override); neither is imported
   here for writing, only equity is read.

What "growth" means here, precisely: the sum of realized P&L on closed
trades plus unrealized marks on open ones, exactly what the broker
reports as account equity. There is no compounding logic to write —
`position_size()` and `micro_position_size()` already read equity fresh
from the broker every run, so a winning trade automatically enlarges
the next trade's size and a account that has not grown automatically
does not. This module's only job is to make that growth (or its
absence) visible over time.

    python -m paper.growth_tracker    # print the recorded history
"""
from __future__ import annotations

import json
import os
from datetime import date

from .micro_sizing import MICRO_EQUITY_THRESHOLD

GROWTH_LOG_PATH = os.path.join("docs", "reports", "paper_growth.jsonl")


def record_equity(today: str, equity: float,
                  path: str | None = None) -> bool:
    """Append one snapshot. Skips a duplicate for the same date so
    re-running the same day (e.g. --preopen then the evening run) does
    not inflate the history with same-day repeats. Returns whether a
    row was written."""
    path = path or GROWTH_LOG_PATH
    history = load_equity_history(path)
    if history and history[-1]["date"] == today:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps({"date": today, "equity": round(equity, 2)},
                           sort_keys=True) + "\n")
    return True


def load_equity_history(path: str | None = None) -> list:
    path = path or GROWTH_LOG_PATH
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue          # a torn line is skipped, not fatal
    return out


def _days_between(a: str, b: str) -> int:
    return max(0, (date.fromisoformat(b) - date.fromisoformat(a)).days)


def growth_summary(history: list) -> dict:
    """Statistics computed from the recorded snapshots ONLY — no ledger
    trades are needed, since equity already nets every closed trade."""
    if len(history) < 2:
        return {}
    start, current = history[0], history[-1]
    delta = current["equity"] - start["equity"]
    pct = (delta / start["equity"]) if start["equity"] else 0.0
    moved = sum(1 for a, b in zip(history, history[1:])
               if b["equity"] != a["equity"])
    peak = max(h["equity"] for h in history)
    trough = min(h["equity"] for h in history)
    return {
        "start_date": start["date"], "start_equity": start["equity"],
        "current_date": current["date"], "current_equity": current["equity"],
        "delta": round(delta, 2), "pct": pct,
        "days_elapsed": _days_between(start["date"], current["date"]),
        "snapshots": len(history),
        "days_with_a_change": moved,
        "days_flat": len(history) - 1 - moved,
        "peak_equity": peak, "trough_equity": trough,
        "to_doctrine_threshold": round(
            max(0.0, MICRO_EQUITY_THRESHOLD - current["equity"]), 2),
    }


def format_growth(summary: dict) -> str:
    if not summary:
        return ("ACCOUNT GROWTH: fewer than 2 recorded snapshots — "
                "nothing to summarize yet. Growth is tracked automatically "
                "each run; check back after a few sessions.")
    s = summary
    lines = [
        "ACCOUNT GROWTH — reporting only; sizing is unaffected by this "
        "module (docs/RESEARCH_LOG.md 2026-08-24).",
        f"  {s['start_date']}  ${s['start_equity']:,.2f}  ->  "
        f"{s['current_date']}  ${s['current_equity']:,.2f}"
        f"   ({s['delta']:+,.2f}, {s['pct']:+.1%})",
        f"  over {s['days_elapsed']} calendar days, {s['snapshots']} "
        "recorded sessions: "
        f"{s['days_with_a_change']} with a change, {s['days_flat']} flat.",
        f"  range so far: ${s['trough_equity']:,.2f} (low) to "
        f"${s['peak_equity']:,.2f} (high).",
    ]
    if s["to_doctrine_threshold"] > 0:
        lines.append(
            f"  ${s['to_doctrine_threshold']:,.2f} to "
            f"${MICRO_EQUITY_THRESHOLD:,.0f} — the equity level where "
            "position sizing reverts from the micro override to "
            "validated doctrine sizing automatically.")
    else:
        lines.append(
            f"  Equity is at or above ${MICRO_EQUITY_THRESHOLD:,.0f} — "
            "doctrine sizing is active; the micro override is dormant.")
    lines.append(
        "  Most sessions will show no change: this system trades ~25 "
        "times a year across the universe, roughly once every 10 "
        "trading days. Flat stretches are the expected shape, not a "
        "malfunction.")
    return "\n".join(lines)


def main() -> None:
    history = load_equity_history()
    if not history:
        raise SystemExit(
            "No growth history recorded yet. It accumulates automatically "
            "on each evening run:\n  python -m paper.daily")
    print(format_growth(growth_summary(history)))
    print()
    print(f"{'date':<12}{'equity':>12}")
    for row in history:
        print(f"{row['date']:<12}${row['equity']:>10,.2f}")


if __name__ == "__main__":
    main()
