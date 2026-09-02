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

---

## 2026-08-21 — H18 built: the combination study

Operator asked whether the tested strategies work better combined. The
mechanics constrain the answer before any data is touched: entry
filters compose by AND, so a combination can only REMOVE trades from
the doctrine baseline — it cannot add a trade or improve one it keeps.
Combining two filters that each deleted money deletes more. And the
combination space is a luck factory: 13 round-5 variants form 2^13 =
8192 subsets, ~400 of which would beat baseline by chance; the best
cell of an exhaustive search is essentially guaranteed to be luck.

`mve.combinations` therefore answers three narrow questions instead of
shopping the space:

1. **WHICH trades does each filter remove, and what were they worth?**
   Two filters can post identical aggregates while deleting completely
   different trades.
2. **Do filters remove the SAME trades?** Pairwise overlap of removed
   sets. High overlap = a combination is redundant; low overlap = a
   genuinely new, stricter rule with a smaller sample.
3. **Does the one pre-registered combo survive?** H11a overhead +
   H15a gap — the only round-5 members not REJECTED solo. Registered
   before the run so the list cannot grow after the numbers are seen.
   The report also prints an interaction line: trades removed by the
   combo vs. the union of its members' removals — near zero means no
   interaction, just both rules at once.

A cross-family pair sweep (one pre-registered primary per family, 21
pairs) is included as a DIAGNOSTIC with the luck arithmetic printed
above it — it exists to show where luck concentrates, not to shop
from. Substitution is counted honestly: removing a signal can free the
one-position-per-ticker slot for a later signal the baseline never
took, so filtering is not pure subtraction.

Not yet run — needs the operator's bars, news, and fundamentals.

277 tests passing.

---

## 2026-08-21 — H15 powered test and H18 combination verdicts

**H15 gap dose-response: the execution-cost story FAILS its powered
test.** The pre-registered criterion, written before the run: a real
cost declines steadily across the gap buckets in BOTH windows; jagged
means the filter's gain was outliers. The pattern is jagged. On train,
expectancy RISES from flat opens (+0.20R) through 0-1% gaps (+0.62R)
to 1-2% (+0.65R) before going negative at 2%+; on test it falls, then
rises, then sits at breakeven for 2%+ (-0.02R over 7 trades). Moderate
gap-ups are fine — on train they were the BEST entries. Only the 2%+
tail is negative in both windows, and that is 12 trades worth -1.53R
combined, with the test half at essentially zero.

The overlap study also exposed where the filter's headline gain came
from: H15a removed 13 trades worth only -2.53R, yet gained +3.87R on
test — the rest is SUBSTITUTION, freed one-position-per-ticker slots
taken by later signals that happened to win. That is luck of the queue,
not a property of gaps. **Not adopted.** The 2%+ tail stays on the
watch list for the 20-year backfill, which multiplies its sample.

**H18 pre-registered combo (H11a+H15a): ADOPT-CANDIDATE on paper,
not adopted.** Train +24.40R vs 21.23, test +18.31R vs 13.16, and the
interaction line reads +0: the members' removals are disjoint (1 shared
trade of 19), so the combo is just both small rules side by side — it
inherits their evidential weakness rather than curing it. Subtracting
H15a's solo numbers, H11a's increment is +0.21R train / +1.28R test.
A candidate whose main ingredient just failed its powered test is not
a candidate.

**The pair sweep found no new information — demonstrably.** 4 of 15
judged pairs beat baseline in both windows against ~1.1 expected by
chance, which looks exciting until the pairs are unmasked: H16a removes
zero trades (it never binds), so "H16a+H15a" IS H15a solo (numbers
match exactly: +24.19/+17.03) and "H11a+H16a" IS H11a solo. The other
two winners both contain H15a. Every "winning combination" is the same
two small effects wearing different hats. This is the cleanest
demonstration yet of why the sweep is a diagnostic and not a menu.

**The autopsy column is the round's real finding.** What each rejected
filter REMOVED, valued per trade: H9a news attention removed 26 trades
worth +0.57R EACH — the news filter was deleting the system's best
trades. High-attention breakouts outperformed here, the opposite of the
pre-registered Barber-Odean story. (Flipping the filter to REQUIRE
attention would be post-hoc story-flipping; if attention-as-positive is
ever tested it goes in as a new pre-registered hypothesis on fresh
data.) H14a close strength removed +0.44R/trade — same lesson. H13a
quiet-base would have removed 89 trades worth +23.85R, most of the
system's profit. The rejected filters were not merely useless; they
were aimed at the best trades.

**Net: doctrine unchanged for the third consecutive round.** RS-02 +
200-day regime + quality momentum survives every challenger. Rounds
5-6 + H18 tested 16 distinct ideas and adopted none — and the
overlap/autopsy tables mean each rejection now carries WHY.

---

## 2026-08-21 — H19 built: confluence as SCORING, not gating

Operator asked about confluence — combining strategies the way traders
stack indicators. The distinction that matters: H18 tested the STRICT
form (require agreement or skip the trade), which failed because the
filters mostly delete good trades. The trader's meaning is the SOFT
form: count what lines up and act with more conviction when more does.
That design cannot repeat the H5 failure — a score never removes a
trade, so total return is untouched; the worst a useless score can do
is nothing.

The overfitting risk moves instead into the WEIGHTS. A fitted
confluence score (2 points for this, half a point for that) has as
many free parameters as weights and will happily memorise the past. So
`mve.confluence` fits nothing:

- **Part A** finally reports the §32 opportunity score — the 0-10
  conviction rubric written into the spec before any backtest existed,
  computed on every signal since the MVE was built, and never once
  examined against outcomes. This is H17's machinery getting its
  first real run.
- **Part B** counts equal-weight votes from the round-5 factor
  primaries, each voting its pre-registered direction — no weights, no
  post-hoc flips (the news factor still votes "quiet is good" even
  though the autopsy suggests the opposite; flipping it after seeing
  the data would be story-flipping).

Verdict instrument: dose-response, same as the H15 gap study.
Expectancy must RISE with the score in BOTH windows. Flat = votes are
noise. Falling = the factors collectively anti-predict — which the
H18 autopsy predicts, and confirming THAT from a second angle would
itself be useful: it would close the book on this factor family and
say future rounds need genuinely different information (deeper
history, intraday structure, breadth/market-internals), not more
recombination of the same seven ideas.

If either slope survives test, the payoff is sizing by score — more
risk on high-conviction signals, every trade still taken — which is
also the only honest use of confluence: it changes how much, never
whether.

`Trade` now carries `signal_date` so signal-time votes join cleanly to
outcomes. 281 tests passing.

---

## 2026-08-21 — Deep backfill first contact: corrupt bars, and a
## walk-forward that ignored the new history

The operator's 20-year run printed an RS-01 "average loss" of
-6,911R and a max drawdown of -3.6 MILLION R. Those are not market
results — free deep history (Stooq/Yahoo) carries corrupt bars
(unadjusted splits, near-zero prices), and one such bar puts the stop
a fraction of a cent from entry, exploding the R-math. RS-02's
numbers looked plausible, but the same bars could sit inside them
undetected. Nothing from that run is judged.

Two defenses added to the backtester, both loud:

- **Thin-stop floor** (`MIN_R_DENOM_FRAC = 0.5%`): a stop within 0.5%
  of entry is not a real swing low; the signal is skipped and counted
  in a `thin_stop_signals` line in the report.
- **Quarantine** (`SUSPECT_R = 50`): a closed trade beyond |50R| is a
  corrupt print, excluded from every aggregate, and listed BY NAME in
  the report (ticker + date) so the offending history can be
  inspected. Ten times the 3R target is unreachable by any real trade
  in this system; only bad data crosses it.

Both run inside `run_backtest`, so every study (hypotheses,
combinations, confluence, walkforward) inherits the protection.

Separately: the walk-forward's windows were HARDCODED to 2021+ — the
operator downloaded 20 years and the study silently walked five. The
splits now derive from the benchmark's actual span: every year from
(first + 3) through the last is tested against all years before it.
Twenty years of data now means ~18 test windows instead of 3.

Also recorded from the operator's paste, pending the re-run for
confirmation: RS-02 full-sample expectancy over ~20 years printed
+0.133R (802 trades) versus +0.341R on the 5-year window — the edge
is thinner across regimes than recent history suggested. If that
holds after the corrupt bars are quarantined, it is the most
important number the deep backfill has produced: the recent window
flattered the edge.

286 tests passing.

---

## 2026-08-23 — The guarded 20-year run: what two decades actually say

The data guards worked. RS-01's -6,911R "average loss" is gone: 20
signals were skipped for stops sitting within 0.5% of entry, no trade
needed quarantining, and RS-01 prints +0.061R instead of -3,935R. The
corruption was entirely thin-stop bars, caught before entry.

**The headline number: RS-02 across 20 years is +0.136R per trade
(800 trades, 51% win rate), against +0.341R on 2021-2026 (177 trades,
58%).** The recent window was flattering the edge by roughly 2.5x. The
edge is real and it is thinner than we thought — that is exactly what
the deep backfill was run to find out, and it is the single most
valuable number the project has produced.

**Walk-forward, now 18 windows instead of 3: the edge held in 14/18.**
Losing years: 2011 (-0.300R), 2014 (-0.462R), 2018 (-0.112R), 2022
(-0.381R); 2020 was flat (+0.001R). Two structural observations. First,
train expectancy is remarkably stationary — every expanding window from
2006-2010 onward sits between +0.05R and +0.16R, so the estimate is not
drifting. Second, 2022 produced only 17 signals against a ~50 typical
year: the 200-day regime filter did its job and kept the system out of
the bear market rather than losing in it.

