# Market Theory Dossier — Evidence, Institutional Mechanics, and What We Exploit

Knowledge base for the RS Options Engine. Everything here is graded by
evidence quality, because trading content mixes replicated science with
folklore freely and the difference is the whole game. Compiled from the
academic literature and market-microstructure research; each claim names
its source so it can be checked.

Reading rule: **Tier 1 = build on it. Tier 2 = mechanically real, exploit
carefully. Tier 3 = tools, not signals. Folklore = ignore.**

---

## TIER 1 — Robust, replicated academic findings

### 1.1 Cross-sectional momentum (the foundation under RS-02)
Jegadeesh & Titman (1993), replicated across decades, countries, asset
classes: stocks that outperformed peers over the past 3–12 months keep
outperforming over the next 3–12 months. This is *relative strength* —
our engine's namesake. It is arguably the most robust anomaly in finance.
- Horizon matters: the effect lives at **weeks-to-months**, not days.
- Our RS-02 (persistent RS + breakout, ~10-day hold) sits at the short
  edge of the documented window — consistent with our +0.25R finding.

### 1.2 Short-term reversal (the warning label on momentum)
Lehmann (1990), Jegadeesh (1990): over ~1 day to 1 month, returns tend to
**reverse**, not continue. Buying a stock because it spiked *yesterday*
is statistically a losing trade on average.
- Directly relevant to any "shorter day trades on momentum" ambition:
  at the 1-day horizon the documented drift points the WRONG way.
- Testable guard (H6 below): penalize entries where most of the RS came
  from a single day's spike.

### 1.3 52-week-high anchoring
George & Hwang (2004): proximity to the 52-week high predicts forward
returns better than plain momentum. Mechanism: traders anchor on the
high, under-react as price approaches it, and the drift resumes after
the breakout. This is the academic backbone of breakout trading.
- Testable (H1): condition RS-02 on distance to the 52-week high.

### 1.4 Post-earnings announcement drift (PEAD)
Ball & Brown (1968), Bernard & Thomas (1989): prices drift in the
direction of an earnings surprise for weeks afterward. Real, persistent,
but shrinking in large caps. For a long-options engine the catch is IV
crush around the event (spec §26 Catalyst Protocol exists for this).

### 1.5 Momentum crashes (why RS-01 died is not a coincidence)
Daniel & Moskowitz (2016): momentum strategies suffer violent crashes
in panics and especially in sharp rebounds after bear markets. Our
backtest replicated this in miniature — RS-01 lost −34.8R in 2022 alone.
Momentum needs a **regime filter**, which is exactly what H2 tests.

### 1.6 The square-root law of price impact (why breakout drift exists)
Microstructure research (Bouchaud, Almgren, and the metaorder
literature): institutional "metaorders" are far too large to execute at
once, so they are split into thousands of child orders over days or
weeks. Measured impact grows like the **square root** of order size, and
price drifts persistently while the metaorder works.
- This is the *mechanical cause* behind our RS-02 finding that 119/160
  exits were time exits at +0.33R: a breakout on 2× volume is often the
  visible edge of a metaorder, and the 10-day drift is the rest of it
  executing. We are not predicting; we are drafting behind size.

---

## TIER 2 — Mechanically real institutional flows

### 2.1 How institutions actually execute
- Benchmarked to **VWAP/TWAP** by execution algos. Consequences: the
  U-shaped intraday volume curve (heavy open/close, dead midday), and
  VWAP acting as an intraday reference level that algos buy below / sell
  above.
- **Anchored VWAP** from a catalyst day (breakout, earnings) approximates
  the average cost basis of the institutions that accumulated that day —
  a level they defend on pullbacks. Practitioner tool (Brian Shannon),
  but mechanically grounded. Testable with our new minute data (H3).
- The **closing auction** carries ~10% of daily volume — institutional
  prints. The first 30 minutes is price discovery; midday is thin; the
  last hour is institutional execution.

### 2.2 Options dealer hedging (gamma flows)
Market makers who sell options hedge continuously. Near strikes with
large open interest, their hedging *dampens* movement ("pinning") when
they are long gamma and *amplifies* it when short gamma. Around monthly
expiration these flows (gamma/charm/vanna) are large enough to matter.
- For us at current scale: context, not signal. Worth knowing that the
  underlying can go quiet near a big round-number strike into expiry.

### 2.3 Calendar flows
Month-end/quarter-end pension rebalancing, index additions/deletions,
option expiration weeks — documented, calendar-predictable pressure.
Cheap to encode later as context flags in the macro calendar.

### 2.4 Institutional constraints ARE our edge
- Institutions cannot buy junk (mandates), cannot take 10-day
  unbenchmarked bets easily (career risk), and cannot enter or exit
  without moving the price (size).
- We can. A small account's only structural advantages: **zero market
  impact, no career risk, and horizon freedom.** Every design choice
  should protect these. Note our own data already whispered the mandate
  point: the only consistent RS-02 losers were AAL and BAC — the
  weakest-quality names in the universe, the ones real institutional
  momentum flows avoid (H4).

---

