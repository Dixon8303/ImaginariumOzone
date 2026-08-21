"""Filter combinations (H18, §72) — do the tested filters interact?

The question sounds open-ended but the mechanics are narrow. Entry
filters compose by AND: a signal must pass every filter, so a
combination can only REMOVE trades from the doctrine baseline — it can
never add a trade or improve one it keeps. "Do they work better
together" therefore decomposes into three measurable questions:

1. WHAT does each filter remove? Not how many trades — WHICH trades,
   and what they were worth. Two filters can post identical aggregate
   numbers while deleting completely different trades.
2. Do filters remove the SAME trades? High overlap means a combination
   is redundant — the second filter adds nothing the first didn't
   already do. Low overlap means the combination is a genuinely new,
   stricter rule — with a smaller sample than either member.
3. For the few members with surviving mechanisms, does the pre-registered
   combination beat both members out of sample?

What this module deliberately does NOT do: search the full combination
space for a winner. Thirteen round-5 variants form 2^13 = 8192 subsets;
at a 1-in-20 luck rate that space contains ~400 "improvements" by
chance alone, and the best cell of an exhaustive search is essentially
guaranteed to be one of them. The pair sweep below exists to SHOW that
arithmetic on real data, not to shop from.

One subtlety the naive comparison misses: removing a signal can FREE
the one-position-per-ticker slot for a later signal the baseline never
took. A filtered variant can contain trades the baseline lacks. Both
directions are counted (removed and substituted-in) rather than
pretending filtering is pure subtraction.

    python -m mve.combinations      # needs news + fundamentals on disk
"""
from __future__ import annotations

from .backtest import DATA_ROOT, run_backtest
from .fundamentals import load_fundamentals
from .hypotheses import (BASELINE, GAP_VARIANTS, TEST_START, TRAIN_END,
                         build_variants, daily_signal_counts, total_r)
from .news import load_news
from .setups import rs02_entry_ok
from .store import DataStore

# One variant per hypothesis family — the pre-registered primary
# threshold. Sweeping every threshold of every family would be
# threshold-mining layered on combination-mining.
FAMILY_PRIMARY = ("H9a_quiet_news_2x", "H10_profitable",
                  "H11a_overhead_10pct", "H13a_quiet_base_40",
                  "H14a_close_top30", "H16a_max2_signals")
GAP_PRIMARY = "H15a_gap_2pct"

# The only round-5 members that were not REJECTED outright get a real
# verdict as combinations. Registered here, before the run, so the list
# cannot quietly grow after the numbers are seen (LAW 12).
PREREGISTERED = (
    ("H11a_overhead_10pct", "H15a_gap_2pct"),
)

SETUP = "RS-02"


def trade_keys(result, setup: str = SETUP) -> set:
    """A trade's identity: where and when it was entered."""
    return {(t.ticker, t.entry_date) for t in result.trades
            if t.setup == setup}


def trade_r(result, setup: str = SETUP) -> dict:
    """{(ticker, entry_date): r_multiple} for value-of-removed math."""
    return {(t.ticker, t.entry_date): t.r_multiple for t in result.trades
            if t.setup == setup}


def compose(filters: list):
    """AND-composition. Idempotent doctrine terms cost a re-check and
    keep every member exactly as it was judged solo."""
    return lambda t, b, s: all(f(t, b, s) for f in filters)


def split_members(names, variants) -> tuple:
    """(entry_filter, max_gap_pct) for a member list. Gap variants are
    fill-time cancellations, so they ride the backtester parameter
    rather than the signal-time filter."""
    fns, gap = [], None
    for name in names:
        if name in GAP_VARIANTS:
            gap = (GAP_VARIANTS[name] if gap is None
                   else min(gap, GAP_VARIANTS[name]))
        else:
            fns.append(variants[name])
    entry = compose(fns) if fns else (lambda t, b, s: rs02_entry_ok(b))
    return entry, gap


def run_windows(store, entry, gap):
    train = run_backtest(store, end=TRAIN_END, active=(SETUP,),
                         entry_filter=entry, max_gap_pct=gap)
    test = run_backtest(store, start=TEST_START, active=(SETUP,),
                        entry_filter=entry, max_gap_pct=gap)
    return train, test


