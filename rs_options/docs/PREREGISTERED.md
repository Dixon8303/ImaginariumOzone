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

## H-27 — Momentum scalping survives the retail latency class

**Registered:** 2026-09-25, BEFORE any scanner, state machine, harness
or backtest for this strategy exists. The commit carrying this entry
precedes the implementation commit; git history is the timestamp.

**Provenance.** The operator supplied a written specification of Ross
Cameron's (Warrior Trading) momentum scalping method, sourced from a
"$2k to $100k in 46 Days" challenge account: 5-pillar small-cap
selection, pullback / crossing-candle entry, 1:1 reward:risk, claimed
~70% win rate over 113 trades, claimed +0.40R per trade. The claim is
recorded here verbatim as the thing under test. It is not adopted, and
its provenance — a marketed challenge result — is itself a reason for
the bar below to be set where it is.

**The null, stated plainly so a later reader cannot soften it.** The
null hypothesis is that small-cap momentum scalping has zero or
negative NET edge at retail latency, and that the source's results are
explained by selection and survivorship — one publicized account out of
a population whose losers are not published. This entry does not
presume the method works. It presumes the null and asks what evidence
would overturn it.

**Scope and placement.** If this survives, it is component #10 under
the repo's independence rule — its own tree, its own execution path.
It is NOT wired into RS Options or HoneyDrip: different instrument
class (sub-$20 low-float small caps), different timeframe (10s/1m),
different data tier. It is registered *here* because the H-* discipline
and §38 both live here, and because §38 is what makes this hypothesis
worth registering at all.

### Gate 0 — §38 EDGE_FASTER_THAN_PIPE (structural, evaluated FIRST)

The spec already answers this question by assertion: §38 states "this
system is a latency-taker, not a latency-competitor" and lists
"scalping and 0DTE gamma harvesting are out of scope at this latency
class." The hard rule rejects any setup whose modeled edge half-life is
shorter than a default 10x the measured end-to-end latency envelope,
**regardless of backtest performance.**

Registering H-27 converts that assertion into a measured proposition.
If the gate trips, §38 is vindicated with evidence instead of assumed;
that is a real result and it closes this entry FAILED.

Frozen measurement, so neither side of it can be reshaped later:

- **Latency envelope L** = p95(data age) + p95(order round-trip),
  measured on the actual execution path over >= 500 samples spanning
  both the 07:00-09:30 pre-market window and regular hours. Measured,
  never assumed, never theoretical zero.
- **Edge half-life T-half** = the smallest execution delay d for which
  net expectancy E(d) <= E(0)/2, with d drawn from
  {0, 100ms, 250ms, 500ms, 1s, 2s, 5s, 10s}. E(d) fills the entry from
  the actual tick tape at (trigger_time + d) at the then-prevailing
  offer; stop and target logic are unchanged.
- **Gate:** if T-half < 10 x L, the hypothesis is **REJECTED —
  structurally, regardless of E(0) and regardless of every criterion
  below.** No expectancy number may override it. That is the spec's
  own rule and this entry does not get an exemption from it.

The spec's §6 routing note compounds this and is adopted verbatim:
on zero-commission / wholesaler PFOF routing (Schwab, Webull,
Robinhood, Alpaca), breakout *anticipation* entries are disallowed;
only validated micro-pullback resting orders are admissible.

### Gate 1 — Fill realism (LAW 14), and why bars are inadmissible

The claimed 1:1 uses a cent-level stop at the pullback low against a
target measured in cents. At that resolution a 1-minute bar **cannot
tell you whether the `Prior_Candle_High + $0.01` trigger printed before
or after the low that stops you out.** That intrabar sequencing
ambiguity is larger than the entire claimed edge, and resolving it by
assumption in either direction decides the result before the data does.

Frozen consequence: **a bar-only study is not admissible evidence for
this entry.** The study runs on trades-and-quotes tick data, with:

- intrabar sequencing taken from the actual tick sequence, never assumed;
- entry filled at the prevailing offer or worse (the trigger is
  marketable by construction), never at the trigger price;
- stop filled at the prevailing bid with slippage, gap-through filling
  at the next available print;
- spread carried as measured, not modeled — on $2-$20 low-float names
  at RVOL >= 5 it runs 1-5 cents and widens in the squeeze, which is
  40bp+ round trip on a $5 stock, roughly 8x the swing book's cost;
- LULD halt and resume handled explicitly; a halt is not a silent skip.

