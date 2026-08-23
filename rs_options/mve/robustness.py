"""Robustness suite (H21, §72) — is the edge one lucky path, and does it
survive its own trading costs?

Two genuine gaps, both identified by an outside dossier and both real:

**Costs were never charged.** Every number this project has produced is
GROSS. No spread, no slippage, no commission. At an edge of +0.117R per
trade that omission is not cosmetic: a cost of 0.01R per round trip is
8.5% of the edge, and 0.05R would be 43% of it. `cost_sensitivity`
re-runs the doctrine at a range of costs and reports where the edge
reaches zero — the break-even is the number that matters, because it
says how much execution quality the strategy can afford to lose.

**The equity curve is a single path.** A max drawdown of -25.6R is what
happened once, in the order it happened. It is not "the" drawdown; it is
one sample from a distribution nobody has looked at. `bootstrap`
resamples the realised trades many times and reports the distribution of
outcomes. If the median bootstrap drawdown is far worse than the
historical one, the historical sequence was kind.

Also added: **Sharpe**, because expectancy-per-trade says nothing about
the ride. Computed from the R series and annualised by trade frequency;
since R scales linearly with risk-per-trade, the Sharpe of the R series
equals the Sharpe of the account returns.

What bootstrap does NOT do, stated plainly so the output is not
over-read: resampling trades independently destroys any serial
correlation. If losses genuinely cluster (they do in trend systems), the
real drawdown distribution is WORSE than the bootstrap's. Treat the
bootstrap drawdown as a floor on the risk, not a ceiling.

    python -m mve.robustness
"""
from __future__ import annotations

import random

from .backtest import DATA_ROOT, _max_drawdown, run_backtest
from .holdout import HOLDOUT_END
from .setups import MAX_ENTRY_GAP, rs02_entry_ok
from .store import DataStore

SETUP = "RS-02"
SEED = 20260823           # fixed: a robustness check must reproduce
ITERATIONS = 2000

# Round-trip cost in basis points of price. The doctrine trades liquid
# large caps commission-free, so this is spread plus slippage — a few
# bps is realistic, and the higher rungs exist to find the break-even.
COST_LADDER_BPS = (0.0, 2.0, 5.0, 10.0, 20.0, 50.0)

# Liquid large caps, commission-free, filled in the opening auction.
# Used for the NET headline figures — gross is the anchor, not the
# answer, and quoting only gross is how a thin edge looks comfortable.
REALISTIC_BPS = 5.0


def sharpe(rs: list, trades_per_year: float) -> float | None:
    """Annualised Sharpe of an R series. None when undefined."""
    n = len(rs)
    if n < 2 or trades_per_year <= 0:
        return None
    mean = sum(rs) / n
    var = sum((r - mean) ** 2 for r in rs) / (n - 1)
    if var <= 0:
        return None
    return (mean / var ** 0.5) * (trades_per_year ** 0.5)


def bootstrap(rs: list, iterations: int = ITERATIONS,
              seed: int = SEED) -> dict:
    """Resample the trade sequence WITH replacement and report the
    distribution of total R and max drawdown. Answers: how much of the
    recorded result was the order things happened in?"""
    n = len(rs)
    if n < 10:
        return {}
    rng = random.Random(seed)
    totals, drawdowns = [], []
    for _ in range(iterations):
        path = [rs[rng.randrange(n)] for _ in range(n)]
        totals.append(sum(path))
        drawdowns.append(_max_drawdown(path))
    totals.sort()
    drawdowns.sort()

    def pct(seq, p):
        return seq[min(len(seq) - 1, int(len(seq) * p))]

    return {
        "iterations": iterations,
        # The distribution is unreadable without the value it is meant
        # to contextualise. Printing them together is what turns "the
        # median path drew -12.8R" into "the path we actually got sat
        # at the Nth percentile of luck".
        "observed_total": round(sum(rs), 2),
        "observed_dd": round(_max_drawdown(rs), 2),
        "total_p05": round(pct(totals, 0.05), 2),
        "total_p50": round(pct(totals, 0.50), 2),
        "total_p95": round(pct(totals, 0.95), 2),
        "losing_paths": round(sum(1 for t in totals if t <= 0) / len(totals), 3),
        # drawdowns are negative; the WORST is the smallest number, so
        # the 5th percentile is the bad tail.
        "dd_p05": round(pct(drawdowns, 0.05), 2),
        "dd_p50": round(pct(drawdowns, 0.50), 2),
    }


def cost_sensitivity(store: DataStore, ladder=COST_LADDER_BPS,
                     end: str = HOLDOUT_END) -> list:
    """Doctrine expectancy at each cost level. The break-even cost is
    the strategy's execution budget."""
    doctrine = lambda t, b, s: rs02_entry_ok(b)          # noqa: E731
    rows = []
    for bps in ladder:
        res = run_backtest(store, end=end, active=(SETUP,),
                           entry_filter=doctrine,
                           max_gap_pct=MAX_ENTRY_GAP, cost_bps=bps)
        s = res.per_setup().get(SETUP)
        rows.append({"cost_bps": bps,
                     "trades": s["trades"] if s else 0,
                     "expectancy_r": s["expectancy_r"] if s else 0.0,
                     "total_r": round(s["trades"] * s["expectancy_r"], 2)
                     if s else 0.0,
                     "rs": [t.r_multiple for t in res.trades
                            if t.setup == SETUP]})
    return rows


