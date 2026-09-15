"""H-26 universe-expansion study — registered in docs/PREREGISTERED.md
on 2026-09-12, BEFORE this module was written; the registration commit
precedes the implementation commit, per the H-* discipline (git history
is the timestamp).

What is different from the H-23 study, and why this is a separate
module rather than a parameter on that one: H-23 measured a single
setup (RS-02), because that was the whole live doctrine at the time.
The live book now runs two (RS-02 and H-25). This study therefore
POOLS the candidate trades from every setup in ACTIVE_SETUPS and judges
the registered criterion on the pooled population — that is what the
live scanner will actually trade on these names. Per-setup splits are
computed and printed as CONTEXT, never as criteria (LAW 20): a cohort
that passes pooled but fails on one setup alone is still a PASS, and
the reverse is still a FAIL.

Re-running H-23's module post-adoption would measure something else
entirely (its "baseline" meant the pre-adoption 22-name universe), so
that module is left alone.

What this does, exactly once per invocation:

1. Verifies the store holds deep history for BOTH the live universe
   and every H-26 candidate (plus benchmark and all sector ETFs,
   including the three new ones — XLB, XLU, XLRE) from ONE consistent
   pull. A missing ticker aborts the study rather than silently
   shrinking an arm (LAW 18).
2. Runs the yearly expanding-window walk-forward TWICE on that data:
   the baseline arm (live UNIVERSE) and the expanded arm (UNIVERSE +
   H26_CANDIDATE_UNIVERSE), same splits, same setups, same guards.
3. Splits the expanded arm's TEST-window trades by membership and
   reports the three registered numbers against the frozen criterion.

It decides nothing. The verdict is read off against the registration
and recorded there; per-ticker cherry-picking after seeing results is
prohibited (adopt all ten or none).

Where to run it: NOT in a restricted-egress cloud session — the
backfill needs Stooq/Yahoo. Either the operator's Mac:

    cd rs_options
    python -m mve.backfill --years 20 $(python -c "from mve.universe import h26_required_tickers; print(' '.join(h26_required_tickers()))")
    python -m mve.h26_study

or the one-click GitHub Actions job (.github/workflows/rs_h26_study.yml),
which does both and commits the report.
"""
from __future__ import annotations

from .backtest import DATA_ROOT, run_backtest
from .setups import ACTIVE_SETUPS, MAX_ENTRY_GAP
from .store import DataStore
from .universe import (BENCHMARK, H26_CANDIDATE_SECTOR_ETF,
                       H26_CANDIDATE_UNIVERSE, SECTOR_ETF, UNIVERSE,
                       h26_required_tickers)
from .walkforward import yearly_splits

REPORT_PATH = "docs/reports/h26_study.txt"
MIN_YEARS_REQUIRED = 15         # a thinner pull is a different study
MIN_TRADES = 50                 # registered bar — stricter than H-23's 30
MAX_COMBINED_DRAG = 0.05        # registered: combined >= baseline - 0.05R


def coverage_check(store: DataStore) -> list:
    """Tickers missing or too thin for the study. Empty means run."""
    problems = []
    for t in h26_required_tickers():
        bars = store.bars(t)
        if bars is None or bars.empty:
            problems.append(f"{t}: no bars on disk")
            continue
        first = str(bars["trade_date"].min())[:4]
        last = str(bars["trade_date"].max())[:4]
        if int(last) - int(first) < 2:
            problems.append(f"{t}: only {first}->{last} on disk")
    bench = store.bars(BENCHMARK)
    if bench is not None and not bench.empty:
        span = (int(str(bench["trade_date"].max())[:4])
                - int(str(bench["trade_date"].min())[:4]))
        if span < MIN_YEARS_REQUIRED:
            problems.append(
                f"{BENCHMARK}: {span}y on disk, study needs "
                f">={MIN_YEARS_REQUIRED}y (run mve.backfill --years 20)")
    return problems


def stats(trades: list) -> dict:
    rs = [t.r_multiple for t in trades]
    if not rs:
        return {"trades": 0, "expectancy_r": None, "total_r": 0.0,
                "win_rate": None}
    wins = sum(1 for r in rs if r > 0)
    return {"trades": len(rs),
            "expectancy_r": round(sum(rs) / len(rs), 3),
            "total_r": round(sum(rs), 2),
            "win_rate": round(wins / len(rs), 3)}


def judge(candidates: dict, baseline: dict, combined: dict) -> dict:
    """The registered criterion, as a pure function of the three arms.

    CONFIRMED  candidates-only expectancy >= 0R at n >= MIN_TRADES AND
               combined >= baseline - MAX_COMBINED_DRAG
    FAILED     candidates-only < 0R at n >= MIN_TRADES, OR combined
               drags more than MAX_COMBINED_DRAG below baseline
    INCONCLUSIVE  below n = MIN_TRADES, however the numbers look
    """
    n = candidates["trades"]
    if n < MIN_TRADES:
        return {"verdict": "INCONCLUSIVE", "n": n,
                "reason": (f"{n} candidate trades, registration requires "
                           f"n >= {MIN_TRADES} for any verdict")}
    exp = candidates["expectancy_r"]
    b, x = baseline["expectancy_r"], combined["expectancy_r"]
    drag = None if (b is None or x is None) else round(b - x, 3)
    if exp < 0:
        return {"verdict": "FAILED", "n": n, "drag": drag,
                "reason": (f"candidates-only {exp:+.3f}R < 0R at n={n}")}
    if drag is not None and drag > MAX_COMBINED_DRAG:
        return {"verdict": "FAILED", "n": n, "drag": drag,
                "reason": (f"combined {x:+.3f}R drags {drag:.3f}R below "
                           f"baseline {b:+.3f}R, more than the registered "
                           f"{MAX_COMBINED_DRAG}R")}
    return {"verdict": "CONFIRMED", "n": n, "drag": drag,
            "reason": (f"candidates-only {exp:+.3f}R at n={n}, combined "
                       f"within {abs(drag or 0):.3f}R of baseline")}