**Round 5 re-judged at 8x TRAIN — and the autopsy became unambiguous.**
The combination study's removal column now reads, per filter, the value
of what it deletes:

    H9a  news        removed 406 trades worth +43.56R
    H13a quiet base  removed 403 trades worth +26.44R
    H10  profitable  removed 163 trades worth +20.58R
    H14a close       removed 164 trades worth +19.99R
    H16a clustering  removed  32 trades worth  +5.11R
    H11a overhead    removed  42 trades worth  +2.34R
    H15a gap 2%      removed  34 trades worth  -8.35R

Every filter except H15a deletes PROFITABLE trades. H15a alone deletes
losers, at -0.25R each. Six ideas were not merely useless; they were
aimed at the system's best trades. One is aimed at its worst.

H9a is the clearest illustration of why an ADOPT-CANDIDATE label means
nothing on its own: it earned the label while deleting 398 of 478
trades worth +42.72R of total return. The automatic CAUTION caught it.

**A methodological problem the backfill created, and the response.**
TRAIN went 61 -> 478 trades. TEST went 47 -> 48, because TEST_START is
a calendar date and only ~20 months live after it. So every "test
confirms" verdict in the round-5 report still rests on ~48 trades — and
that same 48-trade window has now been consulted across rounds 3, 4, 5,
6, H18 and H19. Repeatedly consulting one small window is how a test
set stops being one.

Meanwhile 2006-2020 arrived with the backfill, went straight into
TRAIN, and has never judged anything. That is the project's only virgin
sample, roughly 600 trades. `mve.holdout` (H20) spends it on exactly
two pre-specified candidates and nothing else — a sweep there would
burn the clean sample on the same multiple-comparisons problem it
exists to escape:

1. **The §32 opportunity score.** In the guarded run it rose
   monotonically in BOTH windows across every bucket with >=10 trades:
   train score 9 +0.143R -> score 10 +0.226R; test score 9 -0.200R ->
   score 10 +0.723R. The rubric was written into the spec before any
   market data existed, so it is not fitted. This is the strongest
   result the program has produced, and it is a SIZING candidate — it
   changes how much, never whether.
2. **H15a, the 2% gap cancellation.** At full power the dose-response
   is negative in the top bucket in both windows (train n=25 -0.248R;
   test n=7 -0.023R) and the filter improves expectancy AND total in
   both. But the registered shape was a STEADY decline and what appears
   is a CLIFF at 2% with moderate gaps fine or better. A threshold
   effect is a different claim from the one registered; the holdout
   report says so explicitly rather than quietly accepting it.

**H19 Part B failed and the contrast is informative.** Equal-weight
factor votes rose on train and did not confirm on test (test peaks at 4
votes then falls). The system's own pre-registered conviction rubric
carries information; the six bolted-on factors, counted together, do
not. Consistent with the autopsy.

**Doctrine still unchanged.** Nothing is adopted. Two candidates now
face the only untouched data the project has.

291 tests passing.

---

## 2026-08-23 — H20 holdout: one candidate fails, one confirms

The virgin 2006-2020 sample is spent. Baseline doctrine over those 15
years: **n=376, +0.096R per trade, 50% win rate, +36.10R total.** That
is the hardest stretch the system has faced (2008, 2011, 2014, 2018,
2020) and it is positive. It is also thinner than the +0.136R
full-sample figure, which is itself thinner than the +0.341R that the
2021-2026 window advertised. Each widening of the sample has lowered
the estimate. That is the shape of an honest measurement converging,
not of an edge disappearing — but the direction is one way.

### CANDIDATE 1 — §32 opportunity score: FAILED

    score <=7  n= 24  +0.028R
    score 8    n= 47  -0.152R
    score 9    n=156  +0.115R
    score 10   n=149  +0.165R

The pre-registered criterion was a rise across every populated bucket.
It does not rise: `<=7` sits above `8`. **The score is not adopted, and
the failure is not being relitigated.**

Two honest observations that follow, neither of which rescues it:

- The dramatic test-window number that made this look like the
  program's strongest result — score 10 at +0.723R — was a 24-trade
  fluke. On 149 virgin trades score 10 earns +0.165R against a +0.096R
  baseline. Real, and modest. The lesson is about the 48-trade test
  window, not about the score.
- Gating to high scores would be the H5 failure again: keeping only
  score-10 trades takes total return from +36.10R to +24.6R while
  cutting trade count 60%. Any future use is SIZING or nothing.

The one pattern that repeated in all three samples is score 8 being
negative (-0.133R train, -0.335R test, -0.152R virgin). That is an
observation noticed after the fact, on overlapping samples, with no
clean historical data left to test it — so it is **registered forward**
as FWD-1 in `docs/PREREGISTERED.md` with its threshold, direction,
success criterion and minimum sample (n>=40) fixed in advance. Nothing
acts on it until then. `OpenPosition.score` now records the pairing so
forward paper results accumulate; a test asserts no exit rule reads it.

### CANDIDATE 2 — H15a 2% gap cancellation: CONFIRMS

    baseline   n=376  +0.096R  totR +36.10
    filtered   n=367  +0.117R  totR +42.94
    delta      expectancy +0.021R, total +6.84R over 9 cancelled fills

Both expectancy and total improved, so this is not the H5 failure. The
nine cancelled fills were worth roughly -0.76R each. Critically, the
2006-2020 window is **disjoint** from the 2021-2026 window where the 2%
threshold was chosen, so this is genuine out-of-sample confirmation of
the threshold and not a re-reading of the data that produced it. The
2%+ bucket is negative in every window measured (-0.248R, -0.023R,
-0.209R).

The caveat travels with it: the registered shape was a STEADY decline
and what appears is a CLIFF — moderate gaps are fine or better, only
2%+ is negative. A threshold effect is a different claim. H15a is
recommended on direction, disjoint-sample confirmation, and mechanism
(an execution cost, not a market prediction), NOT on shape.

**Recommendation to the operator: adopt H15a.** It is the first thing
in this project I would change. It cancels roughly 2% of orders, the
failure mode is skipping a trade rather than taking a bad one, and it
is the only rule tested that removes losers instead of winners. Per
LAW 12/20 the encoding is the operator's decision, not mine. FWD-2
registers the forward check that it keeps earning its place.

### What the numbers mean in practice

376 trades over 15 years is ~25 signals a year. At +0.096R each, the
underlying signal produces roughly **+2.4R per year**. Risking 1% of
account per trade, that is about +2.4% a year before options are
involved; long calls lever it up and also add spread and theta costs
that this backtest does not model. Against the operator's stated target
of 1.5-2x per dollar, the measured edge is far smaller — and it is
real, which is more than most of what was tested can say.

### Status of the sample

Every clean historical window is now spent: 2021-2026 chose the
thresholds, 2025-2026 was consulted six times, 2006-2020 judged H20.
`docs/PREREGISTERED.md` exists because forward data is the only honest
test remaining, and claims must be frozen before it arrives.

293 tests passing.

---

## 2026-08-23 — H15a ADOPTED into live doctrine (operator decision)

The operator authorized encoding the 2% fill-gap cancellation. It is the
first rule adopted since H4b (2026-08-16), and the twenty-first
hypothesis tested since.

**Where the number lives.** `setups.MAX_ENTRY_GAP = 0.02`, with the
evidence and the shape caveat in the comment beside it.
`hypotheses.GAP_VARIANTS["H15a_gap_2pct"]` and `holdout.GAP_LIMIT` now
IMPORT that constant rather than repeating `0.02`, so an adopted rule
and the studies that judge it cannot drift apart. H15b keeps its own
literal — it is a comparison arm, not doctrine.

**How a backtested cancellation becomes a broker order.** The live path
submitted a MARKET buy queued for the next open, which fills at any gap
— exactly the behaviour the rule exists to stop. It now submits a LIMIT
at `close x 1.02`. That is the same rule expressed to a broker: it fills
at the open when the open is at or below the cap, and does not fill when
the open gapped through. The `entry_cap` and `signal_close` are written
to the ledger so a fill can always be audited against the rule that
allowed it.

**Two bugs the change exposed, both found by writing the tests.**

1. The closure reconciliation swept up ANY ledger symbol absent from
   broker positions. An order that never filled has no position, so it
   would have been popped and recorded as a closed trade with an unknown
   exit — inventing a round trip that never happened and quietly
   polluting the paper record with phantom trades. Closure now requires
   a confirmed fill (`entry_estimated` False).
2. Nothing distinguished "cancelled" from "still working". A new step
   checks order status before acting: terminal-but-unfilled gets
   cancelled at the broker and removed; `new`/`accepted`/`held`/
   `partially_filled` is left alone; an order queued by the same run is
   skipped because it has not seen an open yet.

**Never silent.** Every cancellation prints under `H15a GAP
CANCELLATIONS` with the cap and the signal close, and the pre-open
briefing prints the limit beside each queued order. A cancellation
nobody is told about is a trade nobody knows was skipped.

**Not encoded:** the §32 opportunity score (failed its holdout) and
every other tested filter. `OpenPosition.score` records the score and a
test asserts no exit rule reads it while FWD-1 is OPEN.

Operator-facing doctrine updated in `robinhood_copilot_playbook.md` —
including the manual version of the rule for Robinhood, where there is
no limit order placed automatically: the scan prints the cap, and a
pre-market price above it means skip the name.

297 tests passing.

---

## 2026-08-23 — The $29 question, answered with numbers

Operator asked whether the account can trade at $29, possibly via cheap
options or penny stocks, and framed it as "use the $29 as trading data."
Three findings, then a build.

