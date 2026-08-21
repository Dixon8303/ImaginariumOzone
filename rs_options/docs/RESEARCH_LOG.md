# Research Log — dated verdicts with evidence

Every production-affecting decision, with the data that earned it.
Append-only; never rewrite a verdict, supersede it with a new entry.

---

## 2026-08-14 — First 5y real-data backtest (394 trades, Stooq daily)

- **RS-01 KILLED** (§60 L2): −0.145R over 234 trades, max DD −47R.
  Autopsy: −34.8R in 2022 alone; 26 gap-through-stop exits averaging
  −2.07R. Structural failure (buys weakness in bear regimes), not
  parametric. Remains in the backtester for re-research.
- **RS-02 retained**: +0.25R over 160 trades, max DD −4.4R, positive
  every year 2023–2026, 13/18 tickers profitable. Losers concentrated in
  the weakest-quality names (AAL, BAC) → hypothesis H4.

## 2026-08-15 — Walk-forward validation (§51), RS-02, fixed parameters

Edge held in **3/3 judged out-of-sample windows**:
- 2024: n=47, +0.371R, 60% wr
- 2025: n=44, +0.167R, 61% wr
- 2026 (partial): n=18, +0.057R, 44% wr

Verdict: validated, with a softening trend that stays under watch
(2026 sample is small). Clears the §51 hurdle for continued co-pilot use.

## 2026-08-15 — Exit-policy study (§41–§42), 150 real signals

| Policy | Train (n=98) | Test (n=52) |
|---|---|---|
| baseline 2R/10-bar | +0.295R | **+0.026R** |
| **wide 3R/15-bar** | **+0.384R** ← train winner | **+0.181R** ← confirmed |
| atr_trail 2×ATR14 | +0.298R | +0.198R |
| breakeven at +1R | +0.276R | +0.017R |

Avg path shape at the old horizon: MFE +0.90R, MAE −0.48R — winners run
past the old 10-day clock (consistent with metaorder drift, see
MARKET_THEORY §1.6).

**ADOPTED: "wide" — 3R target, 15-trading-day hold** (train winner,
confirmed on test per the pre-registered rule). Consequence: minimum
option DTE raised 7 → 21 so contracts outlive the hold.

**Watch list, not adopted:** atr_trail scored best on test (+0.198R) but
was not the train winner; choosing it post-hoc would be peeking. Re-test
it as a fresh hypothesis when new out-of-sample data accumulates.

**Open hypotheses queue (from MARKET_THEORY):** H1 52wk-high proximity,
H2 200d regime filter, H3 anchored VWAP (minute data now on disk —
27 tickers, ~16k bars each), H4 quality screen, H5 earnings blackout,
H6 one-day-spike guard.

## 2026-08-15 — H7 intraday lab built (ORB + intraday momentum)

Operator greenlit the shorter-horizon research track. Built, not yet run
on real data:

- **Deep minute backfill**: `python -m mve.alpaca_data --minute-deep`
  pulls ~2 years of 1-min bars (SPY, QQQ by default) in 90-day chunks
  into the idempotent intraday store. An interrupted run keeps its
  progress.
- **`python -m mve.intraday_study`** runs two documented effects through
  the same pre-registered discipline as the exit study (first 70% of
  sessions = TRAIN, rest = TEST, verdicts CANDIDATE / REJECT / NOISE /
  INCONCLUSIVE with min-n guards 40/20):
  - **ORB**: 15-min opening range; 1-min close beyond it enters at the
    next open, stop at the opposite bound, exit stop-or-session-close.
    R-multiples, conservative fills, 2 bps friction.
  - **Intraday momentum** (Gao/Han/Li/Zhou 2018): sign of the first-30-min
    return positions the last 30 minutes only. Reported in bps net of
    friction.

Boundaries restated: entries are on 1-min closes, not ticks — §38
EDGE_FASTER_THAN_PIPE still bars anything speed-competitive. A CANDIDATE
verdict earns a walk-forward pass and an operator decision, never
auto-adoption. No trading path exists in any of this code.

**Awaiting**: operator's `mve.hypotheses` + updated `mve.exit_study`
reports (H1/H2 verdicts, H3 avwap_trail vs wide) and the first
`--minute-deep` + `intraday_study` run.

## 2026-08-15 — Hypothesis verdicts: H1/H2 entry filters, H3 AVWAP exit

Operator ran `mve.hypotheses` and the updated `mve.exit_study` on the
27-ticker history (CONTROL: train n=110 +0.346R, test n=57 +0.229R).

| Variant | Train | Test | Verdict |
|---|---|---|---|
| H1a 52wk-high 5% | +0.377R (n=68) | +0.225R (n=43) | **NOISE** |
| H1b 52wk-high 10% | +0.384R (n=78) | +0.228R (n=49) | **NOISE** |
| H2a SPY > 200d | +0.444R (n=91) | +0.207R (n=55) | **NOISE** |
| H2b stock > 200d | +0.415R (n=95) | +0.239R (n=53) | **ADOPT-CANDIDATE** |

- **H1 rejected (both widths)**: RS-02's breakout condition already
  selects stocks near their highs — the extra filter mostly just cut
  sample (filtered 82–111 signals) without improving out-of-sample
  expectancy. The George-Hwang effect is likely already embedded in the
  setup, not absent from the market.