The spec's own admission — "expect to capture < 50% of the visual
move" — is an acknowledgement that visible moves overstate achievable
ones. The study therefore reports realized capture rate against the
visually available move as a standing number.

### Frozen rules — the strategy as registered

Thresholds are the operator's specification, taken verbatim and frozen:

1. **Pillar 1 — Price:** $2.00 <= P <= $20.00 (A-quality $5-$10).
2. **Pillar 2 — Gain:** change >= +10.0% (A-setup >= +30.0%).
3. **Pillar 3 — RVOL:** >= 5.0x vs. 50-day SMA volume, compared at the
   same time-of-day (a cumulative-vs-full-day comparison would
   manufacture 5x every morning). Preferred confirmation: day volume
   > 25M shares. Low-volume anticipation entries forbidden.
4. **Pillar 4 — Float:** < 20M shares (high conviction < 10M).
5. **Pillar 5 — Catalyst:** breaking headline in AH or pre-market;
   the no-news sympathy/squeeze exception only when the ticker is the
   #1 leading gainer, at reduced size.
6. **Windows:** optimal 07:00-09:30 ET, secondary 09:30-10:00 ET, hard
   cutoff on new entries at 10:00 ET. All times America/New_York,
   DST-aware.
7. **Entry state machine:** impulse to new HOD on elevated volume ->
   pullback -> buy at `Prior_Candle_High + $0.01`. Stop = pullback low.
8. **1:1 validation gate:** abort unless
   `(Prior_HOD - Entry) >= (Entry - Stop)`. Suppress entirely when
   theoretical upside to prior HOD < $0.10.
9. **Exits:** 50% at prior-HOD retest, trail the runner; hard stop at
   the pullback low; topping tail; doji; volume divergence.
10. **Circuit breakers:** give-back rule (liquidate and halt for the
    day if daily P&L falls to <= 50% of intraday peak P&L); daily max
    loss halt; regime filter (suspend the session after the first two
    leading-gainer breakout setups fail in succession).
11. **Sizing:** 1% of equity risked per trade, consistent with the
    program's existing risk budget. Not specified by the source, so
    frozen here rather than chosen later against results.

**Two of the seven exits cannot be built, and this changes what is
under test.** Exit 3 (abnormally large ask block) and exit 4 (hidden
seller absorption) require Level 2 depth-of-book. Alpaca does not
provide a montage; the Robinhood MCP does not either; both need a
TotalView / DAS-class feed the program does not have. Exit 5 (tape
aggression) is approximated by Lee-Ready trade-side classification
against the prevailing quote, and that approximation is disclosed
rather than presented as the rule it stands in for.

Therefore **what is registered is the bar-and-tape variant, not the
source's method**, and it **may not inherit the source's 70% / 1:1 /
+0.40R figures.** Those figures appear in this entry only as the claim
being tested. If the variant fails, that is not evidence the full
method fails, and the converse is equally barred.

**Ambiguities resolved now, in advance, because each one is an
opportunity to tune against results later:** a pullback is 1-3
consecutive lower-closing 1-minute candles; "tight basing" is <= 3
bars whose combined range <= 50% of the impulse bar's range;
"volume contracts" means mean pullback-bar volume < impulse-bar
volume; a topping tail is an upper wick >= 2x the candle body; a doji
is a body <= 10% of the bar's range; volume divergence is a higher
high on volume below the prior bar's; float is approximated as SEC
`dei:EntityPublicFloat` / price from the most recent filing, with
staleness bounded and disclosed (this is public float in dollars, NOT
true share float, and the substitution is recorded rather than hidden);
catalyst presence is evaluated over [16:00 prior session, 09:30]; the
give-back peak tracks realized plus unrealized P&L intraday; "first two
setups fail" means the session's first two entries both reach their
stop.

**Data requirement.** Trades and quotes tick data for every scanned
candidate across the study period, from one consistent vendor and pull,
with corrupt-tick guards active. A missing or partial symbol-day aborts
the study rather than silently shrinking the sample (LAW 18). Minute
bars alone do not satisfy this requirement — see Gate 1.

**Regulatory constraint, recorded now.** Pattern Day Trader rules cap a
sub-$25,000 margin account at three day trades per five business days.
The strategy is unrunnable as specified below that equity. The paper
account (~$98k) is unaffected for testing; any live decision must state
the account it applies to.

### Success criterion, fixed now

Evaluated in order. Gate 0 and Gate 1 are prerequisites, not tradeable
against performance.