**1. The engine already refuses, and it is right to.** `position_size`
returns 0 shares at $29 — and at $2,000, and at $3,000. The binding
limit is not the 1% risk rule but the 5% NOTIONAL CAP: one share of a
$198 stock is 100% of a $29 account and 10% of a $2,000 one. Minimum
equity to buy a single share, by price:

    $25 stock -> $500      $200 stock -> $4,000
    $50 stock -> $1,000    $500 stock -> $10,000
    $100 stock -> $2,000   $900 stock -> $18,000

The engine placing zero orders at $29 is the risk rules working, not a
bug. Worth stating plainly because "it never trades" reads like a
failure.

**2. Cheap options are not a smaller version of this strategy.** A
contract affordable at $29 (<= $0.29 premium) is deep out of the money
or near expiry: delta roughly 0.05-0.15 against the doctrine's required
0.40-0.80, and a bid/ask commonly 15-30% wide against the doctrine's
10% cap. Both are chain-selection rules the engine already enforces, so
such a contract is not merely a scaled-down trade — it is a trade the
system is built to reject. Nothing measured in this project applies to
it.

**3. Penny stocks are outside every measurement made here.** The
+0.117R was measured on 22 large-cap liquid names. Microcap spreads of
2-10% would consume an edge of that size several times over before any
of it reached the account, and the corrupt-bar guards added on
2026-08-21 exist precisely because thin, reverse-split-prone histories
break the R-math. Testing them is a different research program, not a
smaller version of this one.

**What $0 CAN buy: `paper/option_costs.py`.** The forecast has a hole —
this project has never measured option P&L, because the backtest models
the underlying and historical chains are paid data. The cost recorder
closes it with no capital and no account permissions: at each signal it
selects the contract doctrine WOULD buy, records the real
bid/ask/mid/delta/DTE from the snapshot feed, and reports the dollar
cost plus the equity required to hold it inside the 5% cap. It runs
even when the options CYCLE cannot (that needs options enabled on the
broker account; this needs only market data), and it fails soft — a
missing quote records nothing rather than a zero, so the affordability
report can never lie downward.

What accumulates is the honest answer to "how much account do I need",
priced from the real market rather than estimated, plus the real spread
drag the backtest never charged. When the account can afford a contract
we will already know whether the overlay is viable.

**The uncomfortable arithmetic, recorded because it should not need
rediscovering.** At the measured +2.9%/year, $29 becomes $29.84 in a
year. The binding constraint on this account is not strategy quality —
it is capital. No filter, threshold, or instrument choice changes that,
and the honest lever is contributions.

303 tests passing.

---

## 2026-08-23 — Outside dossier assessed; two real gaps closed (H21)

Operator supplied a quantitative-backtesting dossier claiming 9,000+
backtests over 30 assets and 15 years. Assessed by separating METHODS
(verifiable by running them here) from FINDINGS (unverifiable without
its data). Methods adopted where they filled a gap; findings not
adopted.

**Its two best points were gaps we genuinely had.**

1. **Transaction costs were never charged.** Every number this project
   ever produced is GROSS — no spread, no slippage, no commission. At
   +0.117R per trade that is not cosmetic: 0.01R of cost is 8.5% of the
   edge. `run_backtest` now takes `cost_bps`, charged where it lands —
   paid up at entry (which correctly WIDENS 1R, since a worse fill means
   more risk to the same stop) and received down at exit. It defaults
   to 0.0 so every recorded verdict stays comparable; the study passes
   real figures and reports the BREAK-EVEN cost, which is the
   strategy's execution budget.
2. **The equity curve is a single path.** A -25.6R max drawdown is what
   happened once, in the order it happened. `bootstrap` resamples the
   realised trades 2,000 times and reports the distribution of total R
   and drawdown. Stated with the number, because a bootstrap read as a
   worst case is worse than none: resampling destroys serial
   correlation, so if losses cluster — and in trend systems they do —
   the true distribution is WORSE. It is a FLOOR on risk, not a cap.

Also added **Sharpe** (annualised from the R series; scale-invariant in
risk-per-trade, so it equals the account-return Sharpe). Ours computes
to ~0.65 on the holdout — above the dossier's 0.5 screen.

**Its findings are not adopted, and one has a serious internal problem.**

The dossier reports 9,000 backtests yielding 524 survivors and applies
NO multiple-comparisons correction. At a 5% per-test false-positive rate
9,000 tests produce ~450 survivors from noise alone. Its 524 is barely
distinguishable from that — the exact error this project's summary
footer was built to print. Its headline claim that mean reversion is
"the dominant edge at 64% of survivors" cannot be separated from the
possibility that more mean-reversion variants were tested.

Its claim that trend/momentum is fragile on autopilot and needs "strict
market regime gating" does not contradict our result — it DESCRIBES it.
RS-02 is regime-gated by the 200-day SMA, and that gate is why 2022
produced 17 signals instead of 50.

**Rejected for now, with reasons:** Hidden Markov regime models (Layer
4) add many fitted parameters to a system whose measured edge is
+0.117R; our 1-parameter regime filter already survived out-of-sample
testing, and an HMM is an overfitting machine at this sample size.
Mean-reversion as a base signal is a different strategy family, not a
refinement of this one — testable later as a pre-registered hypothesis,
not adoptable from a dossier. Cross-sectional momentum (rank the
universe, long strongest) is genuinely interesting and academically
supported; its short leg is prohibited (§87 long premium only) but the
long-only ranking version is a legitimate future hypothesis.

313 tests passing.

---

## 2026-08-23 — H-22 pre-registered (cross-sectional momentum, long only)

Operator approved pre-registering the one idea worth taking from the
outside dossier. Registered in `docs/PREREGISTERED.md` **before any
implementation exists** — the study is deliberately not written yet, so
git history shows the parameters were fixed before the first result.

`PREREGISTERED.md` now holds two kinds of entry: **FWD-*** awaiting data
that does not exist, and **H-*** runnable on history the moment they are
written. The second kind lives there because every historical window has
now been glimpsed; writing the parameters down first is what keeps a
test on glimpsed data honest.

**Why this one and not the dossier's other claims.** Cross-sectional
momentum is the only proposal in it that is (a) a mechanism rather than
a survivorship statistic, (b) replicated out-of-sample across decades
and asset classes by people who published their method, and (c)
genuinely different from RS-02 rather than another filter on it — it is
relative rather than absolute, calendar-driven rather than
event-driven, and continuously invested rather than episodic.

**No parameter is fitted.** Ranking reuses the adopted `mom_12_1`,
eligibility reuses the adopted 200-day SMA, rebalance timing and
top-quintile sizing come from the literature. The study therefore
introduces no new free parameter, which is what makes it testable on
windows whose aggregate RS-02 results are already known.

**Three commitments recorded in advance, each of which makes a
comfortable result harder rather than easier:**

- The benchmark is **SPY buy-and-hold with costs**, not RS-02. A
  long-only, near-always-invested strategy that cannot beat the index
  does not justify its complexity, however good a bull decade looks.
- Costs are charged. Monthly rebalancing turns over far more than
  RS-02's ~25 trades a year, so gross figures would flatter this more
  than anything tested so far.
- A **handicap is recorded up front**: the published effect is
  strongest in the long-short spread and the short leg is prohibited
  (§87). A long-only version keeps market beta and drops half the
  factor, so H-22 may fail even if the factor is real — that outcome
  reads "not capturable long-only in 21 names", not "the factor is
  false". Recording this now prevents a failure being spun later into
  either a rejection of the literature or an excuse.

**And what confirmation would not license:** it is a portfolio strategy
needing 3-5 simultaneous positions rebalanced monthly, incompatible
with the current account and awkward with long-premium options. It
would earn the right to be measured alongside RS-02, not to replace it,
and would still need its own adoption decision.

Status: OPEN, registered, not implemented. Implementation is the next
commit and is deliberately separate.
## 2026-08-23 — H21 results: the edge survives costs, but thinly

First run of the robustness suite. Three numbers the project never had,
and one correction to a figure already quoted.

**COST SENSITIVITY (doctrine + H15a, 2006-2020):**

    gross  +0.117R   totR +42.94
    2bp    +0.106R   totR +39.01
    5bp    +0.095R   totR +34.96
    10bp   +0.080R   totR +29.36
    20bp   +0.047R   totR +17.25
    50bp   -0.067R   totR -24.25
    BREAK-EVEN ~32 bps round-trip

The strategy has an execution budget of about 32 bps. Liquid large caps
filled in the opening auction commission-free should cost a few bps, so
there is room — but a third of the edge is gone by 10 bps, and that is
the concrete reason H15a (a pure execution rule) mattered more than any
predictive filter tested across twenty-one hypotheses.

**CORRECTION to the forecast.** Every figure quoted to the operator
before today was GROSS, including "+2.9%/year". At a realistic 5 bps the
expectancy is **+0.095R**, so ~24.5 trades a year is **+2.33R**, or
about **+2.3%/year at 1% risk**. The report now prints the net headline
beside the gross one, because quoting only gross is how a thin edge
looks comfortable.

**SHARPE: 0.52 gross, ~0.42 net at 5 bps.** Worth stating plainly: the
outside dossier proposed a minimum screen of 0.5 out-of-sample. Gross,
this system passes by a hair. **Net of realistic costs, it does not.**
That is not a reason to abandon it — the strategy was measured on the
hardest 15 years, is positive across four crashes, and 0.42 is a real
number rather than a fitted one — but it is the honest headline and it
should not be softened.