- **H2a rejected**: the market-level regime stitch improved train
  strongly (+0.444R) but *degraded* test — textbook overfit shape.
- **H2b (stock above its own 200-day)**: the only variant that improved
  both windows. Honest read: the test margin is thin (+0.010R on n=53)
  — real shrinkage from the +0.069R train margin. Mechanism is sound
  (regime filter on the instrument actually traded; MARKET_THEORY §5)
  and the filter is cheap (skipped 37 signals over ~5y) and fail-closed.
  Encoding awaits the operator's word per LAW 12/20.

**H3 anchored-VWAP trail: REJECTED.** avwap_trail scored train +0.205R
/ test +0.162R — *below* the adopted wide policy on both windows (train
+0.384R, test +0.181R) and the worst train performer of all five
policies. The daily-bar AVWAP ratchets too close to price and cuts
winners early (wr 49%/42%). The idea may deserve a minute-data retest
once H7 history accumulates, but as specified it is falsified. Wide
(3R / 15-bar) remains the adopted exit; atr_trail stays on the
watch-list (best test again at +0.198R, still not the train winner).

## 2026-08-15 — H2b ADOPTED (operator decision)

The operator adopted H2b: RS-02 entries now require the stock above its
own 200-day SMA, fail-closed under 200 bars of history. Encoded in
`mve/setups.py` as `ENTRY_FILTERS`, applied on the live-doctrine path
of `detect_all` only — research tools that pass `active` explicitly
still see raw signals, so future hypothesis studies keep an unfiltered
CONTROL. The hypothesis module now imports the same `above_sma`
implementation the scanner runs, so the studied filter and the live
filter cannot drift apart. Playbook updated. Cost in history: 37
filtered signals over ~5 years.

## 2026-08-15 — H7 verdicts: ORB and intraday momentum both fail

First run on real minute history: 500 sessions (~2 trading years,
2024-08 → 2026-08) of SPY and QQQ, ~393k minute bars, 2 bps friction,
pre-registered 70/30 chronological split.

| Study | Ticker | Train | Test | Verdict |
|---|---|---|---|---|
| ORB 15-min | SPY | +0.054R (n=349) | −0.014R (n=150) | **NOISE** |
| ORB 15-min | QQQ | +0.037R (n=349) | −0.064R (n=150) | **NOISE** |
| Intraday momentum | SPY | −1.26 bps (n=340) | −2.75 bps (n=150) | **REJECT** |
| Intraday momentum | QQQ | −0.44 bps (n=343) | −3.30 bps (n=150) | **REJECT** |

Reads:
- **ORB fired almost every session** (349 of ~350 train days) — the
  15-min range breaks daily, so the setup has no selectivity; win rates
  39–43% with the opposite-bound stop produce expectancy ~0 on train
  and negative out-of-sample. Chop eats the edge.
- **The Gao/Han/Li/Zhou first-30→last-30 effect is negative even
  in-sample** on 2024–2026 data. The paper's sample ended years before
  publication (2018); this is the textbook post-publication decay of a
  documented anomaly. It is not there to harvest at retail friction.
- Friction here was a *generous* 2 bps constant; live costs are worse,
  so the true numbers are below these.

**Consequence: the intraday track is CLOSED for now.** This was the
data's answer to the operator's 5-min-to-3-hr day-trading question —
tested honestly, on the two most liquid instruments, and it failed both
ways. The validated edge remains RS-02 on the daily timeframe with the
wide exit and the H2b regime filter. The 500-session minute store stays
on disk for future use (e.g., a minute-precision AVWAP retest of H3, or
sizing entry slippage assumptions for the daily setups).

**Remaining queue:** H4 quality screen, H5 earnings blackout,
H6 one-day-spike guard — all on the daily track.

## 2026-08-16 — Hypothesis round 2 built: H4 quality + H6 spike guard

`mve.hypotheses` now runs round 2. Methodology change: variants are
tested INCREMENTALLY — every variant includes the adopted H2b regime
filter, and verdicts compare against BASELINE_H2b, not the raw CONTROL.
A filter earns adoption only by improving the system actually being run.

- **H4 momentum-quality**: require positive (H4a) or ≥10% (H4b) trailing
  12-1 month return at signal time — a mechanical, point-in-time quality
  proxy. The motivating forensics (AAL/BAC the only consistent RS-02
  losers) came from in-sample inspection, so tickers are never named;
  the screen must earn adoption on the pre-registered train/test rule.
- **H6 one-day-spike guard**: skip signals whose breakout day itself
  gained ≥5% (H6a) / ≥8% (H6b) — don't chase a stretched move into the
  short-term-reversal window.
- **H5 earnings blackout: DEFERRED** — needs per-ticker earnings dates;
  no free offline source wired yet.

Awaiting the operator's next `python3 -m mve.hypotheses` run (report now
lands in docs/reports/hypotheses.txt).

## 2026-08-16 — Round-2 verdicts: H4b ADOPTED, H6 dead

Operator ran round 2 (verdicts vs BASELINE_H2b, train n=95 +0.415R /
test n=53 +0.239R):

