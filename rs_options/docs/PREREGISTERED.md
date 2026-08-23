# Pre-registered hypotheses

Claims written down **before** the data that will judge them exists.

Why this file exists: the project has spent every clean historical
sample it had. 2021–2026 chose the thresholds. 2025–2026 was consulted
across six rounds. 2006–2020 was spent on the H20 holdout. Nothing
historical is virgin any more, so the only honest test left is
**forward** — results from paper trading and live sessions that have
not happened yet.

Entries come in two kinds. **FWD-*** await data that does not exist
yet. **H-*** can run on history the moment they are written — they live
here because writing the parameters down BEFORE the first run is what
makes a test on already-glimpsed data honest. For those, the commit
that registers the entry must land BEFORE the commit that implements
the study; git history is the timestamp.

A hypothesis recorded here is frozen. The threshold, the direction, the
success criterion, and the minimum sample are all fixed now, in
advance, so that a later reader cannot mistake a reshaped claim for a
confirmed one. If the forward data disagrees, the entry is marked
FAILED and stays in the file.

---

## FWD-1 — Score-8 setups underperform

**Registered:** 2026-08-23, after the H20 holdout.

**Claim.** Among RS-02 signals that pass full doctrine, those with a §32
opportunity score of exactly **8** have negative expectancy, while
scores of 9 and 10 are positive.

**Where it came from.** The §32 score FAILED its pre-registered holdout
test — it did not rise monotonically across all four buckets, because
the `<=7` bucket sits above the `8` bucket. That failure stands and is
not being relitigated. But one sub-pattern repeated in all three
samples measured:

| Sample | score <=7 | score 8 | score 9 | score 10 |
|---|---|---|---|---|
| Guarded train (2006–2024, n=478) | −0.040R | **−0.133R** | +0.143R | +0.226R |
| Guarded test (2025–2026, n=48) | −0.097R¹ | **−0.335R**¹ | −0.200R | +0.723R |
| Virgin holdout (2006–2020, n=376) | +0.028R | **−0.152R** | +0.115R | +0.165R |

¹ n=1 and n=4 — reported for completeness, worth nothing on their own.

Score 8 is negative in every sample. **This is an observation, not a
finding**: it was noticed after the fact, the samples overlap (the
holdout is a subset of guarded train), and no clean historical data
remains to test it. Hence forward registration.

**Success criterion, fixed now.** Over forward paper/live RS-02 trades:

- **CONFIRMED** if, at **n ≥ 40 score-8 trades**, score-8 expectancy is
  negative AND at least 0.15R below the expectancy of score 9–10 trades
  over the same period.
- **FAILED** if at that sample size score-8 expectancy is positive, or
  within 0.05R of the 9–10 group.
- **INCONCLUSIVE** below n = 40. No verdict before then, regardless of
  how the numbers look. At roughly 25 signals a year across the
  universe with maybe a third scoring 8, this needs several years — it
  is a slow test and that is the honest cost of having spent the
  historical samples.

**What may NOT be done with it.** Nothing acts on the score until
CONFIRMED. `OpenPosition.score` is recorded so the pairing accumulates;
no code reads it to size, gate, rank, or skip. If it is ever confirmed,
the permitted use is **sizing** (weight down score-8 risk), never
gating — the holdout showed that gating to high scores raises the
average while cutting total return, which is the H5 failure.

**Status:** OPEN — awaiting forward data.

---

## FWD-2 — The 2% gap cliff persists forward

**Registered:** 2026-08-23, alongside the H15a adoption recommendation.

**Claim.** RS-02 fills whose open gaps **more than 2%** above the signal
close have negative expectancy, while fills gapping 0–2% do not.

**Where it came from.** H15a passed the H20 holdout on data disjoint
from the window that chose its 2% threshold (2006–2020 vs 2021–2026):
expectancy +0.021R and total +6.84R over 9 cancelled fills. The 2%+
bucket was negative in every window measured:

| Window | n | expectancy |
|---|---|---|
| Guarded train 2006–2024 | 25 | −0.248R |
| Guarded test 2025–2026 | 7 | −0.023R |
| Virgin holdout 2006–2020 | 21 | −0.209R |

**The caveat that travels with it.** The registered shape was a
**steady decline** across gap buckets. What appears is a **cliff**:
moderate gaps (0–1%, 1–2%) are fine or better, and only the 2%+ bucket
is negative. A threshold effect is a different claim from the one
registered. H15a is recommended on the strength of the direction, the
disjoint-sample confirmation, and the execution-cost mechanism — not on
the shape, which did not match.

