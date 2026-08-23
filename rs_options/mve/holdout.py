"""Virgin-data holdout (H20, §72) — the two survivors, on untouched years.

The deep backfill created an imbalance that makes every round-5 verdict
weaker than it looks. TRAIN grew from 61 trades to 478. TEST grew from
47 to 48 — because TEST_START is 2025-01-01 and the calendar, not the
data, decides how much lives after it. So every "test confirms" verdict
in that report still rests on ~48 trades, and that same 48-trade window
has now been consulted across rounds 3, 4, 5, 6, H18 and H19. Repeatedly
looking at one small window is how a test set stops being a test set.

Meanwhile 2006-2020 arrived with the backfill and went straight into
TRAIN. It has never been used to judge anything. That makes it the only
genuinely virgin data in the project — roughly 600 trades that no
verdict, threshold, or filter has ever seen.

What is tested here, and nothing else:

1. The §32 opportunity score. Written into the spec before any market
   data existed, so 2006-2020 is out-of-sample in the strictest sense.
2. The H15a 2% gap cancellation. Its threshold was picked while looking
   at 2021-2026, so these years are out-of-sample for it.

Deliberately NOT tested: everything else. A sweep here would burn the
one clean sample the project has on the same multiple-comparisons
problem that makes the main report hard to read. Two pre-specified
candidates, two verdicts, no shopping.

A caveat that must travel with the numbers: 2006-2020 is not a neutral
sample. It contains 2008 and 2020, so it is harder than the years the
doctrine was built on. A candidate that survives here has survived
something real; one that fails MIGHT be regime-specific rather than
false. Failure is evidence, not proof.

    python -m mve.holdout
"""
from __future__ import annotations

from .backtest import DATA_ROOT, run_backtest
from .hypotheses import GAP_BUCKETS, gap_buckets, total_r
from .setups import rs02_entry_ok
from .store import DataStore

SETUP = "RS-02"

# Everything before the window used as TRAIN in every prior verdict.
# Prior rounds trained on <= 2024-12-31 and tested on >= 2025-01-01, so
# 2021-2024 is contaminated and 2025+ is over-consulted. Only these
# years are untouched.
HOLDOUT_END = "2020-12-31"

GAP_LIMIT = 0.02        # H15a, exactly as tested — not re-tuned here


def run_holdout(store: DataStore) -> dict:
    doctrine = lambda t, b, s: rs02_entry_ok(b)          # noqa: E731
    base = run_backtest(store, end=HOLDOUT_END, active=(SETUP,),
                        entry_filter=doctrine)
    gapped = run_backtest(store, end=HOLDOUT_END, active=(SETUP,),
                          entry_filter=doctrine, max_gap_pct=GAP_LIMIT)
    return {"baseline": base.per_setup().get(SETUP),
            "score": base.per_score(),
            "gap_filtered": gapped.per_setup().get(SETUP),
            "gap_dose": gap_buckets(base),
            "thin_stops": base.thin_stop_signals,
            "quarantined": len(base.suspect_trades)}


def _fmt(s) -> str:
    if s is None:
        return "n=  0  exp=   n/a  totR=   n/a"
    return (f"n={s['trades']:>4} exp={s['expectancy_r']:+.3f}R "
            f"wr={s['win_rate']:.0%} totR={total_r(s):+8.2f}")


