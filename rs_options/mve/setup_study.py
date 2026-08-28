"""H-24 / H-25 setup study — registered in docs/PREREGISTERED.md
BEFORE the detectors or this module existed; the registration commit
precedes the implementation commit (git history is the timestamp).

Runs the yearly expanding-window walk-forward, TEST windows only, for
each setup under study, on the tradeable UNIVERSE at run time, with the
H15a entry cap applied exactly as the registrations froze it. Judges
each setup against the frozen criterion:

  CONFIRMED (adoption-eligible): aggregate OOS expectancy >= 0R at
    n >= 50 closed trades, AND expectancy positive in at least half of
    the judged test windows (a window is judged when it holds >= 10
    trades).
  FAILED: aggregate < 0R at n >= 50, or fewer than half of judged
    windows positive.
  INCONCLUSIVE: below n = 50 — and also when n >= 50 but NO window
    reaches 10 trades (the breadth clause is then unjudgeable; frozen
    prose did not anticipate that corner, so it resolves toward no
    verdict rather than a convenient one).

Also reports, per the H-25 registration's overlap commitment, how many
of a setup's trades share a (ticker, signal date) with an RS-02 trade
over the same windows — measured on FILLED trades (the backtester
records tickered signal-dates only for fills; noted as an
implementation reading in PREREGISTERED.md).

Costs: judged GROSS (consistent with every prior verdict), with net
expectancy at REALISTIC_BPS and a linear break-even estimate reported
alongside.

Confirmation makes a setup adoption-ELIGIBLE. Activation into
ACTIVE_SETUPS is a separate operator decision — one live setup at a
time — and nothing in this module touches the live scanner.

Run where the bar vendors are reachable (operator Mac, or the
rs_setup_study Actions job):

    python -m mve.backfill --years 20
    python -m mve.setup_study
"""
from __future__ import annotations

from .backtest import DATA_ROOT, run_backtest
from .expansion_study import coverage_check
from .robustness import REALISTIC_BPS
from .setups import MAX_ENTRY_GAP
from .store import DataStore
from .universe import UNIVERSE
from .walkforward import yearly_splits

SETUPS_UNDER_STUDY = ("H-24", "H-25")
BASELINE_SETUP = "RS-02"                # overlap reference
MIN_TRADES = 50                         # frozen criterion sample floor
MIN_WINDOW_TRADES = 10                  # a window must hold this many to count
REPORT_PATH = "docs/reports/setup_study.txt"


def collect_windows(store: DataStore, setup: str, splits: list,
                    cost_bps: float = 0.0) -> list:
    """[(window_label, [Trade, ...]), ...] over TEST windows only."""
    out = []
    for _, _, test_start, test_end in splits:
        result = run_backtest(store, start=test_start, end=test_end,
                              active=(setup,), max_gap_pct=MAX_ENTRY_GAP,
                              cost_bps=cost_bps)
        trades = [t for t in result.trades if t.setup == setup]
        out.append((f"{test_start[:4]}", trades))
    return out


def judge(windows: list) -> dict:
    """The frozen criterion, as a pure function of per-window trades."""
    all_trades = [t for _, trades in windows for t in trades]
    n = len(all_trades)
    agg = (sum(t.r_multiple for t in all_trades) / n) if n else None
    judged = [(label, trades) for label, trades in windows
              if len(trades) >= MIN_WINDOW_TRADES]
    positive = sum(1 for _, trades in judged
                   if sum(t.r_multiple for t in trades) / len(trades) > 0)
    if n < MIN_TRADES:
        verdict = "INCONCLUSIVE"
        reason = f"n={n} < {MIN_TRADES} — no verdict, per the registration"
    elif not judged:
        verdict = "INCONCLUSIVE"
        reason = (f"n={n} but no single window holds "
                  f">={MIN_WINDOW_TRADES} trades — the breadth clause is "
                  "unjudgeable (resolved toward no verdict)")
    elif agg >= 0 and positive * 2 >= len(judged):
        verdict = "CONFIRMED"
        reason = (f"aggregate {agg:+.3f}R at n={n}, positive in "
                  f"{positive}/{len(judged)} judged windows")
    else:
        verdict = "FAILED"
        reason = (f"aggregate {agg:+.3f}R at n={n}, positive in "
                  f"{positive}/{len(judged)} judged windows")
    wins = sum(1 for t in all_trades if t.r_multiple > 0)
    return {"n": n, "expectancy_r": round(agg, 3) if agg is not None else None,
            "win_rate": round(wins / n, 3) if n else None,
            "total_r": round(sum(t.r_multiple for t in all_trades), 2),
            "judged_windows": len(judged), "positive_windows": positive,
            "verdict": verdict, "reason": reason}