0. **Gate 0 (§38):** T-half >= 10 x L, else REJECTED outright.
1. **Gate 1 (LAW 14):** results produced on tick data under the fill
   model above, else INADMISSIBLE.
2. **CONFIRMED (adoption-eligible)** requires ALL of:
   - **net** expectancy >= **+0.10R**, costs and measured slippage
     deducted — not gross;
   - **n >= 200** closed trades spanning **>= 60 distinct ticker-days**;
   - positive net expectancy in **>= half** of judged calendar months
     (a month is judged at >= 10 trades);
   - **no single ticker-day contributes > 20%** of total net R.
3. **FAILED** if the sample is reached and any clause above is missed.
4. **INCONCLUSIVE** below n = 200 or below 60 ticker-days, however the
   numbers look.

**Why these numbers, written down before the result so the reasoning
cannot be retrofitted:**

- **NET, not gross.** Every other entry in this file judges gross and
  reports break-even, because swing-trading friction is ~5bp against
  expectancies near +0.12R. Scalping inverts that: spread alone is
  40bp+ round trip. A gross criterion here would confirm strategies
  that lose money, so the house convention is deliberately broken and
  the break-even friction level is still reported alongside.
- **+0.10R, not >= 0R.** The claim under test is +0.40R. A zero bar
  would "confirm" a strategy delivering none of its claim while
  consuming more operator attention — pre-market hours, halt risk, live
  tape — than everything else in the program combined. +0.10R is a
  deliberate 4x haircut on the claim: generous to the hypothesis, still
  a real edge, and above the noise floor once scalping costs are paid.
- **60 ticker-days, not just n >= 200.** Scalp trades cluster: ten
  entries on one squeeze are one bet, not ten. Raw trade count alone is
  the easiest way to manufacture significance here, so independence is
  required explicitly.
- **The 20% concentration clause** exists because one 2021-style
  parabolic day can carry an entire result. If it does, that is a
  finding about that day, not about the strategy.
- **Breadth across months** because small-cap momentum is violently
  regime-dependent; a 2021-only edge is a regime artifact.

Per-ticker, per-day, per-window and per-setup-quality (A-setup vs.
baseline) splits are computed and reported as **context, never as
criteria** (LAW 20). Net expectancy is reported beside the live book's
for scale — also context, not a criterion. The thresholds above may be
**tightened** before results and never loosened; that is the only
direction any of them may move.

**Adoption is a separate decision.** CONFIRMED means adoption-ELIGIBLE
only. No activation follows automatically, the philosophy's one-new-
setup-at-a-time sequencing still applies, and because this is a new
component it additionally requires its own execution path, its own
ARMED interlock, and an explicit operator decision naming the account.

**What may NOT be done before the verdict.** No execution path, no
capital, no paper or live wiring, no scanner running against the live
book, and no entry into any tradeable universe. The work exists as
study code in its own tree and nothing else. Partial results do not
license a "small test position" — that is adoption without the verdict.

**Status:** OPEN — registered, implementation and study to follow.

---

## H-26 — Second expansion: sector coverage the universe has never held

**Registered:** 2026-09-12, BEFORE the candidate set or any study code
exists. The commit carrying this entry precedes the implementation
commit; git history is the timestamp.

**Provenance.** The operator asked whether seven names (TSLA, OUST,
ISRG, AMBA, CGNX, AME, COPR) should be added, supplying analyst
consensus ratings and 12-month price targets for each. The ratings are
NOT an input here and were not used: this program selects universe
members on market structure — options depth, cluster coverage, price
structure able to carry a doctrine contract — and measures edge
cross-sectionally. A "Buy / $535 target" changes nothing about whether
a detector fires. Six of the seven were declined on structure (below);
the useful question underneath was the general one — which names would
add genuine coverage — and this entry is the structurally-selected
answer to it.

**Claim.** The live doctrine as it stands today — ACTIVE_SETUPS =
(RS-02, H-25), with the adopted filters H2b / H4b / H15a — has
non-negative out-of-sample expectancy on the candidate names below, and
adding them does not degrade the combined universe's edge.

**What is different from H-23, stated in advance.** H-23 measured a
single setup (RS-02). The live book now runs two. This study therefore
pools the candidate trades from BOTH active setups and judges the
criterion on the pooled population — that is what the live scanner
will actually trade on these names. Per-setup splits are reported as
context, not as criteria (LAW 20): a cohort that passes pooled but
fails on one setup alone is still a PASS, and the reverse is still a
FAIL. No per-setup cherry-picking.