**BOOTSTRAP (2,000 resamples of the same 367 trades):**

    total R      5th +6.42   median +43.00   95th +77.85
    max drawdown 5th -24.39  median -12.84
    paths ending at or below zero: 2.9%

The strongest result in the report: only 2.9% of reorderings lose money.
The positive expectancy is not an artifact of the sequence. The drawdown
half is the sobering part — a median of -12.8R and a 5th percentile of
-24.4R means a 25%-of-account drawdown at 1% risk is an ordinary
outcome, not a disaster scenario. And per the caveat printed with it,
independent resampling destroys serial correlation, so the true
distribution is worse than that.

**Two defects the first run exposed, both fixed.**

1. **Costs were charged BEFORE the H15a gap check.** The gap rule tests
   what the MARKET did — live it is a limit at close x 1.02, and whether
   that limit is breached is a fact about the open, not about your
   slippage. Charging first cancelled fills that would really have
   filled just under the cap. The symptom was visible in the first
   report and I nearly explained it away: trade counts wobbled with cost
   (367 / 368 / 368 / 367 / 367 / 362) when they should be constant
   until the cost is large enough to matter. Now charged after the
   check, with a regression test asserting the count does not move.
2. **The bootstrap printed a distribution with no observed value beside
   it.** A percentile table is unreadable without the number it is meant
   to contextualise — "median -12.8R" only means something next to what
   actually happened. Both are now printed together.

Nothing here is a filter and nothing is adopted; costs and path risk
change what the SAME edge is worth, they do not create or destroy one.

315 tests passing.

---

## 2026-08-23 — Second dossier assessed: one real test, two hard noes

Operator supplied a three-part dossier (Markov regime framework;
trading psychology; premium-selling strategies). Assessed part by part.

### Part 1 — Markov regimes. Testable, and the dossier's own evidence
### does not survive a control it never ran.

The construction is classical and legitimate: label each day Bull /
Sideways / Bear by trailing 20-day return (+/-5%), tally a 3x3
transition matrix, signal on P(Bull) - P(Bear). Its stationary-
distribution point is honest — multi-step forecasts converge and
directional alpha decays, and the dossier says so itself.

**But it reads its diagonal as a finding.** Consecutive states share 19
of their 20 bars, so the label is autocorrelated BEFORE any market
behaviour enters. Checked directly: a pure IID random walk — no
regimes, nothing to detect — scores **86% stickiness** under exactly
this definition. The "high persistence" the dossier celebrates is
mostly the window overlapping itself.

`mve.markov` therefore implements the method WITH the control it needs:
`shuffled_null` shuffles daily returns (destroying all serial structure
while preserving the return distribution), rebuilds the windows, and
re-labels. Only stickiness above that null could carry information. On
synthetic random walks the module correctly reports "indistinguishable"
for 2 of 3 and one false positive — about what a 5% threshold should
produce, which is the diagnostic behaving.

Second correction: **effective sample size.** ~4,000 bars is not 4,000
observations but ~200 non-overlapping windows. Precision quoted on the
raw bar count is ~4.5x too confident.

The module deliberately does NOT trade the signal. Whether it improves
RS-02 is a separate question, and one not worth pre-registering unless
the excess above null is non-trivial — a filter built on a matrix that
measures its own window would be noise with extra steps. The short leg
the dossier prescribes is prohibited regardless (§87).

HMM (its proposed fix for the arbitrary +/-5%) stays rejected for the
reason recorded on 2026-08-23 for the previous dossier: fitted
parameters against a +0.117R edge.

### Part 2 — Psychology. Nothing to implement; it describes what is
### already built, and what the operator's own history cost.

"Activity is not profitability", "wait for the pitch", "capital
preservation as ammo". No code follows from this, but it is not empty:
the operator's broker history is **1,429 round trips, 85% day trades,
$2,386 in fees, -$3,770 net** — that is precisely the failure mode
described. The doctrine already answers it structurally, producing ~25
signals a year rather than ~475, and 17 in 2022 when the regime filter
held it out of a bear market. H21 quantified the same argument: at a
32bp break-even, activity IS the tax.

The dossier's "patience gate" is `ENTRY_FILTERS` plus the H15a fill
cap. Already present; nothing to add.

### Part 3 — Premium selling. Prohibited, and unaffordable by ~100x.

Short puts, jade lizards, short call spreads, short strangles, broken
wing butterflies. This is real, well-documented professional
methodology (tastytrade's mechanics — 45 DTE, 16-20 delta, IVR>=30,
50% profit-taking — are published and sound). It is also excluded here
on three independent grounds, any one of which is sufficient:

1. **Doctrine prohibits it.** §87 KEEP list is long premium, long calls
   only; premium selling is barred until short-structure margin
   adapters are validated in Shadow. That is the operator's own
   standing rule, not a new objection.
2. **Capital.** A single short put at ~20% BPR on a $100 underlying
   needs ~$2,000 of buying power; a strangle needs more. The account
   has $29. This is not a marginal fit.
3. **Risk shape.** These are high-POP, high-severity structures: they
   win often and lose large. "POP > 80%" is true and is not
   expectancy — a strategy winning 80% and losing 5x on the rest is
   break-even before costs. The Jade Lizard's "zero upside risk" is
   accurate as stated and understates the case: the short put leg
   carries substantial DOWNSIDE risk, which the framing omits. An
   account that cannot absorb one assignment has no business holding
   undefined-risk short structures.

Recorded rather than dismissed, because the mechanics are worth
revisiting if the account is ever funded past the margin thresholds
AND the §67 release gate is cleared — in that order.

328 tests passing.

---

## 2026-08-23 — H23 verdict: the Markov regime matrix is measuring itself

First run against real history. The prediction recorded before the run
("mostly no") holds, and the data makes the case sharper than expected.

**Result: 1 of 8 tickers clears its own shuffled null; chance predicts
0.4.** And the one that clears — SPY at 89.8% against a null 95th
percentile of 89.7% — clears by a tenth of a percentage point.

    ticker  stickiness  null mean  null p95   excess
    SPY          89.8%      88.8%     89.7%    +1.1%   ABOVE NULL
    AAL          83.9%      83.1%     84.3%    +0.8%   indistinguishable
    AAPL         85.1%      84.5%     85.5%    +0.5%   indistinguishable
    ABNB         83.2%      82.4%     84.8%    +0.8%   indistinguishable
    AFRM         84.4%      82.2%     85.3%    +2.1%   indistinguishable
    AMD          82.4%      82.5%     83.9%    -0.1%   indistinguishable
    AMZN         84.2%      84.0%     85.1%    +0.2%   indistinguishable
    APTV         84.3%      82.8%     85.7%    +1.4%   indistinguishable

Roughly **99% of the "regime stickiness" the dossier reads as a finding
is the 20-day window overlapping itself.** The market contributes one to
two percentage points, and in seven of eight names that is not separable
from the ticker's own shuffled returns. Note AMD is NEGATIVE: less
sticky than its own shuffle.

**The sharper finding, which the report now states itself.** Look at
SPY's off-diagonal extremes: Bull->Bear 0.2%, Bear->Bull 0.0%. Those are
not market facts. To flip a 20-day state to its opposite in ONE day, the
single new bar must move the trailing window by 10 percentage points —
essentially never. So those cells are near zero by ARITHMETIC, which
makes the dossier's signal P(Bull) - P(Bear) determined by the label
already held:

    in Bull      +0.724 - 0.002 = +0.72
    in Sideways  +0.040 - 0.024 = +0.02
    in Bear       0.000 - 0.788 = -0.79

**The signal reports which state you are already in. That is not a
forecast.** Trading it reduces exactly to "go long when the 20-day
return is >= +5%" — a plain momentum filter, reachable with one line and
no Markov machinery, and testable directly. `signal_is_echo` now detects
this condition and the report says so, so no future reader has to
re-derive it.

Also worth recording: the stationary mix is Bull 11.4% / Sideways 79.5%
/ Bear 9.1%. Under the dossier's own +/-5% thresholds SPY is "Sideways"
four days in five, so the classification spends most of its time saying
nothing.

**Verdict: REJECTED as specified.** Not adopted, not pre-registered for
a trading test, and no further work planned. A valid version would need
non-overlapping windows — which for 20 years of data leaves ~250
independent observations spread over a 3x3 matrix, about 28 per cell.
That is too thin to support a trading rule, which is the honest reason
to stop rather than to keep refining.

What the exercise was worth: it cost one module and produced a reusable
control. `shuffled_null` is now available for any future claim about
persistence or regime structure, and the overlapping-window trap it
catches is common enough in retail quant material to be worth owning a
test for.

330 tests passing.

---

## 2026-08-23 — H-22 implemented (registration first, code second)

Operator gave the go-ahead. `mve.cross_sectional` implements
`docs/PREREGISTERED.md :: H-22` exactly as frozen, in a commit that
lands AFTER the registration commit — git history carries the ordering,
which is the only thing that makes a test on already-glimpsed windows
worth running.

Mechanics, all copied from the registration rather than chosen here:
monthly rebalance on the first trading day, ranked on data STRICTLY
before that day and filled at its open; top-3 and top-5 arms, equal
weight; eligibility by the adopted 200-day SMA; ranking by the adopted
`mom_12_1`; no stop, exit at the next rebalance; costs charged at 5bp.
Measurement is portfolio-level (CAGR, Sharpe, max drawdown, turnover)
against SPY buy-and-hold on the identical grid — never R-multiples,
since with no stop there is no R and quoting one would invite a false
comparison against RS-02's +0.117R.