## TIER 3 — Indicators: what they are and are not

**The uncomfortable truth:** every indicator is arithmetic on past price
and volume. It contains no information the chart didn't already have.
Their legitimate uses are (a) encoding rules objectively so they can be
backtested, (b) marking focal points other traders watch (self-fulfilling
levels), and (c) filtering regimes. As *predictors*, the evidence is thin:
Brock, Lakonishok & LeBaron (1992) found MA rules predictive, but
Sullivan, Timmermann & White (1999) showed much of that was data
snooping, and post-1990 out-of-sample results are weak for raw signals.

| Indicator | Honest value | In our system |
|---|---|---|
| Moving averages (20/50/200d) | Weak as signals; **useful as regime filters** (Faber 2007: long only above the 10-month SMA cuts drawdowns dramatically) and as watched focal points (200d, golden cross) | RS-01 used SMA20 structure; H2 tests a 200d regime filter |
| ADX | Trend-strength filter — helps avoid chop; not directional | Already in HoneyDrip's entry |
| ATR | Not a signal at all — a **risk ruler**. Best use: stop distance and position sizing | Exit study's `atr_trail` policy |
| RSI | Mild mean-reversion signal at short horizons in ranges; "overbought" in a trend is meaningless | Not used; low priority |
| MACD | A derivative of two MAs — adds nothing beyond them | Skip |
| Bollinger bands | Volatility clustering is real: squeezes (contraction) do precede expansion; direction is NOT predicted | Related to our IV-rank work |
| Volume | **The most informative "indicator"** — the only one that carries institutional footprints (§1.6) | Core of RS-02 (2× volume breakout) |

### On "confluence"
Retail confluence usually stacks RSI + MACD + Stochastics — three
transformations of the *same price series* agreeing with themselves.
That is pseudo-confirmation, and spec §33 (correlation control) already
bans it. **Real confluence is independent information sources agreeing:**

```
price structure (breakout)     — what price did
+ volume expansion             — is size participating
+ relative strength vs SPY     — is it leadership or beta
+ volatility regime (IV rank)  — is the option fairly priced
+ institutional level (AVWAP / 52wk high) — where size defends
+ quality/fundamentals         — can institutions own it
```

Six independent axes. Our opportunity score already spans four of them;
H1–H4 add the remaining two. That is confluence done honestly.

---

## FOLKLORE — decoration, not evidence

Named without endorsement so they are recognized when encountered:
indicator-only "confluence" stacks (see above), most chart patterns as
usually traded (head-and-shoulders etc. — weak/unstable evidence; the
one pattern family with academic support is the breakout-from-range /
52-week-high family we already trade), Fibonacci retracement levels
(no documented edge beyond being watched), Elliott waves (unfalsifiable),
"smart money" narratives without a flow mechanism attached.

---

## Ranked, testable hypotheses (feeds spec §72)

| # | Hypothesis | Basis | Data needed | Cost |
|---|---|---|---|---|
| H1 | RS-02 conditioned on proximity to 52-week high improves expectancy | §1.3 George-Hwang | daily (have) | free |
| H2 | 200-day SMA regime filter (long only above) removes most 2022-style losses | §1.5, Faber | daily (have) | free |
| H3 | Anchored VWAP from breakout day works as trail/re-entry level | §2.1 | minute (have, 60d) | free |
| H4 | Quality screen (profitability/leverage) removes the AAL/BAC failure mode | §2.4 | fundamentals (EDGAR/free) | free |
| H5 | Earnings blackout: skip entries within N days of earnings | §1.4 + §26 | earnings calendar (free) | free |
| H6 | One-day-spike guard: penalize RS driven by a single bar | §1.2 reversal | daily (have) | free |

Discipline unchanged: every hypothesis is judged on the train/test split
like the exit study. A hypothesis that only improves the train window is
noise (LAW 12/20).

---

## The synthesis — our theory of the trade

1. Institutions must deploy size; size cannot move at once (§1.6).
2. Their accumulation surfaces as: volume expansion + breakout +
   persistent relative strength — exactly RS-02's trigger.
3. The profit is the **drift while their order finishes** — days, not
   minutes (which is why our time exits capture it and why 1-day
   "momentum" chasing fights the reversal effect instead).
4. Our structural edge is being small: no impact, no benchmark, free
   horizon. We draft behind size; we do not race it (§38's latency-taker
   declaration is the same idea at the microstructure level).
5. Filters that align us with institutional constraints — quality,
   regime, distance-to-highs, earnings awareness — should concentrate
   the edge. Each one gets tested, none gets assumed.

*Sources are canonical papers cited inline (Jegadeesh-Titman 1993;
Lehmann 1990; George-Hwang 2004; Ball-Brown 1968; Bernard-Thomas 1989;
Daniel-Moskowitz 2016; Brock-Lakonishok-LeBaron 1992;
Sullivan-Timmermann-White 1999; Faber 2007; metaorder impact literature
per Bouchaud et al.). Compiled 2026-08-15 from trained knowledge; web
verification unavailable in the compiling session — treat exact figures
as approximate and the directional findings as the load-bearing content.*