def stats(train, test) -> dict:
    return {"train": train.per_setup().get(SETUP),
            "test": test.per_setup().get(SETUP),
            "keys": trade_keys(train) | trade_keys(test)}


def run_combos(store: DataStore, news: dict | None = None,
               facts: dict | None = None, sweep: bool = True,
               families: tuple = FAMILY_PRIMARY,
               prereg: tuple = PREREGISTERED) -> dict:
    if news is None:
        news = load_news()
        if not news:
            raise SystemExit("No news counts on disk. Run: python -m mve.news")
    if facts is None:
        facts = load_fundamentals()
        if not facts:
            raise SystemExit("No fundamentals on disk. "
                             "Run: python -m mve.fundamentals")

    doctrine = lambda t, b, s: rs02_entry_ok(b)          # noqa: E731
    base_train, base_test = run_windows(store, doctrine, None)
    counts = daily_signal_counts(base_train)
    counts.update(daily_signal_counts(base_test))
    variants = build_variants(news, facts, counts)

    base = stats(base_train, base_test)
    base_r = {**trade_r(base_train), **trade_r(base_test)}

    # ── what each family primary removes from the baseline ───────────
    singles = {}
    for name in tuple(families) + (GAP_PRIMARY,):
        entry, gap = split_members([name], variants)
        train, test = run_windows(store, entry, gap)
        s = stats(train, test)
        removed = base["keys"] - s["keys"]
        s["removed"] = removed
        s["removed_r"] = round(sum(base_r[k] for k in removed), 2)
        s["substituted"] = len(s["keys"] - base["keys"])
        singles[name] = s

    # ── pre-registered combinations, full verdict machinery ──────────
    combos = {}
    for members in prereg:
        entry, gap = split_members(list(members), variants)
        train, test = run_windows(store, entry, gap)
        s = stats(train, test)
        removed = base["keys"] - s["keys"]
        s["members"] = members
        s["removed"] = removed
        s["union_removed"] = set().union(
            *(singles[m]["removed"] for m in members if m in singles))
        combos["+".join(members)] = s

    # ── cross-family pair sweep (diagnostic, not verdicts) ───────────
    sweep_rows = []
    if sweep:
        pool = tuple(families) + (GAP_PRIMARY,)
        for i, a in enumerate(pool):
            for b in pool[i + 1:]:
                entry, gap = split_members([a, b], variants)
                train, test = run_windows(store, entry, gap)
                s = stats(train, test)
                sweep_rows.append({"pair": f"{a} + {b}",
                                   "train": s["train"], "test": s["test"]})

    return {"baseline": base, "singles": singles, "combos": combos,
            "sweep": sweep_rows}


def _fmt(s) -> str:
    if s is None:
        return "n=  0  exp=   n/a  totR=   n/a"
    return (f"n={s['trades']:>3} exp={s['expectancy_r']:+.3f}R "
            f"totR={total_r(s):+7.2f}")