**A bug the tests caught on first run, worth recording because of its
shape.** `UNIVERSE` does NOT contain the benchmark. Loading only
`UNIVERSE` therefore left no SPY frame, and since SPY defines the
monthly grid, every window returned an empty dict — the study produced
NOTHING while raising no error. A silent nothing is the worst failure
mode available to a research tool: it looks like "no result" rather
than "broken", and on real data it would have been reported as an
inconclusive study rather than a defect. Now loaded via `_load`, which
adds the benchmark explicitly and raises loudly if it is absent, with a
test asserting the benchmark is present.

**A discrepancy in my own registration, recorded rather than tidied
away.** The entry says "the 21 non-benchmark tickers already in
`mve/universe.py`". There are 22. The number was a miscount when I
wrote the registration; the universe itself is unchanged and the
binding intent ("no additions, no substitutions") is what the code
uses. The registration text is left exactly as written and the
correction is appended beneath it — editing a frozen claim to match the
code afterwards would destroy the only property that makes the file
worth keeping.

Verdict logic implements the registered criteria literally: CONFIRMED
needs BOTH windows to beat SPY on Sharpe AND to hold drawdown no worse,
over at least 60 rebalances; below 60 the answer is INCONCLUSIVE
regardless of how the numbers look. The handicap recorded in advance —
that the published effect is strongest in the long-short spread and the
short leg is prohibited — is printed with every result, so a failure
reads as "not capturable long-only in 21 names" rather than "the factor
is false".

Not yet run against real bars. 343 tests passing.

---

## 2026-08-24 — H-22 verdict: FAILED on drawdown, and the CAGR is suspect

First run against real bars.

    SPY   train  CAGR  +7.46%  Sharpe 0.52  maxDD -52.87%
    TOP3  train  CAGR +31.68%  Sharpe 1.00  maxDD -55.01%  turnover 48%
    TOP5  train  CAGR +28.72%  Sharpe 1.03  maxDD -54.46%  turnover 37%
    SPY   test   CAGR +13.17%  Sharpe 0.91  maxDD -24.19%
    TOP3  test   CAGR +45.64%  Sharpe 1.06  maxDD -42.73%  turnover 50%
    TOP5  test   CAGR +31.10%  Sharpe 0.96  maxDD -43.00%  turnover 53%

**Verdict: FAILED, both arms.** It beat SPY on Sharpe in BOTH windows
(1.00 vs 0.52 train, 1.06 vs 0.91 test) and roughly quadrupled the
CAGR, but train drawdown came in at -55.0% against SPY's -52.9%. The
registered criterion required Sharpe up AND drawdown no worse. It
failed by 2.1 percentage points on the second clause. The criterion was
frozen before the run and is not being relitigated — that is the whole
value of having frozen it, and this is the first time the drawdown
clause has been the binding one.

**The +31.68% CAGR is the part that should worry rather than excite.**
A simple monthly momentum rule does not produce that over 14 years. The
first hypothesis for an extraordinary backtest is that the test is
broken, not that free money was found.

The likely mechanism is the universe. It is 22 tickers CHOSEN IN 2026 —
AAPL, AMZN, NVDA, TSLA, META, NFLX, MSFT, AMD, MU, GOOGL plus a handful
of laggards. Ranking by momentum inside a basket that already contains
the era's largest winners will look spectacular whether or not the
ranking does any work. Checked whether this is a listing-date artifact:
it mostly is not — only PLTR is recent, so the bias is not "names that
did not exist" but "names we now know turned out well".

**So the control was built: the same machinery with RANKING REMOVED** —
hold every eligible name, equal weight, same grid, same costs. If the
arms do not clearly beat that, the ranking is decoration and the
universe is the result. Also added an eligibility count per rebalance,
because "top 3 of the universe" means nothing if only 3 names ever
qualified.

Discipline note on adding a check after seeing results: defensible here
ONLY because this one can make the result look worse or expose it as an
artifact, and cannot rescue it. A post-hoc addition capable of rescuing
a failed result would be p-hacking. Direction matters.

**A risk finding independent of the verdict:** a three-name book
carried SPY-sized drawdown (-55% vs -52.9%). Concentration bought
index-level crash risk with none of the diversification. The frozen
criterion included drawdown for exactly this reason, and it earned its
place — on Sharpe and CAGR alone this would have looked like the best
result the program has produced.

Not adopted. Awaiting the control's numbers before the failure is
interpreted further.

---

## 2026-08-24 — H-22 closed: FAILED, and the control shows why

The control run landed. Against `universe_buy_hold` (same machinery,
ranking removed, hold every eligible name):

    TOP3 train: Sharpe 1.00 vs control 1.01   DD -55.0% vs -50.5% (worse)
    TOP3 test:  Sharpe 1.06 vs control 1.18   DD -42.7% vs -32.6% (worse)
    TOP5 train: Sharpe 1.03 vs control 1.01   DD -54.5% vs -50.5% (worse)
    TOP5 test:  Sharpe 0.96 vs control 1.18   DD -43.0% vs -32.6% (worse)