**Success criterion, fixed now.** Over forward sessions, at **n ≥ 25
cancelled orders**: CONFIRMED if the cancelled set would have averaged
below −0.10R; FAILED if it would have averaged above +0.05R. Cancelled
orders must be logged with the R they would have produced, or this
cannot be judged.

**Status:** OPEN — awaiting forward data. Adoption of the cancellation
rule itself is the operator's decision and does not depend on this
entry; this entry checks whether the rule keeps earning its place.

---

## H-22 — Cross-sectional momentum, long only

**Registered:** 2026-08-23, before any implementation exists. The study
is deliberately NOT written yet.

**Mechanism, stated first.** Jegadeesh & Titman (1993): rank assets
against EACH OTHER and the leaders keep leading over 3-12 month
horizons. It is among the most replicated anomalies in finance —
out-of-sample across forty years, dozens of markets and several asset
classes.

This is a genuinely different claim from RS-02, not a variant of it:

| | RS-02 (adopted) | H-22 |
|---|---|---|
| basis | absolute — is THIS stock breaking out? | relative — which names are strongest? |
| trigger | event-driven (a breakout happens) | calendar-driven (monthly rebalance) |
| exposure | episodic, often flat | continuously invested while names qualify |
| exit | stop / target / 15-day cap | the next rebalance |
| bet | this breakout continues | relative strength persists across a universe |

**Every parameter is fixed here, and none is fitted to this data.**
Each comes from published literature or from already-adopted doctrine,
which is what makes the test meaningful despite the windows having been
glimpsed:

- **Universe:** the 21 non-benchmark tickers already in
  `mve/universe.py`. No additions, no substitutions.
- **Ranking metric:** 12-1 momentum via the existing `mom_12_1`
  (`MOM_LOOKBACK` 252, `MOM_SKIP` 21). Reused deliberately so the study
  introduces no new free parameter.
- **Rebalance:** first trading day of each month, ranked on the prior
  close, filled at that day's open — the same point-in-time discipline
  as every other study here.
- **Holdings:** two arms, top 3 and top 5, equal weight. Both are
  counted against multiple comparisons.
- **Eligibility:** a name must sit above its own 200-day SMA
  (`above_sma`, adopted doctrine). Fewer qualifiers means a smaller
  book; zero means fully in cash.
- **Exit:** at the next rebalance. **No stop loss** — this is the point
  of difference, not an oversight, and it is why R-multiples do not
  apply.
- **Costs:** charged, never gross. Monthly rebalancing of 3-5 names
  turns over far more than RS-02's ~25 trades a year, so a gross result
  would flatter this strategy more than anything tested so far.

**Measurement.** Portfolio-level CAGR, Sharpe, max drawdown, and
turnover. NOT R-multiples: with no stop there is no R, and quoting one
would invite a false comparison against RS-02's +0.117R.

**Benchmark: SPY buy-and-hold over the identical window, costs
included.** This is the honest bar. A long-only, near-always-invested
strategy that cannot beat the index does not justify its complexity,
however good its absolute return looks in a bull decade.

**Windows.** TRAIN <= 2020-12-31, TEST >= 2021-01-01 — stated with the
caveat that since nothing is fitted, the split is a consistency check
rather than a true holdout. Disagreement between the windows is itself
the finding.

**Success criteria, fixed now.**

- **CONFIRMED** if, in BOTH windows, Sharpe exceeds SPY buy-and-hold
  Sharpe AND max drawdown is no worse than SPY's, over at least 60
  rebalances total.
- **FAILED** if either window's Sharpe falls below SPY's.
- **INCONCLUSIVE** below 60 rebalances, regardless of how the numbers
  look.

**A handicap recorded in advance, so a failure is read correctly.** The
published effect is strongest in the LONG-SHORT spread; the short leg
is prohibited here (§87, long premium only). A long-only version keeps
the market beta and drops half the factor, so it is a weaker test than
the literature's. H-22 may fail even if cross-sectional momentum is
real — that outcome means "not capturable long-only in 21 names", not
"the factor is false".

**What confirmation would NOT license.** It is a portfolio strategy
needing 3-5 simultaneous positions rebalanced monthly — incompatible
with the current account, and awkward with long-premium options (buying
calls on five names every month, at the costs `paper/option_costs.py`
is now measuring). It does not modify RS-02 and would not replace it;
it would earn the right to be measured alongside it, and a separate
adoption decision.

**Status:** OPEN — registered, not implemented.

---

## How to close an entry

Add a dated verdict line to the entry, append the reasoning to
`RESEARCH_LOG.md`, and leave the original text untouched. Editing a
registered claim to match its result destroys the only thing this file
is for.