def break_even_bps(rows: list) -> float | None:
    """Linear interpolation to where expectancy crosses zero."""
    for a, b in zip(rows, rows[1:]):
        if a["expectancy_r"] > 0 >= b["expectancy_r"]:
            span = a["expectancy_r"] - b["expectancy_r"]
            if span <= 0:
                return b["cost_bps"]
            frac = a["expectancy_r"] / span
            return round(a["cost_bps"]
                         + frac * (b["cost_bps"] - a["cost_bps"]), 1)
    return None


def run_robustness(store: DataStore) -> dict:
    rows = cost_sensitivity(store)
    gross = rows[0]
    years = 15.0                     # holdout spans ~2006-2020
    per_year = gross["trades"] / years if years else 0.0
    net = next((r for r in rows if r["cost_bps"] == REALISTIC_BPS), gross)
    return {"costs": rows,
            "break_even_bps": break_even_bps(rows),
            "trades_per_year": round(per_year, 1),
            "sharpe_gross": sharpe(gross["rs"], per_year),
            "sharpe_net": sharpe(net["rs"], per_year),
            "net_bps": net["cost_bps"],
            "net_expectancy": net["expectancy_r"],
            "bootstrap": bootstrap(gross["rs"])}


def summary(r: dict) -> str:
    lines = [
        "ROBUSTNESS SUITE — costs and path-dependence (H21, §72)",
        f"window: start of history .. {HOLDOUT_END} | doctrine + H15a",
        "",
        "COST SENSITIVITY — every number this project produced before now",
        "was GROSS. Costs are charged where they land: you pay up at entry",
        "(which also widens 1R) and receive less at exit.",
        f"  {'cost':>8}  {'trades':>7}  {'expectancy':>11}  {'total R':>9}",
    ]
    for row in r["costs"]:
        lines.append(f"  {row['cost_bps']:>6.0f}bp  {row['trades']:>7}  "
                     f"{row['expectancy_r']:>+10.3f}R  "
                     f"{row['total_r']:>+8.2f}")
    be = r.get("break_even_bps")
    lines.append("")
    if be is not None:
        lines += [f"  BREAK-EVEN: the edge reaches zero at ~{be:.0f} bps "
                  "round-trip.",
                  "  That is the execution budget. Liquid large caps trade "
                  "commission-free at a few bps, so the doctrine has room — "
                  "but it is not unlimited, and it is why H15a (which is "
                  "purely an execution rule) mattered more than any "
                  "predictive filter tested."]
    else:
        lines.append("  BREAK-EVEN: not reached on this ladder — extend it "
                     "before concluding the edge is cost-proof.")

    s, sn = r.get("sharpe_gross"), r.get("sharpe_net")
    lines += ["",
              "SHARPE — expectancy says nothing about the ride."]
    if s is None:
        lines.append("  not computable on this sample")
    else:
        lines.append(f"  annualised {s:.2f} at {r['trades_per_year']} "
                     "trades/year (GROSS)")
        if sn is not None:
            lines.append(f"  annualised {sn:.2f} NET at "
                         f"{r['net_bps']:.0f}bp — expectancy "
                         f"{r['net_expectancy']:+.3f}R. This is the "
                         "honest headline; gross is the anchor, not the "
                         "answer.")
        lines.append("  For scale: 0.5 is a common minimum screen, 1.0 is "
                     "good, and anything above 2 on a retail daily-bar "
                     "system should be assumed wrong until proven.")

    b = r.get("bootstrap") or {}
    if b:
        lines += ["",
                  f"BOOTSTRAP — {b['iterations']:,} resampled orderings of the "
                  "SAME trades.",
                  "The recorded equity curve is one path. This is the "
                  "distribution it was drawn from.",
                  f"  total R      5th {b['total_p05']:+.2f}   "
                  f"median {b['total_p50']:+.2f}   "
                  f"95th {b['total_p95']:+.2f}"
                  f"   [observed {b['observed_total']:+.2f}]",
                  f"  max drawdown 5th {b['dd_p05']:+.2f}   "
                  f"median {b['dd_p50']:+.2f}"
                  f"                  [observed {b['observed_dd']:+.2f}]",
                  f"  paths ending at or below zero: {b['losing_paths']:.1%}",
                  "",
                  "  READ THIS CORRECTLY: resampling independently destroys",
                  "  serial correlation. If losses cluster in reality — and",
                  "  in trend-following they do — the true drawdown",
                  "  distribution is WORSE than the figures above. Treat the",
                  "  bootstrap drawdown as a FLOOR on the risk, never a cap."]

    lines += ["",
              "LAW 12/20: costs and path-risk change what the SAME edge is "
              "worth; they do not create or destroy one. Nothing here is a "
              "filter and nothing here is adopted."]
    return "\n".join(lines)


if __name__ == "__main__":
    store = DataStore(DATA_ROOT)
    if not store.tickers():
        raise SystemExit("No data. Run: python -m mve.backfill --years 20")
    from .report import save_and_print
    save_and_print("robustness", summary(run_robustness(store)))