def overlap_with(base_windows: list, setup_windows: list) -> dict:
    """Share of a setup's trades whose (ticker, signal_date) an RS-02
    trade also carries — re-timed RS-02 exposure, not diversification."""
    base = {(t.ticker, t.signal_date)
            for _, trades in base_windows for t in trades}
    mine = [(t.ticker, t.signal_date)
            for _, trades in setup_windows for t in trades]
    if not mine:
        return {"trades": 0, "overlapping": 0, "share": None}
    hits = sum(1 for key in mine if key in base)
    return {"trades": len(mine), "overlapping": hits,
            "share": round(hits / len(mine), 3)}


def linear_break_even(gross: float | None, net: float | None,
                      bps: float) -> float | None:
    """Break-even cost by linear extrapolation from two ladder points.
    An ESTIMATE, labeled as such in the report. None when undefined or
    when costs did not reduce expectancy (extrapolating would mislead)."""
    if gross is None or net is None or gross <= 0 or net >= gross:
        return None
    return round(bps * gross / (gross - net), 1)


def run_setup_study(store: DataStore) -> dict:
    splits = yearly_splits(store)
    base_windows = collect_windows(store, BASELINE_SETUP, splits)
    out = {"splits": len(splits), "universe": len(UNIVERSE), "setups": {}}
    for setup in SETUPS_UNDER_STUDY:
        gross_windows = collect_windows(store, setup, splits)
        net_windows = collect_windows(store, setup, splits,
                                      cost_bps=REALISTIC_BPS)
        verdict = judge(gross_windows)
        net_verdict = judge(net_windows)
        out["setups"][setup] = {
            "windows": [(label, len(trades),
                         round(sum(t.r_multiple for t in trades)
                               / len(trades), 3) if trades else None)
                        for label, trades in gross_windows],
            "gross": verdict,
            "net_expectancy_r": net_verdict["expectancy_r"],
            "net_bps": REALISTIC_BPS,
            "break_even_bps_est": linear_break_even(
                verdict["expectancy_r"], net_verdict["expectancy_r"],
                REALISTIC_BPS),
            "overlap_rs02": overlap_with(base_windows, gross_windows),
        }
    return out


def format_study(res: dict) -> str:
    lines = [
        "H-24 / H-25 SETUP STUDY — out-of-sample (test windows only)",
        f"expanding-window splits: {res['splits']}   "
        f"universe: {res['universe']} names   H15a entry cap applied",
        "",
        "Frozen criterion (docs/PREREGISTERED.md): CONFIRMED needs "
        f"aggregate >= 0R at n >= {MIN_TRADES} AND positive expectancy in "
        f">= half of judged (>= {MIN_WINDOW_TRADES}-trade) windows. "
        "CONFIRMED means adoption-ELIGIBLE; activation is a separate "
        "operator decision, one live setup at a time.",
    ]
    for setup, s in res["setups"].items():
        g = s["gross"]
        lines += ["", f"── {setup} " + "─" * 40]
        if g["n"]:
            lines.append(f"  n={g['n']}  exp={g['expectancy_r']:+.3f}R  "
                         f"wr={g['win_rate']:.0%}  total={g['total_r']:+.1f}R"
                         f"  (GROSS)")
            net = s["net_expectancy_r"]
            if net is not None:
                be = s["break_even_bps_est"]
                lines.append(f"  net at {s['net_bps']:.0f}bp: {net:+.3f}R"
                             + (f"   break-even ~{be:.0f}bp (linear "
                                "estimate)" if be is not None else ""))
        else:
            lines.append("  no trades in any test window")
        lines.append(f"  VERDICT: {g['verdict']} — {g['reason']}")
        ov = s["overlap_rs02"]
        if ov["share"] is not None:
            lines.append(
                f"  overlap with RS-02 (filled-trade ticker+signal-date): "
                f"{ov['overlapping']}/{ov['trades']} = {ov['share']:.0%} — "
                + ("mostly re-timed RS-02 exposure, not diversification"
                   if ov["share"] > 0.5 else
                   "largely distinct from RS-02's trades"))
        lines.append("  per test window (year, n, expectancy):")
        row = "   "
        for label, n, exp in s["windows"]:
            cell = f" {label}:{n}" + (f"@{exp:+.2f}" if exp is not None
                                      else "")
            if len(row) + len(cell) > 74:
                lines.append(row)
                row = "   "
            row += cell
        lines.append(row)
    lines += ["", "A verdict here is read against the registration and "
              "recorded there; per-window numbers are context, not "
              "criteria (LAW 20)."]
    return "\n".join(lines)


def main() -> None:
    store = DataStore(DATA_ROOT)
    problems = coverage_check(store)
    if problems:
        print("STUDY NOT RUN — data coverage problems (LAW 18):")
        for p in problems:
            print(f"  {p}")
        raise SystemExit(1)
    res = run_setup_study(store)
    text = format_study(res)
    print(text)
    import os
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write(text + "\n")
    print(f"\nReport saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
