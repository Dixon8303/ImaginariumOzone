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

## FWD-3 — Fundamental quality and long-call outcomes

**Registered:** 2026-08-26, after the operator asked for options entries
that combine momentum, trend, and fundamentals with "institutional
sensibility."

**Claim.** Among autonomous paper long-call entries (`run_option_cycle`),
positions opened on an underlying that is **trailing-profitable**
(`mve.fundamentals.trailing_net_income` positive over the last four
quarters known as of entry, point-in-time safe on the SEC `filed` date)
realize a higher option-level R multiple (realized P&L / premium paid)
than positions opened on an underlying that is not profitable, or whose
profitability is unknown.

**Where it came from, and why it is not H10 again.** H10 (2026-08-23
combination study, `RESEARCH_LOG.md`) tested a similar-sounding idea —
gating RS-02 STOCK entries on the same trailing-profitability check —
and it FAILED clearly: it removed 163 profitable stock trades worth
+20.58R, one of the two worst filters in that round. **That result
stands and is not being relitigated (LAW 20).** But it measured the
underlying's bounded, stop-defined R. A long call has a different
payoff: it can lose its entire premium to time decay or an underwhelming
move even when the stock's own stop never triggers, and an unconvincing
("story", not earnings) breakout can see its IV contract on top of that
— a failure mode invisible to stock-only R math. Whether the
underlying's fundamental quality discriminates between OPTION outcomes
specifically is a different mechanism on different data, not a rerun of
a closed hypothesis.

**No parameter is fitted.** The profitability test reuses
`is_profitable`/`trailing_net_income` exactly as H10 coded them — no new
threshold tuned to make this presentable.

**No historical test is possible.** Historical option chains are paid
data this project does not have (`paper/option_costs.py`, 2026-08-23).
This can only accumulate forward, one real paper fill at a time — the
same reason FWD-1 and FWD-2 exist.

**Recording mechanism, live today.** Every autonomous paper option entry
tags its ledger record with `fundamental_net_income` — the raw trailing
four-quarter sum, or `null` when unknown (`paper/daily.py ::
run_option_cycle`). Nothing reads this tag to gate, size, or rank
anything; it exists only so the pairing accumulates, exactly like
`OpenPosition.score` under FWD-1.

**Success criterion, fixed now.** Judged only once at least **15 CLOSED
autonomous option trades** exist in EACH of the profitable and
not-profitable/unknown buckets (lower than FWD-1's 40, because option
entries are rarer than stock signals — they must also clear DTE/delta/
spread/open-interest eligibility on top of the RS-02 signal itself):

- **CONFIRMED** if the profitable bucket's mean option R (realized P&L /
  premium paid) is positive AND at least 0.25R above the
  not-profitable/unknown bucket.
- **FAILED** if the two buckets are within 0.10R of each other, or the
  not-profitable bucket is higher.
- **INCONCLUSIVE** below 15 trades in either bucket, regardless of how
  the numbers look.

**What may NOT be done with it.** Nothing gates or sizes on this tag
until CONFIRMED. If confirmed, the only permitted use is **sizing**
(e.g. trimming `contracts_to_buy` on unprofitable-underlying entries),
never an outright entry gate — H10's own failure mode was gating, and
the stock-side lesson (H-22, H5: concentrating on "better" setups can
cut total edge even while raising the average) is exactly the trap a
hard gate would repeat here.

**Status:** OPEN — recording began 2026-08-26, awaiting forward fills.

---

## H-23 — Universe expansion holds the RS-02 edge

**Registered:** 2026-08-27, BEFORE the study module or any backtest on
the candidate names existed. The commit carrying this entry precedes the
commit implementing `mve.expansion_study`; git history is the timestamp.

**Why an expansion at all.** The operator asked how to grow the account
faster. The honest levers are expectancy and trade frequency; the 22-name
universe produces ~25 RS-02 signals a year. A structurally-selected
expansion raises frequency at (if this hypothesis holds) the same
per-trade edge, and accelerates every forward test in this file
(FWD-1/2/3 all wait on sample size). It also widens the set of
micro-affordable names for the sub-$500 override account.

**Claim.** RS-02, with the adopted filters exactly as they stand today
(H2b 200-day regime, H4b 12-1 momentum ≥10%, H15a 2% gap cap), has
non-negative out-of-sample expectancy on the candidate names below, and
adding them does not degrade the combined universe's edge.

**The candidates, fixed now — selected on STRUCTURE only** (options
depth, cluster coverage, price structure able to carry doctrine
contracts), with live prices recorded at registration (2026-08-27):

| Ticker | Cluster | Sector ETF | Price | Micro-affordable |
|---|---|---|---|---|
| UNH | healthcare (new) | XLV | $395 | no |
| ABBV | healthcare (new) | XLV | $258 | no |
| PFE | healthcare (new) | XLV | $28 | yes |
| BA | industrials (new) | XLI | $210 | no |
| RTX | industrials (new) | XLI | $212 | no |
| T | telecom (new) | XLC | $25 | yes |
| VZ | telecom (new) | XLC | $49 | yes |
| V | payments (new) | XLF | $380 | no |
| PYPL | payments (new) | XLF | $61 | yes |
| COIN | crypto_fin (new) | XLF | $191 | no |
| HOOD | crypto_fin (new) | XLF | $110 | yes |
| SOFI | financials | XLF | $19 | yes |
| ORCL | software | XLK | $152 | no |
| CRM | software | XLK | $252 | no |
| CVX | energy | XLE | $200 | no |
| F | ev_auto | XLY | $14 | yes |