| Variant | Train | Test | Verdict |
|---|---|---|---|
| H4a mom > 0 | +0.482R (n=62) | +0.248R (n=43) | ADOPT-CANDIDATE |
| H4b mom ≥ 10% | **+0.516R** (n=50) | **+0.324R** (n=34) | **ADOPTED** |
| H6a no-spike 5% | +0.483R (n=76) | +0.136R (n=47) | NOISE |
| H6b no-spike 8% | +0.405R (n=89) | +0.196R (n=50) | REJECT |

- **H4b adopted by operator decision** — the strongest single finding so
  far: monotone dose-response (tighter screen → higher expectancy in
  BOTH windows), which is the signature of a real effect rather than a
  fitted one. RS-02 live entries now require the 200-day regime AND
  12-1 momentum ≥ +10%, both fail-closed. Canonical implementations
  moved to `setups.py`; `hypotheses.py` imports them. Cost: roughly
  half the signals (~84 vs 148 over 5y) — fewer, better trades.
- **H6 spike guard rejected** — a strong breakout day is not a defect
  of this setup; skipping spike days destroyed test expectancy (H6a
  +0.136R). The short-term-reversal concern does not apply at this
  holding horizon.
- The motivating AAL/BAC forensics resolved honestly: the mechanical
  screen confirms the quality hypothesis without ever naming tickers.

**Queue:** H5 earnings blackout (needs earnings-date source). Doctrine
now: RS-02 + wide exit (3R/15-bar) + H2b regime + H4b quality.

## 2026-08-16 — Trade journal built (operator's broker history)

`python -m mve.trade_journal` reads the operator's Schwab/thinkorswim
transactions export (dropped in `data/`, which is now **explicitly
gitignored** along with `*Transactions*.csv` anywhere — the export
contains the account number and this repo is public). FIFO round-trip
matching, direction-agnostic (longs and shorts), option multiplier and
fees handled via amount-based unit cash. Reports the same statistics
the engine is held to: win rate, avg win/loss, expectancy (in $ and %
of position cost — no stop data, so no R), profit factor, max drawdown,
day-trade share, monthly P&L, and **net contributions separated from
trading P&L** so account growth is attributed honestly. Aggregate-only
report to docs/reports/trade_journal.txt via the report bridge.

Purpose: measure the operator's discretionary day-trading record
(250 → 3,500 claim) with the machine's own yardstick before deciding
whether any of that behavior deserves encoding.

## 2026-08-16 — Operator's broker history measured (trade journal)

First run of `mve.trade_journal` on the operator's 3-year thinkorswim
export (aggregates in docs/reports/trade_journal.txt): 1,429 round
trips, 85% day trades, 58% win rate — but avg win $19.64 vs avg loss
$33.15 → expectancy −$2.64/trade, profit factor 0.81, total −$3,770
with $2,386 of that paid in fees. Two hot months (2024-02/03, +$1,921)
were followed by −$2,790 across 2024-04 and 2024-07. No deposits appear
in this export, so the remembered 250→3,500 run likely lived in a
different account (Robinhood) or as peak unrealized equity.

Diagnosis matches the intraday studies exactly: direction-picking is
fine (58% > coin flip); the losses come from exit asymmetry (winners
cut at ~0.6x the size of losers) and friction on 1-day holds. These are
the two failure modes the adopted doctrine already corrects (3R wide
target, defined invalidation stops, fewer/filtered entries). Personal
evidence now agrees with market evidence: the daily-timeframe system is
the path.

## 2026-08-16 — Hard limit added: no long premium on volatility ETPs

Adopted from the broker-history forensics, on MECHANISM rather than
data mining: VXX-class products (VXX, UVXY, and kin) decay structurally
from contango roll, so long calls fight a built-in downward drift on
top of theta. The operator's record illustrates it — 18 VXX trades at a
67% win rate still lost $857, with the three longest holds (60–68 days)
accounting for ~$871 — but the rule stands on the product's structure,
not on those 18 trades. Encoded in the playbook's hard-limits table.
The 18-ticker live universe never contained these products; this closes
the door on adding them.

The rest of the outside analysis of the broker CSV was reviewed and
mostly declined: the "intraday edge" claim is confounded by the
disposition effect (duration is an effect of outcomes, not a cause —
winners cashed same-day, losers carried), and the per-ticker / per-DTE
"sweet spots" are small-n bucket mining with no monotone structure. Any
of those ideas can still earn adoption the normal way: pre-registered,
train/test, vs the current doctrine baseline.

## 2026-08-16 — H5 built (earnings blackout) + universe expanded to 22

**H5 earnings blackout, round 3 of the hypothesis lab.** New
`mve.earnings` fetches historical reported dates from Alpha Vantage
(ALPHAVANTAGE_API_KEY env var; free tier fits the stock list in one
run) into data/earnings/. `mve.hypotheses` round 3 tests two
pre-registered blackout widths — 3 and 21 calendar days ahead of the
signal — against BASELINE_DOCTRINE (H2b + H4b). Caveat stated before
the data: breakouts sometimes happen BECAUSE of earnings momentum, so
the blackout may cut winners as easily as losers. Tickers without an
earnings file pass untouched (ETFs). Awaiting the operator's run.

