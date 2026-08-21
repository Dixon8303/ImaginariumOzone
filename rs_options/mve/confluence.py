"""Confluence scoring (H19, §72) — grade setups instead of gating them.

Traders using "confluence" rarely mean what H18 tested (require every
indicator to agree or skip the trade). They mean: count how many
things line up and act with more conviction when more of them do. That
is a different design with a different failure mode, and it sidesteps
the trap the gating studies kept hitting — a score never deletes a
trade, so it cannot repeat H5's sin of raising the average by throwing
away profitable trades. The worst a useless score can do is nothing.

The danger is on the other side: WEIGHTED confluence (2 points for
this, 0.5 for that) has as many free parameters as weights, and fitting
them to history is an overfitting machine. So nothing here is fitted:

- Part A reports the §32 opportunity score the system already computes
  on every signal — a 0-10 rubric written in the spec before any of
  this data existed. Built for H17; reported here for the first time.
- Part B counts EQUAL-WEIGHT votes from the round-5 factor primaries,
  each voting exactly the direction that was pre-registered when it
  was a hypothesis. No weights, no flips, no thresholds tuned.

The verdict instrument is dose-response, the same one that judged the
H15 gap claim: confluence is real only if expectancy RISES with the
score in BOTH windows. Flat means the votes carry no information.
Falling means the factors collectively anti-predict (which is what the
H18 autopsy suggests — several rejected filters were removing the
system's best trades). Any monotone result earns at most SIZING by
score, never gating: sizing keeps every trade and every unit of total
return, and merely re-allocates risk toward conviction.

Votes fail closed: an unmeasurable factor votes 0. A missing vote and
a contrary vote are therefore indistinguishable, which is acceptable
for a diagnostic — stated here so nobody mistakes low-vote buckets for
"the factors all disagreed".

    python -m mve.confluence        # needs news + fundamentals on disk
"""
from __future__ import annotations

from .backtest import DATA_ROOT, run_backtest
from .fundamentals import is_profitable, load_fundamentals
from .hypotheses import (TEST_START, TRAIN_END, quiet_base, signal_date,
                         strong_close)
from .news import load_news, quiet_attention
from .setups import rs02_entry_ok
from .store import DataStore
from .volume_profile import clear_overhead

SETUP = "RS-02"
GAP_VOTE_MAX = 0.02             # fill-time vote: open did not run >2% away

# Signal-time voters, each in its pre-registered direction. H16 is
# excluded because it never binds in this universe (round 5) — an
# always-yes voter would just shift every count up by one.
VOTER_NAMES = ("quiet_news", "profitable", "clear_overhead",
               "quiet_base", "strong_close", "small_gap")


def make_voters(news: dict, facts: dict) -> dict:
    """{name: fn(ticker, bars) -> bool} — signal-time votes only; the
    gap vote is fill-time and read off the trade instead."""
    return {
        "quiet_news": lambda t, b: quiet_attention(news, t,
                                                   signal_date(b), 2.0),
        "profitable": lambda t, b: is_profitable(facts, t, signal_date(b)),
        "clear_overhead": lambda t, b: clear_overhead(b, 0.10),
        "quiet_base": lambda t, b: quiet_base(b, 0.40),
        "strong_close": lambda t, b: strong_close(b, 0.70),
    }


def recording_filter(voters: dict, votes: dict):
    """Doctrine entry filter that also records each signal's votes,
    keyed (ticker, signal_date) for the join to trades afterwards."""
    def entry(t, b, s):
        if not rs02_entry_ok(b):
            return False
        votes[(t, signal_date(b))] = {
            name: bool(fn(t, b)) for name, fn in voters.items()}
        return True
    return entry


def vote_count(trade, votes: dict) -> int:
    """Signal-time votes plus the fill-time gap vote."""
    v = votes.get((trade.ticker, trade.signal_date), {})
    n = sum(1 for passed in v.values() if passed)
    if trade.gap_pct <= GAP_VOTE_MAX:
        n += 1
    return n