def summary(results: dict) -> str:
    base = results["baseline"]
    lines = [
        "VIRGIN-DATA HOLDOUT — two candidates, untouched years (H20, §72)",
        f"holdout window: start of history .. {HOLDOUT_END}",
        "",
        "Why this exists: the deep backfill grew TRAIN 8x and left TEST at",
        "~48 trades, and that same window has been consulted across six",
        "rounds. These years arrived with the backfill, went straight into",
        "TRAIN, and have never judged anything. Two pre-specified",
        "candidates are tested here. Nothing else — a sweep would spend",
        "the clean sample on the same problem it exists to escape.",
        "",
        f"BASELINE_DOCTRINE  {_fmt(base)}",
    ]
    if results["thin_stops"] or results["quarantined"]:
        lines.append(f"  (data guards: {results['thin_stops']} thin-stop "
                     f"signals skipped, {results['quarantined']} trades "
                     "quarantined)")

    lines += ["",
              "CANDIDATE 1 — the §32 opportunity score.",
              "  Pre-registered in the spec before any market data existed,",
              "  so these years are out-of-sample in the strictest sense.",
              "  It must RISE with the score to be worth sizing by."]
    for bucket, s in results["score"].items():
        thin = "   (thin)" if s["trades"] < 10 else ""
        lines.append(f"    score {bucket:<4} n={s['trades']:>4} "
                     f"exp={s['expectancy_r']:+.3f}R{thin}")
    empty = {"trades": 0, "expectancy_r": 0.0}
    ordered = [results["score"].get(k, empty) for k in ("<=7", "8", "9", "10")]
    solid = [s for s in ordered if s["trades"] >= 10]
    if len(solid) >= 2:
        rising = all(b["expectancy_r"] > a["expectancy_r"]
                     for a, b in zip(solid, solid[1:]))
        top, bottom = solid[-1], solid[0]
        lines.append(
            f"    verdict: {'RISES' if rising else 'DOES NOT RISE'} across "
            f"the {len(solid)} buckets with >=10 trades "
            f"({bottom['expectancy_r']:+.3f}R -> "
            f"{top['expectancy_r']:+.3f}R)")
    else:
        lines.append("    verdict: INCONCLUSIVE (too few populated buckets)")

    gap = results["gap_filtered"]
    lines += ["",
              f"CANDIDATE 2 — H15a, cancel fills gapping > {GAP_LIMIT:.0%}.",
              "  Its threshold was chosen while looking at 2021-2026, so",
              "  these years are out-of-sample for it.",
              f"    filtered   {_fmt(gap)}"]
    if base and gap:
        d_exp = gap["expectancy_r"] - base["expectancy_r"]
        d_tot = total_r(gap) - total_r(base)
        lines.append(f"    vs baseline: expectancy {d_exp:+.3f}R, "
                     f"total {d_tot:+.2f}R over "
                     f"{base['trades'] - gap['trades']} cancelled fills")
        lines.append(f"    verdict: {'CONFIRMS' if d_exp > 0 and d_tot > 0 else 'DOES NOT CONFIRM'} "
                     "(needs BOTH expectancy and total to improve — a rule "
                     "that lifts the average by deleting winners is the H5 "
                     "failure)")
    lines += ["", "  gap dose-response on virgin data:"]
    for row in results["gap_dose"]:
        thin = "   (thin)" if row["trades"] < 10 else ""
        lines.append(f"    {row['label']:<16} n={row['trades']:>4} "
                     f"exp={row['expectancy_r']:+.3f}R "
                     f"totR={row['total_r']:+8.2f}{thin}")
    lines.append("    The pre-registered shape was a STEADY decline. A cliff "
                 "at the top bucket only is a threshold effect, which is a "
                 "different claim — say so rather than accepting it as the "
                 "one that was registered.")

    lines += ["",
              "READING IT: these years include 2008 and 2020 and are harder",
              "than the ones the doctrine was built on. Surviving here is",
              "strong evidence. Failing here MIGHT mean regime-specific",
              "rather than false — failure is evidence, not proof.",
              "",
              "LAW 12/20: this is the project's only untouched sample. Once",
              "it has been consulted it is no longer virgin, so it is spent",
              "on these two candidates and not re-used for shopping."]
    return "\n".join(lines)


if __name__ == "__main__":
    store = DataStore(DATA_ROOT)
    if not store.tickers():
        raise SystemExit("No data. Run: python -m mve.backfill --years 20")
    from .report import save_and_print
    save_and_print("holdout", summary(run_holdout(store)))