**Universe: 18 → 22 tickers.** Added TSLA (ev_auto/XLY), MU (semis/SMH),
PLTR (software/XLK), SBUX (consumer/XLY) on STRUCTURAL criteria — deep
options liquidity and cluster coverage — explicitly NOT on the
operator's per-ticker P&L (small-n noise both directions; the same
standard that declined the "natural strengths" list). Declined: SPXW
(index options, outside §87 scope), VXX (banned ETP), PLUG (price and
spread structure unfit for long calls). Required follow-up on the
operator's Mac: `python3 -m mve.backfill` (pulls the new tickers'
history), then re-run `python3 -m mve.backtest` and
`python3 -m mve.walkforward` — the strategy-level edge must be
confirmed on the expanded universe before the new names carry live
trust. Earnings fetch auto-includes the new stocks (20 ≤ 25/day cap).

## 2026-08-16 — Autonomous PAPER shadow track (§87)

Operator asked for the daily scan to run itself and for paper execution
on Alpaca. Built `rs_options/paper/` + `.github/workflows/paper_trader.yml`
(21:35 UTC weekdays — after the NYSE close year-round, runs on GitHub's
servers so the Mac need not be on):

1. Fetches fresh daily bars for the 22-ticker universe (Alpaca IEX).
2. Runs the adopted live doctrine via `detect_all` — the same code path
   the operator's manual scan uses, so paper and live can never diverge.
3. Paper-trades survivors as the UNDERLYING equity: market buy queued
   for the next open (matching the backtester's next-open entry),
   bracket stop at invalidation, target at +3R, time exit at 15
   trading days. Sizing: 1% equity risk, 5% notional cap, 8 positions.
4. Commits `docs/reports/paper_trading.txt` — today's signals with
   entry/stop/target AND the playbook's option guidance for the
   operator's discretionary Robinhood execution, plus open positions,
   closed trades in R, and the cumulative record.

Guardrails: `PAPER_URL` is a hard-coded constant (no parameter, no env
override — there is no live path in this package by construction),
`RS_PAPER_ARMED=YES` interlock, keys from env only. A freshness gate
compares the benchmark's last bar to today's date, so a holiday run
cannot re-signal stale bars. Ledger lives in docs/reports (paper
account data only, never keys).

Scope honesty: this validates the SETUP SIGNAL with fake money on
equities. Options P&L still is not modeled (historical chains are paid
data), and live execution remains co-pilot — the operator's word, per
trade, in Robinhood. The point is a dated, machine-kept track record
that the operator only has to read.

## 2026-08-16 — Universe expansion PASSES; H5 earnings blackout rejected

**Universe expansion validated (22 tickers).** Re-run on the expanded
universe after backfilling TSLA/MU/PLTR/SBUX:
- Backtest: RS-02 177 trades, 58% wr, **+0.341R** (18-ticker run was 140
  trades / +0.389R — 37 more trades at a slightly lower average, edge
  intact). RS-01 stays negative (−0.108R): correctly killed.
- Walk-forward: **3/3 test windows held** — 2024 +0.577R (n=48),
  2025 +0.307R (n=49), 2026 +0.227R (n=24), max DD −3.0 to −4.3R.
The four added tickers earned their place on strategy-level evidence,
which was the pre-registered gate.

**H5 earnings blackout — REJECTED despite an ADOPT-CANDIDATE label.**

| Variant | Train | Test |
|---|---|---|
| BASELINE_DOCTRINE | +0.348R (n=61) | +0.280R (n=47) |
| H5a blackout 3d | +0.359R (n=58) | +0.288R (n=44) |
| H5b blackout 21d | +0.451R (n=48) | +0.250R (n=34) |

The verdict logic flagged H5a because both windows nudged up. The
arithmetic says otherwise:
- The gain is +0.011R train / +0.008R test — an order of magnitude
  smaller than H4b's +0.085R test margin, and it comes from excluding
  just **3 trades per window**.
- Those excluded trades were **profitable** (+0.135R and +0.163R
  average). Total return FELL in both windows (+21.23R → +20.82R
  train, +13.16R → +12.67R test). The per-trade average rose only
  because slightly-below-average WINNERS were removed.
- No dose-response: the wider 21-day blackout was much better on train
  and worse on test. H4b earned adoption partly on a monotone
  threshold response; H5 shows the opposite — the signature of noise.

**Methodology note added to the standard:** expectancy-per-trade alone
can be gamed by a filter that removes profitable-but-below-average
trades. Future variants must be checked for total-R direction and for
how many trades actually differ before an ADOPT-CANDIDATE is believed.
A verdict label is an input to the decision, not the decision.

Doctrine unchanged: RS-02 + wide exit (3R/15-bar) + H2b regime + H4b
quality + no volatility ETPs. The §72 hypothesis queue is now empty.

## 2026-08-16 — position_manager recovered, completed, adopted

A local session authored `mve/position_manager.py` + tests; the commit
was dropped during a rebase and the files existed nowhere on GitHub.
Recovered from the operator's reflog (branch `recovered-pm`), reviewed,
and completed.

What it is: a PURE decision function for open long-call positions —
HOLD or EXIT with accumulated reasons. No sizing, no contract choice,
no order placement (§67 execution stays human-confirmed). It moves the
playbook's exit rules from prose (skippable under pressure, which is
when they matter) into deterministic, testable code.