def vote_table(result, votes: dict, setup: str = SETUP) -> list:
    """Expectancy by vote count. Adjacent counts with tiny samples are
    NOT merged — thin buckets should look thin."""
    by_count = {}
    for t in result.trades:
        if t.setup != setup:
            continue
        by_count.setdefault(vote_count(t, votes), []).append(t.r_multiple)
    rows = []
    for count in sorted(by_count):
        rs = by_count[count]
        rows.append({"votes": count, "trades": len(rs),
                     "expectancy_r": round(sum(rs) / len(rs), 3),
                     "total_r": round(sum(rs), 2)})
    return rows


def run_confluence(store: DataStore, news: dict | None = None,
                   facts: dict | None = None) -> dict:
    if news is None:
        news = load_news()
        if not news:
            raise SystemExit("No news counts on disk. Run: python -m mve.news")
    if facts is None:
        facts = load_fundamentals()
        if not facts:
            raise SystemExit("No fundamentals on disk. "
                             "Run: python -m mve.fundamentals")
    voters = make_voters(news, facts)
    out = {}
    for window, kw in (("train", {"end": TRAIN_END}),
                       ("test", {"start": TEST_START})):
        votes = {}
        result = run_backtest(store, active=(SETUP,),
                              entry_filter=recording_filter(voters, votes),
                              **kw)
        out[window] = {"rubric": result.per_score(),
                       "votes": vote_table(result, votes)}
    return out


def summary(results: dict) -> str:
    lines = [
        "CONFLUENCE STUDY — grade setups, do not gate them (H19, §72)",
        f"train <= {TRAIN_END} | test >= {TEST_START} | doctrine trades only",
        "",
        "Scores never remove a trade, so nothing here can repeat H5's",
        "average-up-total-down failure. The question is narrower: does",
        "MORE agreement predict a BETTER trade? Only a rise that holds",
        "in BOTH windows counts — and it earns sizing by score, never",
        "gating.",
        "",
        "PART A — the §32 opportunity score (0-10 rubric, pre-registered",
        "in the spec; computed on every signal since the MVE was built,",
        "reported here for the first time):",
    ]
    for window in ("train", "test"):
        lines.append(f"  {window}:")
        for bucket, s in results[window]["rubric"].items():
            lines.append(f"    score {bucket:<4} n={s['trades']:>3} "
                         f"exp={s['expectancy_r']:+.3f}R")
    lines += [
        "",
        "PART B — equal-weight factor votes (round-5 primaries, each in",
        "its pre-registered direction; no weights, no flips; unmeasurable",
        "factors vote 0; +1 fill-time vote when the open gapped <= "
        f"{GAP_VOTE_MAX:.0%}):",
        "  voters: " + ", ".join(VOTER_NAMES),
    ]
    for window in ("train", "test"):
        lines.append(f"  {window}:")
        for row in results[window]["votes"]:
            lines.append(f"    {row['votes']} votes  n={row['trades']:>3} "
                         f"exp={row['expectancy_r']:+.3f}R "
                         f"totR={row['total_r']:+7.2f}")
    lines += [
        "",
        "READING IT: rising in both windows = confluence carries real",
        "information -> candidate for sizing by score (more risk on",
        "high-vote signals, all trades still taken). Flat = the votes",
        "are noise; the doctrine gate already extracted the signal.",
        "Falling = the factors collectively anti-predict, confirming",
        "the H18 autopsy from a second angle. Thin buckets (n < 10)",
        "prove nothing in any direction.",
        "",
        "LAW 12/20: a monotone slope on train alone is how overfitting",
        "looks. Sizing by score gets adopted only if the slope survives",
        "the test window, and only by operator decision.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    store = DataStore(DATA_ROOT)
    if not store.tickers():
        raise SystemExit("No data. Run: python -m mve.backfill")
    from .report import save_and_print
    save_and_print("confluence", summary(run_confluence(store)))