**The candidates, fixed now — selected on STRUCTURE only**, with live
measurements recorded at registration. Chain depth is the expiration
count and total listed contracts; the spread is measured on the CALL
whose delta is nearest 0.60 in the 2026-10-16 expiry, the doctrine's
21–60 DTE window:

| Ticker | Cluster | Sector ETF | Price | Mkt cap | Avg vol | Chain (exp/contracts) | 0.60δ strike | Bid/Ask | Spread |
|---|---|---|---|---|---|---|---|---|---|
| FCX | materials (new) | XLB | $72.73 | $104B | 7.3M | 17 / 1,094 | 70 (δ0.63) | 5.90 / 6.10 | **3.3%** |
| NEM | materials (new) | XLB | $128.09 | $135B | 5.7M | 16 / 1,580 | 125 (δ0.60) | 8.65 / 9.30 | **7.2%** |
| CCJ | energy (3rd) | XLE | $100.74 | $44B | 1.6M | 13 / 1,066 | 100 (δ0.55) | 6.65 / 6.90 | **3.7%** |
| NEE | utilities (new) | XLU | $83.43 | $174B | 10.8M | 16 / 1,022 | 82.5 (δ0.56) | 2.91 / 3.15 | **7.9%** |
| SO | utilities (new) | XLU | $87.17 | $101B | 7.2M | 16 / 1,002 | 87.5 (δ0.52) | 1.60 / 2.70 | 51.2% |
| DHI | homebuilders (new) | XLY | $142.75 | $40B | 1.7M | 16 / 1,108 | 140 (δ0.60) | 7.40 / 9.30 | 22.8% |
| LEN | homebuilders (new) | XLY | $79.60 | $20B | 2.3M | 16 / 978 | 80 (δ0.51) | 2.40 / 4.70 | 64.8% |
| UNP | rail (new) | XLI | $289.62 | $172B | 1.3M | 17 / 1,776 | 285 (δ0.60) | 11.50 / 13.30 | 14.5% |
| PLD | real_estate (new) | XLRE | $137.34 | $133B | 2.3M | 10 / 552 | 135 (δ0.60) | 5.20 / 6.40 | 20.7% |
| ISRG | health_devices (new) | XLV | $366.70 | $130B | 2.1M | 18 / 2,468 | 355 (δ0.64) | 21.80 / 25.60 | 16.0% |

Measurement provenance, recorded so the numbers can be audited: all
rows measured post-close via the TradingView feed — FCX, NEM, CCJ,
NEE, DHI, UNP, PLD, ISRG and every chain-depth figure on 2026-09-05
(41 DTE); SO and LEN prices and spreads on 2026-09-12 (34 DTE), which
is why their prices differ from the same-day snapshot of the others.
**Open interest is not in this feed and was therefore NOT verified** —
the registered MIN_OPEN_INTEREST = 100 floor is enforced live and
fail-closed inside `select_contract`, so an OI-thin contract is
refused at trade time rather than screened here. Stating that gap
rather than implying a check that did not happen.

**The spread bar is an OPTIONS-track criterion, not a study gate.**
This distinction is frozen now because it would otherwise be tempting
to blur later. The study measures the STOCK doctrine, which needs only
daily bars; a wide options chain cannot make a stock's breakout edge
better or worse. What a wide chain does mean is that the name cannot
carry the options overlay economically. So: a candidate that fails the
spread bar stays in the STUDY (its stock trades are measured like any
other) and, if the cohort is CONFIRMED and adopted, is tradeable as
stock while the options cycle's existing MAX_SPREAD_PCT check declines
its contracts on its own. No name is silently dropped from the study
for a reason the study does not measure.

**Pre-specified exclusion rule, fixed now.** Post-close marks are
systematically wider than intraday ones, so the table above is
suggestive, not conclusive. On the first OPEN-MARKET measurement taken
after this registration, any candidate whose 0.60-delta spread exceeds
MAX_SPREAD_PCT (10%) is recorded in a dated implementation note as
options-ineligible — and STAYS IN the study per the paragraph above.
On the evidence in hand, SO (51.2%) and LEN (64.8%) are the likely
ineligibles, with DHI, PLD, ISRG, UNP borderline; FCX, NEM, CCJ and
NEE already pass even on post-close marks. Naming the expected outcome
in advance is the point: it cannot be quietly revised after results.