As recovered it encoded 2 of the playbook's 5 exit rules (DTE floor,
invalidation). Completed here with the two the exit study actually
validated:
- **TARGET** at +TARGET_R on the underlying, and
- **TIME_EXIT** at MAX_HOLD_BARS trading days,
both imported from `backtest` rather than re-typed, so a doctrine
number still lives in exactly one place.

Also added: `not_evaluated` on the verdict. A rule whose inputs are
missing (older records lack entry_date / entry_underlying) is reported
as NOT CHECKED rather than silently passing — the same principle as the
"no silent caps" rule in the backtester.

Provenance correction: the module's docstring cites Robinhood figures
(116 trades, −$918 of expirations) that are NOT reproducible from this
repo. Marked as the motivating anecdote, not verified evidence — while
noting that the independent Schwab/thinkorswim analysis reached the
same diagnosis on a different account (1,429 round trips, avg win
$19.64 vs avg loss $33.15). Two accounts, two analyses, one failure
mode: unbounded losers, clipped winners.

Not yet wired into a caller — it is the exit authority the co-pilot
flow should consult, and wiring it is the next operational step, not a
research one. 193 tests passing.

## 2026-08-16 — Daily run now reviews held options (co-pilot side)

`position_manager` is wired into the autonomous daily run. The equity
side was already self-enforcing (Alpaca brackets + time exit); the
option side — where the operator's real money and real failure mode
live — had no daily check. Now it does.

`paper/open_options.json` holds the contracts the operator is carrying
in Robinhood; the daily run applies all four exit rules to each and
prints a POSITION REVIEW in the report. The file is committed, so it
can be edited directly on github.com without touching the Mac.

Two design points worth keeping:
- **Held options are reviewed even on non-trading days.** The freshness
  gate blocks scanning and orders, but days-to-expiry keeps running
  over a weekend — a position can cross the DTE floor while the market
  is shut. The holiday report says plainly that prices are the last
  available, not today's.
- **A malformed row raises rather than being skipped.** A position the
  review silently drops is a position nobody is watching, which is the
  precise failure the module exists to prevent. Same rule for tickers
  outside the universe: reported as NOT PRICED, never omitted.

201 tests passing.

## 2026-08-16 — H8 built: VIX term structure as a regime filter

Answering "what else can be learned to read market fluctuations," the
first Tier-1 item: a volatility-regime reading that needs no new data
vendor and no API key.

`mve/vix_regime.py` fetches VIX and VIX3M daily closes (CBOE's public
CSV, Yahoo fallback) and computes the ratio. Below 1.0 the curve is in
CONTANGO — the normal state, more risk priced further out. At or above
1.0 it is BACKWARDATION: near-term fear exceeds three-month, i.e. the
market pricing stress now.

Mechanism stated before the test (as always): breakouts bet on
continuation, and backwardation is precisely when continuation breaks —
correlations converge and trends whipsaw, the momentum-crash regime in
MARKET_THEORY §1.4. Two pre-registered thresholds, round 4 of the
hypothesis lab: ratio < 1.00 (skip backwardation) and < 0.95 (require
real contango). Fails closed — a date with no reading blocks rather
than assuming calm.

The regime also prints in the daily paper report as CONTEXT ONLY. It
gates nothing until H8 is judged and adopted; the report says so on the
line itself, so a reader cannot mistake context for doctrine.

**The H5 lesson is now automatic.** `hypotheses.summary` prints total-R
alongside expectancy for every variant, and an ADOPT-CANDIDATE that
raised the per-trade average while lowering total return now prints a
CAUTION line saying so — as does one where fewer than 8 trades differ
from baseline. A regression test replays the exact round-3 H5 numbers
and asserts both cautions fire. The reasoning that caught H5 by hand is
now part of the instrument.

210 tests passing. Awaiting the operator's `mve.vix_regime` +
`mve.hypotheses` run for the H8 verdict.

## 2026-08-16 — Discovery power: deep history + cross-sectional breadth

Built in answer to the operator's question — "what if new inputs reveal
the real pattern?" The honest risk is not only overfitting; it is being
UNDERPOWERED, where a real but moderate effect looks like noise and gets
rejected. Both changes raise what the lab can detect WITHOUT lowering
the bar.

**1. Deep backfill.** `python -m mve.backfill --years 20`. Fixed a
latent bug found while adding it: `backfill()` accepted a `years`
argument but never forwarded it to `fetch_bars`, so the Yahoo fallback
silently capped every deep pull at 5 years — a deep backfill would have
looked like it worked while quietly returning the old window. The CLI
now takes `--years`, and each ticker reports its actual first->last
date, because a name that IPO'd in 2020 cannot have 20 years and
pretending otherwise misreads every study downstream.

Why it matters: ~5 years and 177 trades can only resolve fairly large
effects. Twenty years spans 2008 and 2020 — it both quadruples the
evidence and lets us ask whether the edge is regime-dependent rather
than assuming.

**2. Cross-sectional breadth.** `BacktestResult.per_ticker()` plus a
breadth line under every verdict: how many individual tickers a variant
improved, among names with >= 5 trades in both arms. An ADOPT-CANDIDATE
that helps a MINORITY of names now prints a CAUTION — aggregate
expectancy can be carried by two or three lucky tickers, and that is a
different (weaker) claim than "this works."

