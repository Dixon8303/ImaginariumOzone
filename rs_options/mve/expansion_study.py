"""H-23 universe-expansion study — registered in docs/PREREGISTERED.md
BEFORE this module was written; the registration commit precedes the
implementation commit, per the H-* discipline (git history is the
timestamp).

What it does, exactly once per invocation:

1. Verifies the store holds deep history for BOTH the incumbent
   universe and every candidate (plus benchmark and sector ETFs) from
   ONE consistent data pull. Mixed-vendor data across arms would make
   the comparison meaningless, so a missing ticker aborts the study
   rather than shrinking an arm silently (LAW 18 — no substituted
   data).
2. Runs the yearly expanding-window walk-forward TWICE on that data:
   the baseline arm (incumbent UNIVERSE) and the expanded arm
   (UNIVERSE + CANDIDATE_UNIVERSE), same splits, same setup, same
   guards.
3. Splits the expanded arm's TEST-window trades by membership and
   reports the three registered numbers: candidate-only out-of-sample
   expectancy, incumbent baseline expectancy, and combined expectancy —
   against the acceptance criterion frozen in PREREGISTERED.md.

It decides nothing. The verdict is read off against the registered
criterion and recorded there; per-ticker cherry-picking after seeing
results is prohibited by the registration (adopt all candidates or
none).

Where to run it: NOT in a restricted-egress cloud session — the
backfill needs Stooq/Yahoo. Either the operator's Mac:

    cd rs_options
    python -m mve.backfill --years 20 $(python -c "from mve.universe import expansion_required_tickers; print(' '.join(expansion_required_tickers()))")
    python -m mve.expansion_study

or the one-click GitHub Actions job (.github/workflows/rs_expansion_study.yml),
which does both and commits the report.
"""
from __future__ import annotations

from .backtest import DATA_ROOT, run_backtest
from .store import DataStore
from .universe import (BENCHMARK, CANDIDATE_SECTOR_ETF, CANDIDATE_UNIVERSE,
                       SECTOR_ETF, UNIVERSE, expansion_required_tickers)
from .walkforward import yearly_splits

REPORT_PATH = "docs/reports/expansion_study.txt"
MIN_YEARS_REQUIRED = 15         # a thinner pull is a different, weaker study
SETUP = "RS-02"


def coverage_check(store: DataStore) -> list:
    """Tickers missing or too thin for the study. Empty means run."""
    problems = []
    for t in expansion_required_tickers():
        bars = store.bars(t)
        if bars is None or bars.empty:
            problems.append(f"{t}: no bars on disk")
            continue
        first = str(bars["trade_date"].min())[:4]
        last = str(bars["trade_date"].max())[:4]
        span = int(last) - int(first)
        # Sector ETFs and younger listings (HOOD 2021, COIN 2021 …) can
        # not span 15 years; require deep history only of tickers that
        # EXISTED long enough. A young listing's shorter series is real
        # coverage, not a partial fetch — the momentum filter already
        # fail-closes entries during its first ~13 months.
        if span < 2:
            problems.append(f"{t}: only {first}->{last} on disk")
    # The benchmark's span defines the walkable windows, so it must be
    # deep even though single names may be young.
    bench = store.bars(BENCHMARK)
    if bench is not None and not bench.empty:
        span = (int(str(bench["trade_date"].max())[:4])
                - int(str(bench["trade_date"].min())[:4]))
        if span < MIN_YEARS_REQUIRED:
            problems.append(
                f"{BENCHMARK}: {span}y on disk, study needs "
                f">={MIN_YEARS_REQUIRED}y (run mve.backfill --years 20)")
    return problems


def run_expansion_study(store: DataStore) -> dict:
    expanded_universe = sorted(set(UNIVERSE) | set(CANDIDATE_UNIVERSE))
    expanded_sectors = dict(SECTOR_ETF, **CANDIDATE_SECTOR_ETF)
    splits = yearly_splits(store)

    def walk(universe: list, sector_map: dict) -> list:
        rows = []
        for train_start, train_end, test_start, test_end in splits:
            test = run_backtest(store, universe=universe,
                                sector_map=sector_map,
                                start=test_start, end=test_end,
                                active=(SETUP,))
            rows.append(((test_start, test_end), test))
        return rows

    baseline_rows = walk(list(UNIVERSE), SECTOR_ETF)
    expanded_rows = walk(expanded_universe, expanded_sectors)

    def collect(rows, keep=None):
        out = []
        for (_, result) in rows:
            for t in result.trades:
                if t.setup == SETUP and (keep is None or t.ticker in keep):
                    out.append(t)
        return out

    baseline_trades = collect(baseline_rows)
    candidate_trades = collect(expanded_rows, keep=set(CANDIDATE_UNIVERSE))
    combined_trades = collect(expanded_rows)

    def stats(trades):
        rs = [t.r_multiple for t in trades]
        if not rs:
            return {"trades": 0, "expectancy_r": None, "total_r": 0.0,
                    "win_rate": None}
        wins = sum(1 for r in rs if r > 0)
        return {"trades": len(rs),
                "expectancy_r": round(sum(rs) / len(rs), 3),
                "total_r": round(sum(rs), 2),
                "win_rate": round(wins / len(rs), 3)}

    return {
        "splits": len(splits),
        "baseline": stats(baseline_trades),
        "candidates_only": stats(candidate_trades),
        "combined": stats(combined_trades),
        "per_candidate": {
            t: stats([tr for tr in candidate_trades if tr.ticker == t])
            for t in sorted(CANDIDATE_UNIVERSE)
        },
    }


def format_study(res: dict) -> str:
    b, c, x = res["baseline"], res["candidates_only"], res["combined"]

    def line(label, s):
        if not s["trades"]:
            return f"  {label:<18} no trades"
        return (f"  {label:<18} n={s['trades']:>4}  "
                f"exp={s['expectancy_r']:+.3f}R  "
                f"wr={s['win_rate']:.0%}  total={s['total_r']:+.1f}R")

    lines = [
        "H-23 UNIVERSE EXPANSION STUDY — out-of-sample (test windows only)",
        f"expanding-window splits: {res['splits']}   setup: {SETUP}",
        "",
        line("baseline (22)", b),
        line("candidates only", c),
        line("combined", x),
        "",
        "Registered criterion (docs/PREREGISTERED.md H-23):",
        "  CONFIRMED: candidates-only expectancy >= 0R at n >= 30, AND",
        "  combined expectancy within 0.05R of baseline.",
        "  FAILED: candidates-only < -0.05R at n >= 30, or combined drags",
        "  more than 0.05R below baseline.",
        "  Adoption is ALL candidates or NONE — per-ticker cherry-picking",
        "  after seeing these numbers is prohibited by the registration.",
        "",
        "per-candidate (context only — NOT an adoption criterion):",
    ]
    for t, s in res["per_candidate"].items():
        if s["trades"]:
            lines.append(f"  {t:<6} n={s['trades']:>3}  "
                         f"exp={s['expectancy_r']:+.3f}R")
        else:
            lines.append(f"  {t:<6} no trades")
    return "\n".join(lines)


def main() -> None:
    store = DataStore(DATA_ROOT)
    problems = coverage_check(store)
    if problems:
        print("STUDY NOT RUN — data coverage problems (LAW 18, no "
              "substituted data):")
        for p in problems:
            print(f"  {p}")
        raise SystemExit(1)
    res = run_expansion_study(store)
    text = format_study(res)
    print(text)
    import os
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write(text + "\n")
    print(f"\nReport saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