**Cluster assignments, frozen, with the reasoning.** FCX (copper) and
NEM (gold) are both GICS Materials and share one `materials` cluster
even though their drivers differ — when in doubt, group, because the
§78 cluster cap is a risk control and the tighter reading is the safe
one. CCJ is GICS Energy (uranium) and joins `energy` beside XOM/CVX;
XLE is an imperfect RS_sector benchmark for a uranium miner and that
imperfection is recorded here rather than solved by inventing a
benchmark. UNP takes its own `rail` cluster: a railroad is not the
aerospace pair (BA/RTX) and not the airlines (AAL/DAL), and a
single-name cluster is honest here because nothing else in the
universe co-moves with it. ISRG takes `health_devices` rather than
joining `healthcare`: this is the argument JNJ lacked when it was
rejected at H-23 — an insurer (UNH) and two pharma names (ABBV, PFE)
do not share a device/robotics business's drivers. The risk in that
call is that a 4th healthcare name effectively widens healthcare
exposure past what one cluster cap would allow, and that risk is
stated here, in advance, as the cost of the choice.

**Evaluated and REJECTED at registration**, so the rejections cannot
be quietly revisited after results exist:

- **TSLA** — already in UNIVERSE since 2026-08-16. Not a candidate.
- **CPPMF** (Coppernico Metals, $0.29, $57M cap) — OTC, no listed US
  options, penny price. The PLUG rejection reasons compounded; Alpaca
  cannot trade it.
- **OUST** ($2.6B) and **AMBA** ($2.8B) — small caps, and semis is
  already 3-deep (NVDA/AMD/MU). The AVGO/INTC/QCOM rejection
  (concentration, not coverage) applies, plus every name in the
  universe to date is large or mega cap: the measured edge has never
  been tested on small caps, so adding them is a bet, not an extension.
- **CGNX** (4 expiries / 124 contracts, 15.4% at δ0.63) and **AME**
  (5 / 308, 21.3% at δ0.68) — the two thinnest chains screened by a
  wide margin; both would also sit in industrials beside BA/RTX.
- **FSLR** — GICS semiconductors, which makes it the 4th semi.
- **LIN** ($478) and **GLD** ($407) — a doctrine call on an underlying
  this expensive costs several times the 1% risk budget at current
  equity (the LLY/CAT precedent); GLD is additionally an ETP whose
  exposure NEM already covers.
- **NUE** (776K shares/day) — thinnest equity liquidity screened.
- **GM** — ev_auto 3rd (TSLA, F). **CRWD** — software 4th (PLTR, ORCL,
  CRM). **RCL / CCL** — cruise lines move on the same travel-demand
  story as the airlines cluster: correlation, not coverage.

**Data requirement.** One consistent daily-bar pull for BOTH arms —
every incumbent, every candidate, benchmark and all sector ETFs
(including the three new ones, XLB / XLU / XLRE) from the same vendor
in the same backfill, corrupt-bar guards active. A missing ticker
aborts the study (LAW 18); it never silently shrinks an arm. All ten
candidates are long-established listings, so unlike H-23 this cohort
has no young-listing caveat.

**Success criterion, fixed now.** Yearly expanding-window walk-forward
(`yearly_splits`, MIN_TRAIN_YEARS=3), test windows only, pooled across
ACTIVE_SETUPS as of registration, judged GROSS with the break-even
cost reported:

- **CONFIRMED (adoption-eligible)** if candidate-only pooled
  expectancy ≥ 0R at **n ≥ 50** closed candidate trades, AND
  combined-universe expectancy ≥ baseline − 0.05R (both arms from the
  same pull).
- **FAILED** if candidate-only pooled expectancy < 0R at n ≥ 50, OR
  the combined universe drags more than 0.05R below baseline.
- **INCONCLUSIVE** below n = 50, regardless of how the numbers look.

The n ≥ 50 bar is deliberately stricter than H-23's n ≥ 30: two pooled
setups over ten names will clear it easily, and it matches the bar the
two most recent registrations (H-24, H-25) already use. Tightening a
threshold before seeing results is the only direction it may move.

**Adoption is ALL candidates or NONE.** Per-ticker cherry-picking
after seeing results is prohibited — keeping only the names that
backtested well is selection bias wearing a lab coat. If the list
fails, a narrower list may be registered later as a NEW entry with a
written structural rationale, never by editing this one.

**What may NOT be done before the verdict.** The candidates do not
enter the tradeable `UNIVERSE`, the live scan, or the paper trader.
They exist only in `H26_CANDIDATE_UNIVERSE` (a fetch/study set), and
the study reads them only through its own runner. H-23's
`CANDIDATE_UNIVERSE` is NOT reused or mutated — it stays frozen for
that study's reproducibility.