**Known limitation, stated plainly:** the 2025-2026 test window has now
been used to judge eight hypothesis rounds. Every pass makes it less
genuinely out-of-sample. It remains the best historical evidence
available, but the only truly uncontaminated test bed from here is the
forward paper track — data that arrives after the rules were fixed.
Deep history helps precisely because it adds evidence that was never
part of that selection loop.

216 tests passing.

## 2026-08-16 — Pre-open briefing added

Operator asked for a morning scan. `python -m paper.daily --preopen`
(cron 12:45 UTC weekdays) reports what the previous close implies:
candidates with stop/target/1R and the option guidance, which names are
already held, what is queued to fill at the open, open positions, and
the held-option review.

**Read-only by construction.** It places no orders and never writes the
ledger — so it cannot double-trade against the evening run, which
remains the single trading authority. A manual workflow run defaults to
`preopen` too, so an accidental click cannot place orders.

Point-in-time note: pre-open, the newest bar IS yesterday's close, and
that is exactly the information the signal is allowed to use. The
freshness gate is therefore an AGE check (<= 4 calendar days, covering
long weekends) rather than the evening run's same-day requirement.

221 tests passing.

## 2026-08-16 — Autonomous PAPER options: the measurement gap opens

The paper track now trades OPTIONS by itself, not just equities. This
is the first time the project measures the instrument it actually
trades. Every rule adopted so far — wide exit, H2b, H4b — was validated
on the UNDERLYING, because historical chains are paid data. Forward
paper fills are free, so the record starts accumulating now.

`paper/options_broker.py`: contract discovery, selection, and orders on
Alpaca's paper endpoint (inherits the hard-coded URL and the
RS_PAPER_ARMED interlock). Selection reuses chain_select's constants —
DTE 21-60, delta 0.40-0.80 targeting 0.60, spread <= 10% — rather than
re-typing them.

**Greeks honesty:** when the data plan carries delta, selection uses it.
When it does not, it falls back to a moneyness proxy (strike near
0.97 x spot) and the report SAYS which basis was used. A silent swap
between "chosen by delta" and "chosen by a rule of thumb" would make
the resulting P&L uninterpretable.

Mechanics worth recording:
- **Exits are the loop, not the broker.** Alpaca has no bracket orders
  for options, so unlike the equity side nothing is self-enforcing.
  `run_option_cycle` evaluates every held contract through
  `position_manager` each run and sells on a verdict. Exits run BEFORE
  entries so a freed slot can be reused the same day.
- **Sizing is by max loss.** A long call can go to zero, so the premium
  is the risk: contracts = floor(1% equity / (mid x 100)), capped at 5.
  Deliberately more conservative than a delta-based estimate.
- **Limit at the mid to open**, never market — on an instrument whose
  spread is the dominant cost, a market order donates the spread.
- **An options outage degrades to a note.** The equity track is the
  validated one; a chain-endpoint failure must not take it down.

237 tests passing. What this buys: in ~20-30 closed option trades there
will finally be an answer to the question the backtests could never
reach — does a correct call on the stock actually make money as a
contract, after spread and decay?

## 2026-08-16 — Round 5 built: H9 news, H10 fundamentals, H11 volume

Three new inputs, each with its mechanism stated before any data was
looked at, each tested as the FULL adopted doctrine plus one filter so
a verdict is about that filter alone.

**H9 — news attention** (`mve/news.py`, Alpaca news API, free with the
APCA keys already set). Measures ATTENTION: articles in the last 5 days
versus the ticker's own 60-day baseline rate. Mechanism: Barber & Odean
(2008) plus the metaorder story both say a breakout arriving in a burst
of coverage is more crowded and more likely to fade than one accumulated
quietly, so the filter SKIPS high attention. If the data says the
opposite that is a finding, not licence to flip the story afterwards.

Deliberately NOT sentiment. Scoring headlines with a keyword list
produces a number that looks rigorous, is mostly noise, and cannot be
reproduced across a rewrite. Sentiment can be its own honestly-labelled
hypothesis later.

**H10 — profitability** (`mve/fundamentals.py`, SEC EDGAR XBRL, free,
no key). Trailing four quarters of net income. The whole difficulty is
point-in-time: a quarter ending 03-31 is not public on 03-31, and using
the period date would leak the future into every backtest. EDGAR carries
a `filed` date on every fact, so the lookup returns only what a reader
could have known by that close. Annual figures are excluded so quarters
cannot be double-counted, and a re-reported period keeps its EARLIEST
filing. Mechanism: Novy-Marx (2013) profitability factor — a breakout in
an unprofitable name is more story than earnings.

**H11 — overhead supply** (`mve/volume_profile.py`, no new data source).
Volume-by-price over the trailing 60 sessions, spreading each bar's
volume across its own high-low range, then measuring the share that
traded ABOVE today's close. Every such share is a break-even seller the
rally must absorb.

Why this is worth testing when H1 (52-week high) and H3 (anchored VWAP)
both failed: those are PRICE levels, and RS-02's 20-day breakout already
encodes price structure — they were largely restating the entry rule.
This is a VOLUME measurement, which is genuinely new information. The
support/resistance family is 0-for-2 so far; H11 is the honest third
try, not a fourth angle on the same idea.

All three fail closed. Overhead supply and the point of control also
print in the daily paper report as CONTEXT ONLY, labelled as gating
nothing until judged.