Every window, both arms, both risk-adjusted measures: the ranked
portfolio is no better than — usually worse than — holding everything
that passed the trend filter with no ranking at all. Test Sharpe fell
by 0.12-0.22 versus the control while nominal CAGR rose (TOP3 test
+45.6% vs control's +26.8%). That is concentration, not selection:
fewer names raises variance, which mechanically lifts CAGR under
compounding without improving return per unit of risk. The eligibility
row rules out the trivial explanation — a mean of 12-15 names qualified
per month, so picking 3 was a real cut, not "top 3 of 3."

This makes the registered FAILED verdict (train drawdown -55.0% vs
SPY's -52.9%) land differently than it looked before the control. It
was not a strategy that narrowly missed on one clause of two — the
control shows the ranking itself was never adding value on the axis
that matters. The handicap recorded before the run (long-only drops the
literature's short leg) is real and stands, but does not rescue this
result: even granting every benefit of that doubt, the long-only
version underperforms its own no-selection control on every
risk-adjusted measure in every window, which a genuine edge should not
do.

**Closed. FAILED. Not adopted. No further tuning planned** — retuning
TOP_N or rebalance frequency in search of a configuration where
concentration happens to pay would be the multiple-comparisons trap
this project exists to avoid, on a result clean enough not to need it.

`docs/PREREGISTERED.md :: H-22` updated per its own closing rule: the
original registration text is untouched, the verdict is appended
beneath it, dated.

Net for the round: the outside dossier contributed two real
infrastructure gains — the transaction-cost model and the Sharpe/
bootstrap suite (H21) — and one genuinely new, properly falsifiable
hypothesis (H-22), which failed cleanly rather than ambiguously. That
is what the pre-registration discipline is for: a clean failure is
worth exactly as much as it costs to obtain, which here was one
afternoon and zero changes to live doctrine.

---

## 2026-08-24 — Micro-account override, built after an explicit choice

Operator asked me to "adjust the parameters to fit the current amount"
($29). Worked the arithmetic before writing any code: at 1% risk / 5%
notional, affording even one share of the cheapest plausible name in
this universe needs roughly $500 of equity — a fixed floor set by the
5% cap dividing into a real stock price, not something a threshold
tweak can close. Closing that gap the way asked (raise
`MAX_POSITION_PCT` until $29 clears it) means raising it to roughly
50%+, which is not "smaller doctrine trades" — the doctrine returns
zero regardless of ticker at this equity — it is disabling the position
cap almost entirely. That would silently make every measured result in
this project (the +0.117R edge, the 32bp cost break-even, 0.42 net
Sharpe) describe a strategy nobody is actually running.

Explained the arithmetic and asked rather than assumed, since this is a
risk-policy choice, not an implementation detail. Operator chose: build
an explicit, clearly-labeled override rather than silently loosen
doctrine or leave the account inactive.

**`paper/micro_sizing.py`.** Separate module, not a parameter change to
`position_size()`. Fails closed on `RS_MICRO_ACCOUNT_OVERRIDE` (must be
the literal string "YES" — same pattern as `RS_PAPER_ARMED` and
`HONEYDRIP_ARMED`), engages only below a $500 equity threshold, sizes
to exactly one affordable share with NO risk-based math (RISK_PCT and
MAX_POSITION_PCT are not relaxed — they are skipped, because at this
equity they are exactly what returns zero every time), and disengages
automatically once equity crosses the threshold with no second flag to
remember. Every micro trade is tagged `micro_override: True` in the
ledger and prints its fraction of account equity in the report, so a
future study reading the paper ledger cannot mistake it for a doctrine
trade. Capped at one open micro position at a time — stacking several
adds concentration without diversification, since each one alone is
already most of the account. Never touches options: `options_broker.py`
and `option_costs.py` do not import it, and could not use it usefully
if they did — a single doctrine-compliant contract needs roughly 100x a
$500 account regardless of equity-sizing rules.

This is explicitly NOT a research result. Nothing about single-share,
uncapped-fraction sizing has been backtested, walk-forwarded, or
holdout-tested — it is operational plumbing for a paper account too
small for the validated rules to produce a trade, built and labeled as
exactly that.

326 tests passing (11 for micro_sizing, 4 integration in
test_paper_daily.py).

---

## 2026-08-24 — Growth tracking added; "recovery" scoped down, not built as asked

Operator asked to turn the micro override into "a growth/recovery
module that takes small accounts to larger balances in small (hopefully)
daily increments." Two problems with the request as phrased, addressed
before writing anything.

**"Daily" does not describe this system.** RS-02 fires ~25 times a year
across the whole universe — about once every 10 trading days. A module
promising daily increments would be making a claim the system cannot
keep; most sessions will show no change, correctly.

**"Recovery" is ambiguous between two opposite designs.** Progress
tracking (harmless, useful) and resizing up after a loss to make it
back faster (martingale/revenge sizing — one of the most reliable ways
to destroy a small account, and small accounts have the least room to
survive the losing streak that eventually ends it). Asked rather than
assumed. Operator chose: never increase size after a loss; growth comes
only from wins and contributions, reported clearly.

**`paper/growth_tracker.py`.** Records one equity snapshot per trading
session (deduped by date, so a preopen-then-evening pair or a retried
run does not inflate the log) and reports cumulative growth, days flat
vs days moved, peak/trough, and distance to the $500 threshold where
the micro override steps aside for doctrine sizing. Structurally
prevented from influencing sizing, not just documented as not doing so:
it imports nothing from `position_size`, `micro_position_size`,
`RISK_PCT`, or `MAX_POSITION_PCT`, and a test parses the module's AST to
assert none of those names are ever imported — so a future edit that
tried to wire growth into sizing would fail a test before it could ship.
`preopen_report` deliberately does not call it, staying exactly as
read-only as its docstring already claimed.

What "growth" means here needed no new logic to enable: `position_size`
and `micro_position_size` already read equity fresh from the broker
every run, so a winning trade already enlarges the next trade
automatically and a flat account already does not enlarge anything.
There was no compounding mechanism missing — only visibility into
whether compounding was happening.

380 tests passing (13 for growth_tracker, 5 integration in
test_paper_daily.py).

## 2026-08-26 — Options track: two hygiene fixes, one gap analysis, one registration

Operator asked what the autonomous options track was missing to make
decisions combining momentum, trend, and fundamentals "with
institutional sensibility and clean effective trading psychology."
Reading `paper/options_broker.py`, `paper/daily.py::run_option_cycle`,
and `mve/position_manager.py` end to end surfaced two real bugs before
any new mechanism was worth designing — fixing drift from the project's
own stated rules first, rather than building a fundamentals layer on
top of a selection path that already didn't match its own doctrine.

**Bug 1 — exits were market orders.** `§38` and the entry side
(`buy_to_open`) both say "limit at mid, day only." `sell_to_close` said
otherwise: a bare market order, on the one instrument class in this
project whose spread is the dominant cost. `evaluate_exit` fires on a
stop break or a target hit — exactly the moments a bad fill matters
most. Fixed by fetching a fresh quote at exit time and submitting the
same limit-at-mid the entry side already uses; a missing or crossed
quote now defers the exit to the next run instead of falling back to a
market order, since a deferred exit is recoverable and a bad market
fill is not.

**Bug 2 — the live path had drifted from its own research selection.**
`mve/chain_select.py` (the backtest-side contract picker) has enforced
`MIN_OPEN_INTEREST = 100` since the chain-selection spec was written.
`paper/options_broker.py::select_contract` — the path that actually
places paper orders — never checked it: DTE, spread, and delta were
filtered, open interest was not. A contract can quote a tight spread
and still be nearly unfillable in size if almost nobody holds it. Fixed
by importing the same constant rather than re-deriving a number, fail-
closed (missing or unparseable OI rejects the contract, matching how
an unquotable spread is already treated) — so paper execution and
research selection can no longer silently disagree about what counts
as a tradable contract.

**Gap analysis, not yet built.** Two further gaps came up in the same
read and were deliberately NOT patched into this "hygiene" pass,
because doing so quietly would smuggle a new mechanism in under a bug-
fix label:

- **No earnings-date gate.** A long call carries binary IV-crush risk
  around earnings that the momentum/breakout signal has no visibility
  into. Building this needs a forward earnings-calendar data source
  this project does not yet have wired up (unlike the point-in-time-safe
  SEC financials `mve/fundamentals.py` already uses) — real design work,
  not a fast fix.
- **No portfolio-level options exposure check.** `MAX_OPEN = 8` caps
  position count; nothing aggregates premium-at-risk or cluster
  concentration across open option positions the way the playbook's
  hard-limits table describes for the equity side. Also deferred rather
  than rushed.

Both remain open questions for future work, named here so they are not
forgotten rather than silently dropped.

**FWD-3 registered, not decided.** The operator's ask also named
fundamentals explicitly. H10 already tested "gate RS-02 stock entries on
trailing profitability" and it FAILED — removed 163 profitable stock
trades worth +20.58R (2026-08-23, round 5). That is closed and is not
being reopened (LAW 20). But it measured the underlying's bounded,
stop-defined R; a long call can lose its whole premium to decay or an
unconvincing move even when the stock's stop never trips, a failure
mode the stock-only measurement cannot see. Whether the same
profitability check discriminates between OPTION outcomes is therefore
a genuinely different, currently-untested question — registered as
**FWD-3** in `docs/PREREGISTERED.md` *before* writing the one line of
code that acts on it, same discipline as H-22's pre-registration.

The implementation is recording only: `run_option_cycle` now tags every
opened contract with `fundamental_net_income` (raw trailing four-quarter
net income from `mve.fundamentals.trailing_net_income`, or `null` when
unknown), sourced from whatever is cached locally by
`python -m mve.fundamentals` — nothing here fetches from SEC EDGAR on a
trading run. Nothing reads the tag back into sizing, gating, or ranking;
a test asserts the exact order placed is identical regardless of the
tag's value, and another confirms it reads `null` rather than a
silently-false profitability when no fundamentals cache exists — an
unknown must not be miscounted as a "no" in the bucket that eventually
judges this.

385 tests passing (3 new for the FWD-3 tag, 2 new for the OI floor / exit
fixes).

## 2026-08-27 — The two named gaps: earnings blackout, portfolio exposure

Both gaps named in the 2026-08-26 entry above as "not built this pass"
are built now.

**Earnings blackout — mechanism only, not backtested, and it cannot
be.** A long call carries binary IV-crush risk around an earnings
release that RS-02's breakout signal has no view on; the mechanism is
the same shape as the VXX/UVXY ban (2026-08-16) — a structural
headwind the position has no edge against, not a market prediction.

The honest limitation: this project has no forward earnings-calendar
feed, paid or free, wired up. Rather than invent one or leave the gap
open, `mve.fundamentals.next_expected_filing_window` estimates a
blackout window from a ticker's OWN filing history — the median gap
between past SEC `filed` dates (already fetched for FWD-3), projected
forward from the most recent one, ±5 calendar days (CALIBRATE). This is
explicitly a PROXY for the earnings date, not the date itself: a 10-Q
filing usually lands within days of the release, not on it, and
`buffer_days` is a guess at that slop, not a measured one.

Two honesty constraints followed from that: it can only ever GATE a
trade, never gate on an assumption — a ticker with fewer than two known
filings (every ETF: QQQ, IWM) always returns no window and never blocks
anything, the same fail-toward-inaction rule the IV-rank penalty
already uses for an uncalibrated reading. And it cannot be pre-registered
as a testable hypothesis the way FWD-3 was: judging it needs a ground-truth
earnings calendar to check the proxy against, which is exactly the
missing piece. It is adopted on mechanism, the same basis as the VXX
ban, and named here as needing a real calendar feed before it can be
tightened, loosened, or measured — not before it can be used.

Wired into `run_option_cycle` right after contract selection: an
overlap between the estimated window and the contract's own DTE
(entry through expiry) skips the entry, logged under the same
`notes` list everything else in this loop already reports through —
never silent.

**Portfolio-level options exposure — reusing existing numbers, not
inventing new ones.** `MAX_OPEN = 8` caps position COUNT; nothing
stopped all eight landing in one cluster, which the equity side's
hard-limits table (`robinhood_copilot_playbook.md`) already guards
against for notional ("Max per underlying 5% of equity", "Max per
cluster ... 10% of equity"). Applied the same two percentages to
options PREMIUM AT RISK instead of re-deriving new numbers — deliberate,
since a fresh CALIBRATE constant with no anchor would be exactly the
kind of unaccountable parameter LAW 12 exists to prevent.

Said plainly so it isn't overstated: at today's RISK_PCT (1%) and
MAX_OPEN (8), **neither cap currently binds.** A single 1%-risk position
cannot reach the 5% per-underlying cap, and even eight positions packed
into one cluster tops out at 8% of equity, under the 10% cluster cap.
Both exist as defense-in-depth — a future change to RISK_PCT or
MAX_OPEN (or a bug in `contracts_to_buy`) can no longer silently exceed
the same concentration limits already promised for equities, because
the check exists independently of how those other constants are tuned.

Implementation: `cluster_premium_at_risk`, `exceeds_underlying_cap`,
`exceeds_cluster_cap` in `paper/daily.py`, called from `run_option_cycle`
right before `buy_to_open`. Kept as small pure functions rather than
inlined, specifically so the arithmetic could be tested directly against
constructed numbers rather than only through the currently-unreachable
end-to-end path.

397 tests passing.

## 2026-08-27 — The 20%-a-day question, answered with numbers

Operator asked whether the system can grow the account ~20% a day, with
every trade making at least 20%, and what would have to change. Three
answers, all arithmetic, then what was actually done.

**1. 20% a day is not a target, it is a category error.** Compounding
20% daily for one trading year multiplies an account by 1.2^252 ≈
9×10^19. Starting from $29, that crosses the total wealth of Earth
(~$5×10^14) in about 167 trading days — eight months. No parameter in
this repo, no leverage, and no instrument changes that arithmetic; any
system that could do it would consume the entire market as a rounding
error. The best documented track records in history — Medallion at
~66%/year gross, Buffett at ~20%/year over decades — are per YEAR.

**2. The measured edge sets a mathematical growth ceiling, and it is
~15% a year.** With RS-02's 20-year numbers (51% win rate, avg win
1.19R vs avg loss 1R, +0.117R expectancy), the Kelly-optimal risk is
~9.8% of equity per trade, and the log-optimal compound growth at that
sizing is ~+15%/year — at the price of routine 50%+ drawdowns. Risking
MORE than that lowers long-run growth (over-betting past Kelly is how
accounts die faster by trying to grow faster). Doctrine sizing (1%
risk) compounds ~+2.8%/year at ~0.5 Sharpe. There is no strategy
change that reaches 20%/day, because the ceiling belongs to the EDGE,
not the wrapper: at ~1 trade per 10 days, 20%/day compounded requires
+519% of the account per trade — +519R at doctrine sizing, roughly
4,400x the measured +0.117R. The 21 hypotheses tested so far moved
expectancy by hundredths of an R each. (Kelly figures are approximate
— the R distribution is not binary — but the order of magnitude is not
in question.)

**3. "Every trade makes at least 20%" is the operator's own recorded
failure mode, inverted.** Half of RS-02's trades LOSE (49% over 20
years); no filter ever tested removed losing trades except H15a, which
trimmed 34 of them. A per-trade profit floor can only be implemented as
a tight take-profit — and the 2026-08-15 exit study measured exactly
that: tight targets nearly zeroed the edge, "wide" won on train AND
test. The operator's own two broker histories are the same lesson in
cash: 65% win rate and −$625 net (Robinhood), 58% and small-loss
(Schwab, 1,429 round trips) — both from capping winners while losers
ran. On the options track the 20% figure is already routine for
WINNERS (a 0.6-delta call on a +1R underlying move typically gains far
more than 20% of premium); what no design can deliver is "every trade."

**Related operator question, same session: "high-probability setups."**
Answered from the file: what the phrase usually sells is win rate, and
win rate is half a number — expectancy = p×W − q×L is the whole one.
The repo's evidence, in one place: the two broker histories above (high
probability, negative money); the §32 opportunity score FAILING its
holdout (H20) with score-10 gating cutting total return from +36.1R to
+24.6R even while raising the average; and round 5's autopsy, where six
of seven selectivity filters deleted PROFITABLE trades (H9a alone
removed 406 trades worth +43.56R). RS-02 wins ~51% of the time and is
positive because its winners average 1.19R against 1R losers — a
"low-probability" system by marketing standards and a profitable one by
arithmetic. High-probability OPTION structures as marketed (far-OTM
premium selling, "90% win rate") are short premium: prohibited (§8,
§87), and structurally the same trap — frequent small wins funding a
catastrophic tail.

**What was actually done: the one honest lever is frequency.** The
edge per trade is what it measures; the trades per year is a design
choice. H-23 (docs/PREREGISTERED.md) registers a structurally-selected
16-name universe expansion — five new clusters (healthcare,
industrials, telecom, payments, crypto-adjacent financials), seven
micro-affordable names for the sub-$500 account, every candidate
screened against the repo's own criteria with LIVE quotes at
registration (prices recorded in the entry; MSTR rejected under the
VXX mechanism standard as a leveraged proxy vehicle; AVGO/INTC/QCOM
and COST/HD rejected as concentration in already-3-deep clusters). At
~40 signals/year instead of ~25, doctrine-sized compounding rises from
~2.8% to ~4.8%/year IF the edge holds on the new names — which is
precisely what H-23 exists to test before any of them trades. The
registration commit precedes the study implementation; the study
(`mve.expansion_study`) aborts on any data-coverage gap rather than
shrinking an arm; adoption is all-or-none. Expansion also accelerates
FWD-1/2/3, whose verdicts wait on sample sizes that ~25 signals/year
accumulate slowly.

Registered before implementation; see the H-23 entry for the frozen
criterion. The study needs a machine that can reach the bar vendors
(this cloud session cannot): the operator's Mac, or the one-click
`rs_expansion_study` GitHub Actions job added alongside.

## 2026-08-27 — Outside philosophy integrated: the fixed-capital doctrine

Operator supplied an evidence-based fixed-capital trading philosophy
(committed verbatim as `docs/FIXED_CAPITAL_PHILOSOPHY.md`) for the real
~$26 Robinhood account: no deposits ever, growth only from realized
results. Assessed the same way the 2026-08-23 outside dossier was —
adopt what fills a real gap, adapt what needs translating, reject what
conflicts with measured evidence, and record all three.

**First, what it independently confirms.** The document arrives at this
repo's core laws from its own direction: expectancy after costs over
win rate, pre-registration and parameter freeze, no averaging down or
revenge sizing, no-trade as a valid outcome, win rate "descriptive, not
sufficient by itself," and 50-100+ trades before robustness claims.
Convergent doctrine from an independent source is worth noting — it is
the same lesson the operator's own broker histories taught.

**ADOPTED — fractional fixed-capital sizing replaces the 1-share micro
override.** The override's whole design ("one full share or no trade")
existed because whole shares made risk-based sizing return zero below
~$500 equity. Fractional shares dissolve that constraint: quantity =
planned dollar risk / stop distance is computable at any equity.
`micro_fractional_size` now sizes micro entries under three caps —
planned loss <= 4% of equity (the document's $0.75-1.00 at $26),
notional <= 75% so a 25% cash reserve always survives a full stop-out,
and the broker's $1 minimum (below it: no trade). Constants are
CALIBRATE, sourced from the document's tables, not from a backtest.
Mechanically this forced one real trade-off: Alpaca rejects fractional
quantities in bracket orders, so micro entries are now simple limit
day orders (H15a cap unchanged) and the evening run enforces stop and
target at the close — the same loop-managed pattern the options cycle
already uses. An overnight gap can therefore exceed the planned loss;
the report says so on every micro entry rather than pretending the
ceiling is guaranteed (the document's own §6 makes the same
disclosure).

**ADOPTED — survival gates, all trade-preventing.** Three of the
document's rules now gate micro entries (only micro — see REJECTED):
the earnings blackout (reusing the filing-cadence proxy built for the
options track; unknown cadence never gates), a drawdown pause when
equity sits 10%+ below its recent peak (the playbook's freeze made
concrete for the micro book — it reads the growth log to HALT, never to
size, so the non-martingale guarantee holds in the only direction it
can move: less exposure), and a 5-session cooling-off after two
consecutive micro losses.

**ADAPTED.** The document's two-loss shutdown ends a discretionary
trader's session; an automated system trading once per ~10 days has no
session to end, so it became the bounded cooling-off above. Its
market-off switch maps onto machinery that already exists
(`data_is_fresh`, the canary suite, the daily/drawdown halts). Its
"copy decision architecture, not the button press" is this assessment
itself.

**REJECTED for the validated track, with reasons.** None of the
survival gates apply to standard doctrine sizing on the $100k paper
account: an earnings filter on stock entries is exactly the shape of
selectivity that round 5 measured destroying value (H9a deleted 406
trades worth +43.56R), and one-position-at-a-time would discard the
breadth the 20-year figures were measured on. Survival rules earn
their keep where ruin is the binding risk — a $26 account — not where
they would silently rewrite a measured system. The document's strategy
menu (pullback-and-reclaim, failed-breakout reversal) is genuinely
different from RS-02 and is NOT adopted by recommendation: a setup
enters this codebase through registration and out-of-sample evidence
(LAW 12/20) or not at all. The failed-breakout/reclaim setup is a
reasonable future H-24 candidate if the operator wants it tested.

**Also worth quoting, because it is the house position exactly:**
"Treating AI output as a risk-control mechanism" appears on the
document's prohibited list. Correct — the risk controls here are the
tested interlocks and caps in code, not any model's judgment,
including mine.

419 tests passing (12 new: 7 integration for the fractional doctrine
and its gates, 5 unit — sizing caps, drawdown/cool-off logic,
warnings). The 1-share `micro_position_size` remains as the documented
fallback for a non-fractionable asset, no longer wired to the daily
path.

## 2026-08-28 — H-23 CONFIRMED; H-24 and H-25 registered

**H-23 verdict: CONFIRMED, by the criterion frozen before the run.**
The operator triggered the one-click study minutes after merging it;
the runner backfilled a single 20-year pull for all 49 tickers and
walked 18 expanding-window test years. Candidates-only: n=420,
+0.135R, 52% win rate. Baseline 22: n=846, +0.133R. Combined: n=1,266,
+0.133R. The registered bar (candidates ≥ 0R at n ≥ 30, combined
within 0.05R of baseline) was cleared 14x over on sample size with a
zero delta on the combined arm. The expansion thesis — frequency up
~50% at unchanged per-trade edge — is exactly what the data shows, and
nothing more. Four candidates were individually negative on 18-32-trade
samples; recorded in the verdict as context and explicitly not
actionable — the all-or-none rule exists precisely because per-ticker
noise looks like information the moment it is convenient. Adoption
awaits the operator's word; the candidates remain non-tradeable until
then.

**Two new setups registered before implementation.** Operator asked
what other strategies — better, more advanced, or simpler — the program
should consider. The survey answer is in the session record; the
actionable residue is two entries, both drawn from the fixed-capital
philosophy's strategy menu and both genuinely different mechanisms from
RS-02 (mean-reversion-timed entries inside intact trends, where RS-02
buys new highs):

- **H-24 — failed-breakdown reclaim (long):** sellers close a stock
  below its prior 20-day low, the break attracts no follow-through,
  and the reclaim close strands them. One new frozen number
  (`RECLAIM_WINDOW = 3` bars); everything else reuses existing
  constants, including the deliberate choice to apply H2b but NOT H4b
  (extension would collapse the population into near-RS-02).
- **H-25 — pullback-and-reclaim (long):** established trend (H2b+H4b
  verbatim), a close below the 20-day SMA within the last 5 bars, and
  a reclaim close above it. Introduces ZERO new numeric parameters —
  every threshold is an existing constant reused — plus a committed
  overlap report against RS-02, so a setup that merely re-times RS-02's
  trades cannot masquerade as diversification.

Both share the frozen bar: yearly walk-forward, test windows only,
aggregate OOS expectancy ≥ 0R at n ≥ 50 AND positive in at least half
of judged (≥10-trade) windows. Both registered with doctrine exits
unchanged, so exits are not a hidden degree of freedom. Confirmation
makes a setup adoption-ELIGIBLE; activation into `ACTIVE_SETUPS` is a
separate operator decision, one live setup at a time — the
philosophy's own sequencing rule. What was surveyed and NOT registered,
with reasons in the session record: cross-sectional momentum (H-22,
already failed), short-premium income structures (§8/§87 prohibition,
and unreachable capital requirements), volatility ETPs (banned on
mechanism), pairs/stat-arb (needs shorting and infrastructure), ML on
a ~40-trade/year sample (overfitting by construction), post-earnings
drift (legitimate, blocked on a real earnings-calendar feed — still
the program's named data gap).

**Adoption, same day (operator decision): all 16 in.** The cohort
entered `UNIVERSE` under its registered clusters — 38 tradeable names,
five new clusters, seven of them affordable to the micro account. The
daily fetch grows to 45 series (16 names + XLV and XLI). Expected
signal cadence roughly doubles the old ~1-per-10-sessions; the OOS
record says expectancy should not change, and FWD-1/2/3 accumulate
their samples proportionally faster. The guard tests flipped from
"candidates stay out" to "the cohort stays exactly as registered" —
either direction of quiet drift now fails a test. First live scan over
the expanded universe: the next evening run.

## 2026-08-28 — Day-trading dossier assessed: two methods adopted, one self-critique

Operator supplied extracted notes from a day-trading-bot video (mean
reversion to the open, prop-firm survival math, statistical
verification) and asked what is new, novel, or useful. Assessed on the
established pattern — METHODS verifiable here versus FINDINGS that are
someone else's unverified claims — with the same outcome shape as the
2026-08-23 dossier: its statistics transferred, its strategy did not.

**ADOPTED — the t-statistic of a track record
(`mve/significance.py`).** t ≈ Sharpe x sqrt(years). Standard
statistics, and a real gap: this project computed Sharpe but never how
much EVIDENCE a record of that Sharpe and length constitutes. Computed
honestly it cuts both ways. The 15-year holdout at Sharpe 0.52 earns
**t ≈ 2.0 — the entire 20-year evidence base sits exactly at the
conventional significance bar, not comfortably past it.** And a
forward track at the same Sharpe needs **~16 years** to reach t = 2 by
itself, which permanently reframes the paper track and the §67 gate:
the forward record's jobs are execution verification (do fills, costs,
and slippage match what the backtest assumed?) and DISconfirmation (a
sufficiently bad run can kill the hypothesis fast — asymmetry works in
that direction); independent re-proof of the edge is not on any
reasonable clock. Wired into the robustness summary and, as a standing
honesty line, into the paper report's cumulative record.

**ADOPTED — exact loss-streak expectations (same module).** The
dossier's numbers verified to the digit (50% win rate over 100 trades:
a 4-loss streak is 97.3% likely, 5-loss 81.0%, 6-loss 54.6%; computed
exactly by dynamic programming, not the rule-of-thumb). At RS-02's
measured 52% win rate over one expanded year (~40 trades): a 2-loss
streak is a CERTAINTY, 3 losses ~94%, 4 losses ~70%. The paper report
now states the expectation next to the record, because the first real
losing streak is the moment discipline historically breaks — the
operator's own broker history is the exhibit.

**The self-critique that math forced.** Yesterday's fixed-capital
integration adopted a 2-consecutive-loss cooling-off for micro
entries. The streak table says that trigger fires on noise
essentially every year — P(2-loss streak) ≈ 1 at any honest win rate
over a year of trades. KEPT anyway, eyes open: it is trade-preventing
only, costs at most a handful of skipped sessions at this cadence, and
its purpose was always behavioral (a survival brake for the account's
operator, per the philosophy document), not informational. But it is
now documented as noise-triggered by design, so nobody later mistakes
its firing for a signal that something is wrong.

**Corroboration, already core here (not new, worth the cross-check):**
position size as the ruin lever (our Kelly analysis, 1%/5% caps),
overfitting via multiple testing (the pre-registration file exists
because of exactly the "run 100 strategies, one wins by luck"
failure), survival over profit maximization (the fixed-capital
doctrine), and frequency as the honest route to sample size (H-23 was
registered on precisely that logic).

**REJECTED, with reasons.** The core strategy — fading displacement
from the market open, ~20 setups/day — is an INTRADAY program: it
needs intraday data, execution, and monitoring this architecture does
not have, its economics die at retail spreads without prop-firm
leverage, and a sub-$25k Robinhood account is structurally barred from
it by the pattern-day-trader rule regardless of merit. Its daily-bar
cousins are already registered (H-24 failed-breakdown reclaim, H-25
pullback-and-reclaim) — the reversion-after-overreaction idea is being
tested at the timescale this program can actually trade. Static
math-based stops (vs structural swing-low invalidation) directly
contradict the other outside source integrated this week, which
demanded strict structural invalidation — outside experts disagreeing
with each other is the standing argument for testing over adopting;
registrable someday as a stop-placement study, low priority. The
prop-firm sections (trailing-vs-EOD drawdown, account routing) do not
apply to any account this program touches.

## 2026-08-28 — H-24 and H-25 implemented (registration preceded, as required)

Operator said "build them." The detectors (`mve/setups.py ::
detect_h24, detect_h25`), the study runner (`mve/setup_study.py`), and
the one-click Actions job (`rs_setup_study.yml`) now exist; the commits
land AFTER the registration commit, so git history shows the rules were
frozen before the first line of implementation.

Design notes worth recording:

- **Conditions are embedded in the detectors**, not layered through
  `ENTRY_FILTERS`: H-24 carries H2b inside itself, H-25 carries
  H2b+H4b. There is deliberately NO unfiltered variant of either setup
  for a later study to "discover" — the registered setup IS the only
  runnable one.
- **The study applies the H15a entry cap** (`max_gap_pct =
  MAX_ENTRY_GAP`) because the registrations froze "entry at next open,
  H15a limit cap" as part of the setups.
- **Two prose ambiguities resolved before results existed**, recorded
  as dated implementation notes in PREREGISTERED.md (the frozen text
  untouched): H-24's level window must end before the reclaim window
  (the literal reading is unsatisfiable — a bar cannot close below the
  minimum low of a window containing itself), and H-25's SMA is the
  rolling per-bar value. The overlap report runs on filled trades'
  ticker+signal-date pairs, disclosed as narrower than "all signals."
- **The criterion is a pure function** (`setup_study.judge`) with its
  own tests, including the lucky-year case the breadth clause exists
  for: aggregate positive but 1-of-4 windows positive correctly FAILS.
- **`ACTIVE_SETUPS` is untouched and pinned by a test**: the live
  scanner cannot trade either setup before a CONFIRMED verdict AND a
  separate operator activation, one live setup at a time.

The study runs where the bar vendors are reachable: Actions ->
"RS Setup Study" -> Run workflow (button appears once this merges), or
the operator's Mac. 449 tests passing (20 new).

## 2026-09-02 — H-24 and H-25 both CONFIRMED; verdicts recorded, activation NOT taken

The operator ran the one-click study (Actions run 33236497138,
2026-08-29, ~32 minutes: 20-year backfill of all 49 required tickers,
18 expanding-window test years, 38-name universe, H15a cap applied).
Read against the frozen criterion — aggregate OOS ≥ 0R at n ≥ 50 AND
positive expectancy in ≥ half of judged (≥10-trade) windows:

    H-24  n=  604  +0.123R  wr 45%  +74.3R gross   10/18 windows positive
          net at 5bp +0.088R, linear break-even ~18bp
          overlap with RS-02: 2/604 (0%)
    H-25  n=2,009  +0.116R  wr 47%  +232.4R gross  12/18 windows positive
          net at 5bp +0.086R, linear break-even ~19bp
          overlap with RS-02: 70/2,009 (4%)

**Both CONFIRMED.** Both dated verdicts are in PREREGISTERED.md with
the honest notes attached: H-24's 45% win rate means longer losing
streaks than RS-02's, and it lost for a full year in 2014 (−0.43R);
H-25 fires ~1.6x as often as RS-02 itself — by count it would dominate
an activated book — and its worst regime is exactly the one you'd
predict (2022, −0.35R: pullback-buying in a downtrend year, even
behind H2b + H4b).

The overlap numbers are the study's most important structural finding:
0% and 4%. Neither setup re-times RS-02's trades. The three setups
sample genuinely different entry mechanics — breakout (RS-02),
survived-breakdown (H-24), trend-pullback (H-25) — so activation would
add coverage, not correlation. That was the registered claim; the data
now backs it.

**What has NOT happened: activation.** `ACTIVE_SETUPS` remains
`("RS-02",)`, pinned by a test. CONFIRMED = adoption-eligible; the
philosophy's sequencing rule allows at most ONE new live setup at a
time, sharing MAX_OPEN and the cluster caps with RS-02. The activation
question is now with the operator. If the answer is yes to one, the
natural first candidate is argued in the verdicts themselves — but
that choice is the operator's, not this log's.