**Status:** OPEN — registered, implementation and study to follow.

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

**Verdict (2026-08-28). CONFIRMED by the registered criterion.** The
study ran on a single 20-year pull (Actions run 33140266618, report
committed as `docs/reports/expansion_study.txt`), 18 expanding-window
test years:

    baseline (22)     n=  846  +0.133R  wr 52%  total +112.2R
    candidates only   n=  420  +0.135R  wr 52%  total  +56.7R
    combined          n=1,266  +0.133R  wr 52%  total +168.9R

Candidates-only expectancy ≥ 0R at n ≥ 30: met, 14x over the minimum
sample. Combined within 0.05R of baseline: met exactly — the delta is
zero at the reported precision, with the candidates fractionally ahead.
Frequency rose ~50% at unchanged per-trade edge, which is precisely the
mechanism the registration predicted and nothing more.

Honest notes that travel with the verdict: four candidates were
individually negative (PFE −0.126R, T −0.199R, V −0.169R, VZ −0.039R)
on per-ticker samples of 18–32 trades — noise-sized, reported for
context, and NOT actionable: per-ticker cherry-picking after seeing
results is prohibited above. This pull's baseline (+0.133R) also sits
above the H20 holdout figure (+0.117R) — a different vendor and a test
span that includes the flattering 2021–2026 years; the comparison
between arms is internally consistent, which is what the criterion
measures.

**Adoption (all 16 or none) is the operator's decision and has not
been taken as of this verdict.** The candidates remain non-tradeable
until the operator gives the word.

**Adoption (2026-08-28, operator decision):** ADOPTED, all 16, the
same day the verdict was recorded. The cohort entered `UNIVERSE` with
its registered clusters and sector benchmarks; the ten at-registration
rejections stayed out; the guard tests flipped from candidates-stay-
out to cohort-stays-exactly-as-registered. Live universe: 38 names.

---

## H-24 — Failed-breakdown reclaim, long

**Registered:** 2026-08-28, BEFORE any detector or study code exists.
The commit carrying this entry precedes the implementation commit; git
history is the timestamp.

**Provenance.** The fixed-capital philosophy's "forced participation"
proxy (`docs/FIXED_CAPITAL_PHILOSOPHY.md` §13: break of a level, failed
continuation, return through the level, normal volume, market not
contradicting, entry after the retest confirms), translated to daily
bars and to the long-only side this program is allowed to trade (§87):
the tradeable version of a failed move is a failed BREAKDOWN — sellers
break support, the break attracts no follow-through, and the reclaim
strands them. This is a mean-reversion-timed entry inside an intact
trend, mechanically different from RS-02's strength-breakout: RS-02
buys a stock making new highs; H-24 buys one that just survived a trip
below support. The two cannot fire on the same bar (a close above the
prior 20-day high cannot also be a reclaim of the prior 20-day low).

**Frozen rules — daily bars; every reused number imports the existing
constant, never re-types it:**