252 tests passing. Awaiting the operator's `mve.news`,
`mve.fundamentals` and `mve.hypotheses` run.

## 2026-08-17 — Round 6 built: H12–H17, plus a multiple-comparisons guard

Operator asked for all six devised hypotheses to be run. Built. Each is
in a dimension nothing else in the system touches, and each states its
mechanism before any data was looked at.

- **H12 partial exits** (`exit_study`): book half at +1.5R (or +1.0R),
  move the runner's stop to breakeven, let it ride to +3R. This is where
  the operator's OWN broker history said the disease was — avg win
  $19.64 vs avg loss $33.15 — and yet five rounds went to entry filters
  and only one to exits. Correcting that imbalance.
  Conservative ordering preserved: the partial fills only AFTER the
  gap-stop and stop checks on the same bar, so it can never flatter a
  losing bar. A trade that never reaches the level behaves identically
  to `wide` — the scheme cannot help losers, only shape winners.
- **H13 volatility contraction**: ATR percentile within its own trailing
  year. Nothing in the system measured stock-level volatility at all.
  Mechanism: a breakout from a quiet base gives a tight stop and a fresh
  move — more reward per unit risk.
- **H14 close strength**: where in the day's range the close landed.
  Demand persisting into the bell versus sellers meeting it.
- **H15 gap cost**: an EXECUTION test, not a prediction. Implemented in
  the backtester as `max_gap_pct`, cancelling the fill when the next
  open gaps too far above the signal close — what a real desk does.
  Counted as `gapped_signals`, never silently dropped.
- **H16 signal clustering**: the first SET-level question asked here.
  Counts are taken from the BASELINE run so the filter is judged against
  the same signal set it sees. Both stories (broad strength vs crowded
  top) are plausible, which is exactly when it is tempting to decide
  after seeing the answer — so the direction is pre-registered as
  crowding-is-risk.
- **H17 sizing by conviction**: not a filter. `BacktestResult.per_score`
  reports expectancy by opportunity-score bucket. If conviction carries
  no information, sizing by it cannot help — this measures the
  precondition rather than assuming it.

**The multiple-comparisons guard.** This round takes the count to ~13
variants. At a 1-in-20 luck rate that is ~0.65 ADOPT-CANDIDATEs expected
from chance alone, and the summary now prints exactly that. When the
number of candidates is within what chance would produce, the report
says so and calls them things to RE-TEST rather than findings.

This is the honest counterweight to running many tests at once: the
answer to "more information is usually helpful" is yes — provided the
bar rises with the number of questions asked. It now does, automatically.

262 tests passing.

## 2026-08-17 — H8 verdict: volatility regime REJECTED (both variants)

| Variant | Train | Test |
|---|---|---|
| BASELINE_DOCTRINE | +0.348R (n=61, totR +21.23) | +0.280R (n=47, totR +13.16) |
| H8a no backwardation | +0.338R (n=60, +20.28) | +0.225R (n=45, +10.12) |
| H8b contango < 0.95 | +0.326R (n=59, +19.23) | +0.253R (n=44, +11.13) |

Clean rejection: worse than baseline on BOTH windows, at BOTH thresholds,
in expectancy AND total return. No dose-response — tightening the
threshold did not help, which is what a real effect would have shown.

The interesting detail is what the filter removed. H8a skipped 1 train
trade worth +0.95R and 2 test trades worth +3.04R — **+1.52R each**.
The backwardation days it screened out produced ABOVE-average trades in
this sample, the opposite of the pre-registered mechanism (breakouts bet
on continuation; backwardation is when continuation breaks).

Honest reading: n is 1-3 trades, far too few to claim the reverse effect
is real. The defensible statement is that there is NO evidence for the
mechanism here, and no basis for flipping it either. Filed as rejected;
the reverse would be a new hypothesis needing its own pre-registration.

Tally: 11 hypotheses judged, 3 adopted (H2b regime, H4b quality, wide
exit). H1, H2a, H3, H5, H6, H7, H8 rejected. Rounds 5 and 6 (H9-H17)
are built and awaiting a run.

## 2026-08-17 — Partial-fetch guard (a near-miss worth recording)

The operator's round-5 fetch dropped mid-universe on a DNS failure and
saved news for **7 of 22 tickers**, then the SEC fetch failed outright.
Had `mve.hypotheses` run on that state it would have produced a
confident-looking H9 verdict — because the filter fails closed, the 15
uncovered names would simply have been skipped, and the study would have
measured "these 7 tickers" while appearing to measure news attention.

That is the exact failure mode this project keeps guarding against, and
it nearly arrived through the back door of a network hiccup rather than
through a reasoning error.

Two fixes:

1. **Retries with backoff** in `news.py` and `fundamentals.py`. A single
   transient DNS failure should not silently shrink the sample.
2. **Coverage validation** in `hypotheses.py`. Before anything is
   scored, per-ticker datasets are checked against the universe; a
   variant whose data covers under 95% of required tickers is marked
   **INVALID** with the missing names listed, and is never given a
   verdict. A regression test replays the incident with a fabricated
   +0.9R result and asserts it is invalidated rather than adopted.

The general principle, now enforced rather than remembered: a filter
that fails closed converts missing data into a hidden sample
restriction. Fail-closed is right for TRADING (skip what you cannot
verify) and dangerous for RESEARCH (you silently changed the question).
Both behaviours are now explicit.