def summary(results: dict) -> str:
    base = results["baseline"]
    bt, bs = base["train"], base["test"]
    lines = [
        "COMBINATION STUDY — do the tested filters interact? (H18, §72)",
        f"train <= {TRAIN_END} | test >= {TEST_START} | "
        f"all rows vs {BASELINE}",
        "",
        "Filters compose by AND: a combination only REMOVES trades from",
        "the baseline. It cannot add a trade or improve one it keeps —",
        "so a combination earns its keep only by removing NET-NEGATIVE",
        "trades that neither member removed alone.",
        "",
        f"{BASELINE:<24} train: {_fmt(bt)}   test: {_fmt(bs)}",
        "",
        "WHAT EACH FILTER REMOVES (vs baseline, both windows pooled):",
        "  a filter is redundant in combination exactly to the extent",
        "  it removes the same trades as its partner.",
    ]
    for name, s in results["singles"].items():
        n = len(s["removed"])
        avg = (s["removed_r"] / n) if n else 0.0
        sub = (f", substituted in {s['substituted']}"
               if s["substituted"] else "")
        lines.append(f"  {name:<22} removed {n:>3} trades worth "
                     f"{s['removed_r']:+7.2f}R ({avg:+.2f}R each){sub}")

    singles = results["singles"]
    names = list(singles)
    lines += ["", "PAIRWISE OVERLAP of removed trades (shared / union):",
              "  ~0% = the filters police different trades; combining is",
              "  a genuinely new, stricter rule with a smaller sample.",
              "  ~100% = the second filter is redundant."]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ra, rb = singles[a]["removed"], singles[b]["removed"]
            union = ra | rb
            if not union:
                continue
            shared = len(ra & rb)
            lines.append(f"  {a:<22} x {b:<22} "
                         f"{shared:>3}/{len(union):<3} "
                         f"({shared / len(union):.0%})")

    if results["combos"]:
        lines += ["", "PRE-REGISTERED COMBINATIONS (the only members not "
                      "REJECTED solo in round 5):"]
    for name, s in results["combos"].items():
        t, e = s["train"], s["test"]
        lines.append(f"  {name}")
        lines.append(f"    train: {_fmt(t)}   test: {_fmt(e)}")
        if not t or not e or t["trades"] < 20 or e["trades"] < 10:
            lines.append("    verdict: INCONCLUSIVE (insufficient trades)")
            continue
        train_up = t["expectancy_r"] > bt["expectancy_r"]
        test_up = e["expectancy_r"] > bs["expectancy_r"]
        verdict = ("ADOPT-CANDIDATE" if train_up and test_up
                   else "REJECT (train did not improve)" if not train_up
                   else "NOISE (train improved, test did not confirm)")
        lines.append(f"    verdict: {verdict}")
        dr = (total_r(bt) - total_r(t)) + (total_r(bs) - total_r(e))
        if verdict == "ADOPT-CANDIDATE" and dr > 0:
            lines.append(f"    CAUTION: total return fell {dr:+.2f}R while "
                         "the average rose — the H5 failure mode.")
        extra = len(s["removed"]) - len(s["union_removed"])
        lines.append(f"    interaction: removed {len(s['removed'])} trades; "
                     f"its members removed {len(s['union_removed'])} "
                     f"between them ({extra:+d} from interaction). "
                     "Near zero = no interaction, just both rules at once.")

    rows = results["sweep"]
    if rows:
        judged = [r for r in rows
                  if r["train"] and r["test"]
                  and r["train"]["trades"] >= 20 and r["test"]["trades"] >= 10]
        ranked = sorted(judged, key=lambda r: total_r(r["test"]),
                        reverse=True)
        lines += ["",
                  f"PAIR SWEEP — DIAGNOSTIC ONLY. {len(rows)} cross-family "
                  f"pairs tested, {len(rows) - len(judged)} below minimum "
                  "trade counts. At a 1-in-20 luck rate "
                  f"~{len(rows) * 0.05:.1f} pairs beat baseline by chance;",
                  "the best cell of a sweep is where luck concentrates. "
                  "Nothing below is adoptable from this table.",
                  "  top pairs by TEST total return:"]
        for r in ranked[:6]:
            lines.append(f"  {r['pair']}")
            lines.append(f"    train: {_fmt(r['train'])}   "
                         f"test: {_fmt(r['test'])}")
        beat = sum(1 for r in judged
                   if total_r(r["test"]) > total_r(bs)
                   and total_r(r["train"]) > total_r(bt))
        lines.append(f"  pairs beating baseline totR in BOTH windows: "
                     f"{beat}/{len(judged)} judged "
                     f"(chance predicts ~{len(rows) * 0.05:.1f})")

    lines += ["",
              "LAW 12/20: a combination is a new hypothesis, not a merger "
              "of old verdicts. Only the pre-registered set above carries "
              "verdicts, and none is adopted without operator decision."]
    return "\n".join(lines)


if __name__ == "__main__":
    store = DataStore(DATA_ROOT)
    if not store.tickers():
        raise SystemExit("No data. Run: python -m mve.backfill")
    from .report import save_and_print
    save_and_print("combinations", summary(run_combos(store)))
