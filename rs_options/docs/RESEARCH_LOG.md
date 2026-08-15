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