1. **Level:** the prior 20-day low (`RS02_BREAKOUT_LOOKBACK` window,
   excluding the latest bar — the mirror of RS-02's prior-high).
2. **Break:** at least one of the last 3 bars CLOSED below that level
   (a close, not a wick — "a visible break"). The 3-bar window is the
   one genuinely new number in this registration
   (`RECLAIM_WINDOW = 3`, CALIBRATE): the document's "holds on a
   retest" reads as days, not weeks, and it is frozen here before any
   result exists.
3. **Reclaim (the signal bar):** the latest bar closes back ABOVE the
   level.
4. **Volume:** signal-bar relative volume ≥ 1.0 — the document's "at
   least normal," which is the existing RS-01 volume standard.
5. **Market context:** benchmark return ≥ `RS02_BENCH_MIN_RETURN`
   (−2%) — "the broader market is not contradicting."
6. **Trend context — frozen choice, stated in advance:** H2b applies
   (stock above its own 200-day SMA; a reclaim in a broken long-term
   trend is a falling knife, not trapped sellers). H4b does NOT apply:
   requiring +10% 12-1 momentum would collapse the population into
   near-RS-02 extension, and the mechanism under test is trend-intact
   dip-survival, not extension. Fails closed under 200 bars of history.
7. **Stop:** the standard 5-day swing-low invalidation every setup
   already uses (`INVALIDATION_LOOKBACK`) — the breakdown episode's low
   by construction. **Entry:** next open, H15a limit cap. **Exits:**
   the doctrine bracket unchanged — +3R target, stop, 15-bar time exit.
   Zero new exit machinery, so exits are not a hidden degree of
   freedom.

**Success criterion, fixed now.** Yearly expanding-window walk-forward
(`yearly_splits`), test windows only, on the tradeable UNIVERSE as of
the study run (recorded in the report), one consistent data pull,
corrupt-bar guards active, judged GROSS with the break-even cost
reported (consistent with every prior verdict):

- **CONFIRMED (adoption-eligible)** if aggregate out-of-sample
  expectancy ≥ 0R at **n ≥ 50** closed trades (the philosophy's own
  minimum initial sample), AND expectancy is positive in at least half
  of the judged test windows (a window counts when it holds ≥ 10
  trades) — one lucky year must not carry the verdict.
- **FAILED** if aggregate < 0R at n ≥ 50, or fewer than half the
  judged windows are positive.
- **INCONCLUSIVE** below n = 50, regardless of how the numbers look.

**What CONFIRMED does and does not do.** It makes the setup
adoption-ELIGIBLE. Activation into `ACTIVE_SETUPS` is a separate
operator decision (§60), one new live setup at a time per the
philosophy's own sequencing rule, sharing `MAX_OPEN` and the cluster
caps with RS-02 — never a private allocation. A FAILED verdict stays in
this file; a re-parameterized variant registers as a new entry.

**Status:** OPEN — registered, implementation and study to follow.

**Implementation notes (2026-08-28, added after the fact — the frozen
text above is NOT edited).** Two places the prose needed an exact
reading, resolved before any result existed:

1. *The level window ends before the reclaim window.* Read literally,
   "the prior 20-day low excluding the latest bar" would include the
   break bars themselves — and a bar can never CLOSE below the minimum
   LOW of a window containing itself, making rule 2 unsatisfiable. The
   only satisfiable reading, implemented: the level is the 20-day low
   of the window ending immediately before the last `RECLAIM_WINDOW`
   bars, so the level predates the break it must be broken by.
2. *"The last 3 bars"* means the 3 bars immediately preceding the
   signal bar (the signal bar itself closed above and cannot be the
   break).
3. The H2b trend condition is embedded IN the detector, so every
   research run of this setup carries it — there is no unfiltered
   variant to accidentally study.

**Verdict (2026-09-02). CONFIRMED by the registered criterion.** The
study ran on a single 20-year pull (Actions run 33236497138, report
committed as `docs/reports/setup_study.txt`), 18 expanding-window test
years on the 38-name universe, H15a entry cap applied:

    n=604   +0.123R   wr 45%   total +74.3R   (GROSS)
    net at 5bp: +0.088R    linear break-even ~18bp

Aggregate ≥ 0R at n ≥ 50: met, 12x over the minimum sample. Breadth:
positive expectancy in 10 of 18 judged windows (every window held ≥ 10
trades) — the ≥-half clause met. The committed overlap accounting:
2 of 604 filled trades (0%) share a (ticker, signal-date) with RS-02 —
the registration's mechanical-distinctness claim held; this is added
coverage, not a re-timing of RS-02's trades.

Honest notes that travel with the verdict: win rate is 45% versus
RS-02's 52% — the edge is carried by payoff, not hit rate, so losing
streaks will run longer than the live book's; and the worst window
(2014: −0.43R on 42 trades) shows the setup can lose for a full year.
Per-window numbers are context, not criteria (LAW 20).

**CONFIRMED makes H-24 adoption-ELIGIBLE only. No activation decision
has been taken as of this verdict** — entry into `ACTIVE_SETUPS` is
the operator's separate call, one live setup at a time, sharing
`MAX_OPEN` and the cluster caps with RS-02.

**Activation status (2026-09-02, operator decision):** NOT activated.
The operator took H-25 for the one-at-a-time slot; H-24 stays
CONFIRMED and adoption-eligible, activatable only by a later separate
decision.

---

## H-25 — Pullback-and-reclaim, long

**Registered:** 2026-08-28, same commit-order discipline as H-24.

**Provenance.** The fixed-capital philosophy's priority-1 strategy
(`docs/FIXED_CAPITAL_PHILOSOPHY.md` §5): "identify a security in an
established daily trend; wait for a controlled pullback toward a
support or moving-average zone; enter only after price reclaims the
level with acceptable volume and market context; define invalidation
below the recent swing low." Buying strength on a discount inside a
trend, versus RS-02's buying strength at new highs — entry timing is
the difference under test.

**Frozen rules — this registration introduces NO new numeric
parameter; every threshold is an existing constant reused:**

1. **Established trend:** H2b AND H4b, both adopted filters verbatim —
   close above the 200-day SMA and 12-1 momentum ≥ +10%. "Established
   daily trend" is exactly what they already measure. Fails closed
   under ~13 months of history.
2. **Controlled pullback:** at least one of the last 5 bars
   (`INVALIDATION_LOOKBACK` window) CLOSED below the 20-day SMA
   (`RS01_STRUCTURE_SMA` — the moving-average zone the codebase
   already defines).
3. **Reclaim (the signal bar):** the latest bar closes back ABOVE the
   20-day SMA.
4. **Volume:** signal-bar relative volume ≥ 1.0 ("acceptable volume,"
   the RS-01 standard).
5. **Market context:** benchmark return ≥ `RS02_BENCH_MIN_RETURN`.
6. **Stop:** the standard 5-day swing-low invalidation (the pullback
   low by construction). **Entry:** next open, H15a cap. **Exits:**
   doctrine bracket unchanged.

**Overlap accounting, committed in advance:** the study reports how
many H-25 signals coincide with an RS-02 signal on the same
ticker-date. A setup that mostly re-times RS-02's trades adds
correlation, not coverage, and the report must say which it is.

**Success criterion, fixed now:** identical machinery and thresholds to
H-24 — CONFIRMED at aggregate OOS expectancy ≥ 0R with n ≥ 50 AND
positive in ≥ half of judged (≥10-trade) windows; FAILED and
INCONCLUSIVE as in H-24; GROSS with break-even reported; universe and
data-pull rules as in H-24. Activation is a separate operator decision,
one live setup at a time.

**Status:** OPEN — registered, implementation and study to follow.

**Implementation notes (2026-08-28, added after the fact — the frozen
text is NOT edited).** The 20-day SMA is the ROLLING SMA evaluated at
each bar (a pullback bar is compared to the SMA as of that bar, not
today's); "the last 5 bars" means the 5 bars immediately preceding the
signal bar; both trend conditions (H2b and H4b) are embedded in the
detector itself. The committed overlap report is measured on FILLED
trades' (ticker, signal-date) pairs — the backtester records tickered
signal dates only for fills — a slightly narrower measure than "all
signals," disclosed here rather than silently substituted. Shared
corner case for both entries, resolved toward no verdict: n ≥ 50 with
NO single window reaching 10 trades leaves the breadth clause
unjudgeable and returns INCONCLUSIVE, never a convenient pass.

**Verdict (2026-09-02). CONFIRMED by the registered criterion.** Same
study run as H-24 (Actions run 33236497138, one consistent pull,
report `docs/reports/setup_study.txt`):

    n=2,009   +0.116R   wr 47%   total +232.4R   (GROSS)
    net at 5bp: +0.086R    linear break-even ~19bp

Aggregate ≥ 0R at n ≥ 50: met, 40x over the minimum sample. Breadth:
positive expectancy in 12 of 18 judged windows. The overlap accounting
committed in advance: 70 of 2,009 filled trades (4%) share a
(ticker, signal-date) with RS-02 — this is coverage, not correlation;
the setup is not re-timing RS-02's trades.

Honest notes that travel with the verdict: H-25 fires roughly 1.6x as
often as RS-02 itself on the same universe (2,009 vs 1,266 filled
test-window trades in the expansion study's combined arm) — by trade
count it would be the dominant setup if activated, which raises the
practical weight of its bad regimes: 2022 was −0.35R on 47 trades
(pullback-buying in a downtrend year hurts even behind H2b + H4b),
and the two most recent windows sit near zero (2025 +0.09R,
2026 −0.14R partial). Per-window numbers are context, not criteria
(LAW 20).

**CONFIRMED makes H-25 adoption-ELIGIBLE only. No activation decision
has been taken as of this verdict** — and the philosophy's own
sequencing rule (one new live setup at a time) means H-24 and H-25
cannot both activate in the same step even if the operator wants both
eventually.

**Activation (2026-09-02, operator decision):** ACTIVATED — H-25
entered `ACTIVE_SETUPS` alongside RS-02, chosen over H-24 for the
first slot (larger sample, broader window breadth, fastest forward
evidence). It shares `MAX_OPEN`, sizing, the H15a cap, and every
survival gate with RS-02 — no private allocation. H-24 remains
CONFIRMED and adoption-eligible but NOT active; per the sequencing
rule it may activate only by a later, separate operator decision,
naturally after H-25 has forward fills to judge.

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