def run_h26_study(store: DataStore) -> dict:
    expanded_universe = sorted(set(UNIVERSE) | set(H26_CANDIDATE_UNIVERSE))
    expanded_sectors = dict(SECTOR_ETF, **H26_CANDIDATE_SECTOR_ETF)
    splits = yearly_splits(store)

    def walk(universe: list, sector_map: dict) -> list:
        rows = []
        for _train_start, _train_end, test_start, test_end in splits:
            # ACTIVE_SETUPS, not a single setup: the criterion is
            # pooled over what the live book actually trades. The H15a
            # entry cap is part of the adopted doctrine, so it applies
            # here exactly as it does live.
            test = run_backtest(store, universe=universe,
                                sector_map=sector_map,
                                start=test_start, end=test_end,
                                active=tuple(ACTIVE_SETUPS),
                                max_gap_pct=MAX_ENTRY_GAP)
            rows.append(((test_start, test_end), test))
        return rows

    baseline_rows = walk(list(UNIVERSE), SECTOR_ETF)
    expanded_rows = walk(expanded_universe, expanded_sectors)

    def collect(rows, keep=None, setup=None):
        out = []
        for (_, result) in rows:
            for t in result.trades:
                if keep is not None and t.ticker not in keep:
                    continue
                if setup is not None and t.setup != setup:
                    continue
                out.append(t)
        return out

    cand = set(H26_CANDIDATE_UNIVERSE)
    baseline = stats(collect(baseline_rows))
    candidates = stats(collect(expanded_rows, keep=cand))
    combined = stats(collect(expanded_rows))

    return {
        "splits": len(splits),
        "setups": list(ACTIVE_SETUPS),
        "baseline": baseline,
        "candidates_only": candidates,
        "combined": combined,
        "verdict": judge(candidates, baseline, combined),
        # context only, never criteria (LAW 20)
        "per_setup": {
            s: stats(collect(expanded_rows, keep=cand, setup=s))
            for s in ACTIVE_SETUPS
        },
        "per_candidate": {
            t: stats(collect(expanded_rows, keep={t}))
            for t in sorted(H26_CANDIDATE_UNIVERSE)
        },
    }


def format_study(res: dict) -> str:
    def line(label, s):
        if not s["trades"]:
            return f"  {label:<20} no trades"
        return (f"  {label:<20} n={s['trades']:>5}  "
                f"exp={s['expectancy_r']:+.3f}R  "
                f"wr={s['win_rate']:.0%}  total={s['total_r']:+.1f}R")

    v = res["verdict"]
    lines = [
        "H-26 UNIVERSE EXPANSION STUDY — out-of-sample (test windows only)",
        f"expanding-window splits: {res['splits']}   "
        f"setups pooled: {'+'.join(res['setups'])}   "
        f"live universe: {len(UNIVERSE)} names   "
        f"candidates: {len(H26_CANDIDATE_UNIVERSE)}",
        "",
        "Frozen criterion (docs/PREREGISTERED.md H-26): CONFIRMED needs "
        f"candidates-only >= 0R at n >= {MIN_TRADES} AND combined within "
        f"{MAX_COMBINED_DRAG}R of baseline. CONFIRMED means "
        "adoption-ELIGIBLE; adoption is all ten or none, and is the "
        "operator's decision.",
        "",
        line(f"baseline ({len(UNIVERSE)})", res["baseline"]),
        line("candidates only", res["candidates_only"]),
        line("combined", res["combined"]),
        "",
        f"  VERDICT: {v['verdict']} — {v['reason']}",
        "",
        "per-setup split of the candidate trades "
        "(CONTEXT ONLY — not a criterion, LAW 20):",
    ]
    for s, st in res["per_setup"].items():
        lines.append(line(f"  {s}", st))
    lines += ["", "per-candidate (CONTEXT ONLY — per-ticker "
                  "cherry-picking is prohibited by the registration):"]
    for t, s in res["per_candidate"].items():
        if s["trades"]:
            lines.append(f"  {t:<6} n={s['trades']:>4}  "
                         f"exp={s['expectancy_r']:+.3f}R")
        else:
            lines.append(f"  {t:<6} no trades")
    lines += ["",
              "A verdict here is read against the registration and "
              "recorded there. Adoption does not follow automatically "
              "from CONFIRMED."]
    return "\n".join(lines)


def main() -> None:
    store = DataStore(DATA_ROOT)
    problems = coverage_check(store)
    if problems:
        print("H-26 study ABORTED — the data pull is incomplete "
              "(LAW 18: never study a silently shrunken arm):")
        for p in problems:
            print(f"  {p}")
        raise SystemExit(1)
    res = run_h26_study(store)
    text = format_study(res)
    with open(REPORT_PATH, "w") as f:
        f.write(text + "\n")
    print(text)
    print(f"\nwritten to {REPORT_PATH}")


if __name__ == "__main__":
    main()