264 tests passing.

## 2026-08-17 — Two fetch bugs found by running it

**SEC 403 Forbidden.** My error: the SEC's fair-access policy requires a
User-Agent carrying a real contact address, and mine had none. Fixed by
reading `SEC_CONTACT_EMAIL` from the environment — deliberately NOT
hard-coded, because an email address is the operator's to give and does
not belong in a public repository. Missing or malformed, the tool exits
with the exact line to add to ~/.zshrc rather than failing at the API.

**News fetch still dropping tickers** (19/22 after retries, a different
subset than the previous 7/22 — so it is the operator's DNS resolver
buckling under sustained connections, not the endpoint). Two changes:
- backoff raised from ~0.35s to 3s doubling. A resolver needs seconds to
  recover; the first attempt retried far too fast to help.
- **the fetch now SKIPS tickers already on disk**, so repeated runs
  CONVERGE on complete coverage instead of re-rolling the same dice on
  all 22 every time. `--refresh` forces a full re-fetch. The summary
  names what is still missing and says to run it again.

Worth recording as a pattern: both failures were invisible to the test
suite because both live at the network boundary, and both were found by
the operator simply running the thing. The coverage guard added earlier
today is what makes these merely annoying rather than dangerous — an
incomplete fetch now blocks a verdict instead of quietly biasing one.

266 tests passing.

---

## 2026-08-21 — Round 5 verdicts: H9, H10, H11, H13, H14, H15, H16

Thirteen variants across seven hypothesis families, judged against
BASELINE_DOCTRINE (train n=61 exp=+0.348R totR=+21.23; test n=47
exp=+0.280R totR=+13.16). **Nothing is adopted.**

**Rejected outright — the mechanism did not survive contact with data:**

- **H9 news attention** (both thresholds). REJECT: train fell in both
  variants, and total return collapsed (+21.23R → +11.49R on train).
  Screening out breakouts arriving in a burst of coverage deletes a lot
  of good trades. The pre-registered story — Barber & Odean attention,
  crowded entries fade — was stated before the test and is now simply
  wrong for this setup. Recorded as a finding, not re-narrated.
- **H14 close strength** (both thresholds). REJECT. Closing at the top
  of the day's range does not predict follow-through; both variants cut
  total return. A widely repeated piece of chart folklore that does not
  hold here.
- **H10 trailing profitability.** NOISE — train improved sharply
  (+0.546R) and test did not confirm (+0.257R vs baseline +0.280R).
  Test total return FELL by 2.37R, so the filter deleted profitable
  trades out of sample. Coverage passed, so this is a real verdict on
  the filter and not an artifact of missing SEC data. Textbook
  train-only improvement.

**Untested, not refuted — the sample could not exercise them:**

- **H16 signal clustering.** Both variants returned numbers bit-identical
  to baseline: no day in five years ever produced more than two signals,
  so the cap never bound. The report called this REJECT, which reads as
  tested-and-failed. Fixed — the summary now prints NO EFFECT / UNTESTED
  when a variant's trade count and total R match baseline exactly.
  Incidentally this answers the worry that motivated H16: clustering is
  not a problem in this universe.
- **H13 volatility contraction.** n=13 and n=20 on train. Train
  expectancy looked strong (+0.73R, +0.67R) and that is exactly why it
  must not be read — twenty trades cannot distinguish a real effect from
  a run of luck. Needs the deep backfill before it can be judged.

**The one candidate worth a second look, and why it is still not adopted:**

- **H15 gap-at-open cancellation.** H15a (2%) improved train AND test,
  and unlike the H5 failure mode the TOTAL return rose in both windows
  (+21.23→+24.19, +13.16→+17.03). Six cancelled fills were worth
  −6.83R combined, roughly −1.14R each: near-maximum losers. The
  mechanism is also the right kind — an execution cost, not a market
  prediction. You signal on the close and fill at the next open; if the
  open has run 2% away from you, the stop distance is already blown out
  before the trade starts.

  Against it: **six trades**, and **no dose-response**. The tighter 1%
  variant removes more trades and gains less, meaning the extra two it
  cuts were worth about +1.43R each. A real cost should get worse
  monotonically as the gap widens. That it does not is the strongest
  argument that these six fills are outliers.

  Rather than re-run the same underpowered test, the study now measures
  the claim at full power: every trade carries its entry gap, and the
  report buckets expectancy by gap size across ALL trades in both
  windows. If paying up at the open genuinely costs money, expectancy
  declines steadily across the buckets in train and test alike. If it
  is six unlucky fills, the pattern will be jagged. That is a real test;
  the filter version was not.

**Multiple comparisons.** 13 variants, ~0.7 ADOPT-CANDIDATEs expected
from chance. Four appeared — but H11a/H11b and H15a/H15b are two
hypotheses at two thresholds, not four independent tests, and H11's
candidates rest on 4 and 2 differing trades respectively (H11b improved
0 of 10 tickers). Treating those as findings would be indefensible.

**Net result of round 5: no change to live doctrine.** RS-02 with the
200-day regime filter and the H4b quality-momentum threshold stands
exactly as it did. Seven ideas tested, five eliminated cheaply, two
sent back for a properly powered test.

271 tests passing.