Evaluated and REJECTED at registration, so the rejections cannot be
quietly revisited after results exist: MSTR (leveraged single-asset
proxy whose premium-to-holdings can compress structurally — the
mechanism standard behind the VXX/UVXY ban extends to it), AVGO, INTC,
QCOM (semis already 3-deep; concentration, not coverage), COST, HD
(consumer already 3-deep), LLY, CAT (a doctrine call on a ~$800-1,200
underlying costs several times the 1% risk budget at current equity —
equity-only names add cluster weight without serving the options
track), JNJ (healthcare 4th, no distinct structure over the three
kept), GE (aerospace already covered by BA+RTX).

**Data requirement.** One consistent daily-bar pull for BOTH arms —
every incumbent, every candidate, benchmark and sector ETFs from the
same vendor in the same backfill, corrupt-bar guards active. A missing
ticker aborts the study (LAW 18); it never silently shrinks an arm.
Young listings (COIN, HOOD, SOFI — 2021; PLTR already in-universe —
2020) contribute their full real history; the H4b filter already
fail-closes their first ~13 months.

**Success criterion, fixed now.** On the yearly expanding-window
walk-forward (benchmark-span windows, MIN_TRAIN_YEARS=3), test windows
only, measured inside the combined universe:

- **CONFIRMED** if candidate-only expectancy ≥ 0R at **n ≥ 30 candidate
  trades**, AND combined-universe expectancy ≥ baseline − 0.05R (both
  arms from the same pull).
- **FAILED** if candidate-only expectancy < −0.05R at n ≥ 30, OR the
  combined universe drags more than 0.05R below baseline.
- **INCONCLUSIVE** below n = 30, regardless of how the numbers look.

**Adoption is ALL candidates or NONE.** Per-ticker cherry-picking after
seeing results is prohibited — keeping only the names that backtested
well is selection bias wearing a lab coat, the exact failure H-22's
control exposed. If the list fails, a narrower list may be registered
later as a NEW entry with a written structural rationale, never by
editing this one.

**What may NOT be done before the verdict.** The candidates do not
enter the tradeable `UNIVERSE`, the live scan, or the paper trader.
They exist only in `CANDIDATE_UNIVERSE` (a fetch/study set), and the
study reads them only through `mve.expansion_study`.

**Status:** OPEN — registered, awaiting the study run (needs a machine
that can reach the bar vendors: the operator's Mac, or the
`rs_expansion_study` GitHub Actions job).

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

**Implementation note (2026-08-23, added after the fact — the claim
above is NOT edited).** The entry says "the 21 non-benchmark tickers".
`UNIVERSE` actually holds 22, none of them the benchmark; the 21 was a
miscount here, not a different universe. The binding intent — the
existing universe, no additions or substitutions — is what
`mve.cross_sectional` uses. Recorded rather than silently reconciled,
because editing a registration to match the code is how
pre-registration stops meaning anything.

**Status:** OPEN — implemented in `mve.cross_sectional`, awaiting a run
against real bars.

**Verdict (2026-08-24).** FAILED, both arms, by the registered
criterion — train drawdown (TOP3 -55.0%, TOP5 -54.5%) worse than SPY's
-52.9%. Sharpe beat SPY in both windows for both arms; the criterion
required BOTH clauses and the drawdown clause was the one that bound.

The control added post-hoc (`universe_buy_hold`: hold every eligible
name, no ranking) makes the failure more informative than a bare FAILED
would suggest. Against the control, in EVERY window, on BOTH
risk-adjusted measures:

    TOP3 train: Sharpe 1.00 vs control 1.01 (-0.01)   DD -55.0% vs -50.5% (worse by 4.6pp)
    TOP3 test:  Sharpe 1.06 vs control 1.18 (-0.12)   DD -42.7% vs -32.6% (worse by 10.1pp)
    TOP5 train: Sharpe 1.03 vs control 1.01 (+0.02)   DD -54.5% vs -50.5% (worse by 4.0pp)
    TOP5 test:  Sharpe 0.96 vs control 1.18 (-0.22)   DD -43.0% vs -32.6% (worse by 10.4pp)

Concentrating to 3-5 names raised nominal CAGR (TOP3 test +45.6% vs
control's +26.8%) but did NOT raise Sharpe — it fell in 3 of 4 windows,
most sharply on test, the window that matters most for judging whether
this generalizes. The extra CAGR is concentration risk, not selection
skill: fewer names means more variance, which mechanically lifts CAGR
under compounding without improving return per unit of risk. The
handicap recorded above (long-only drops the literature's short leg)
remains true, but does not rescue this: even the handicapped long-only
version underperforms its own no-selection control on every
risk-adjusted measure, which a genuine long-only momentum edge would
not do.

Read together with the eligibility row (mean 12-15 names qualify per
month; the filter is a real cut, not "top 3 of 3") this is a clean
result, not an underpowered one: cross-sectional momentum ranking, on
top of the adopted trend filter, adds concentration and subtracts
risk-adjusted return, in this universe, on both measures, in both
windows.

**FAILED. Not adopted. No further work planned** — a null result this
clean does not call for retuning TOP_N or the rebalance frequency; that
would be searching for the one configuration where concentration
happens to pay, which is exactly the multiple-comparisons trap this
project's guards exist to catch.

---

## How to close an entry

Add a dated verdict line to the entry, append the reasoning to
`RESEARCH_LOG.md`, and leave the original text untouched. Editing a
registered claim to match its result destroys the only thing this file
is for.
