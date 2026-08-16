"""Hypothesis studies — RS-02 entry filters (spec §72; MARKET_THEORY queue).

Round 1 (2026-08-15, resolved): H1 52wk-high (both widths) NOISE;
H2a SPY-regime NOISE; H2b stock-above-own-200d ADOPTED into doctrine.

Round 2 (current) tests INCREMENTALLY on top of the adopted doctrine —
every variant includes the H2b regime filter, and verdicts compare
against BASELINE_H2b, not the raw CONTROL. A filter only earns adoption
if it improves the system actually being run.

H4 — momentum-quality screen (Jegadeesh-Titman 12-1 momentum, skipping
     the last month to avoid the short-term-reversal window): does
     requiring positive long-term momentum — a mechanical, point-in-time
     proxy for "quality" that never names tickers — improve RS-02?
     (Motivating forensics: AAL/BAC were the only consistent RS-02
     losers. Hard-coding those tickers out would be peeking; a
     pre-registered mechanical screen is the honest version.)
H6 — one-day-spike guard (short-term reversal): does skipping signals
     whose breakout DAY itself gained more than X% — buying into an
     already-stretched move — improve RS-02?
H5 — earnings blackout: DEFERRED, needs per-ticker earnings dates
     (no free offline source wired yet).

Adoption rule (pre-registered, LAW 12/20): beat BASELINE_H2b on TRAIN
and CONFIRM on TEST. Fewer trades with equal expectancy is NOT an
improvement.

    python -m mve.hypotheses
"""
from __future__ import annotations

import pandas as pd

from .backtest import DATA_ROOT, run_backtest
from .setups import above_sma  # canonical impl — H2b adopted into live doctrine
from .store import DataStore

TRAIN_END = "2024-12-31"
TEST_START = "2025-01-01"
HIGH_WINDOW = 252               # trailing sessions ~ 52 weeks
MOM_LOOKBACK = 252              # 12-1 momentum window (CALIBRATE)
MOM_SKIP = 21                   # skip the reversal-prone last month
BASELINE = "BASELINE_H2b"       # verdicts compare against adopted doctrine


def near_52wk_high(bars: pd.DataFrame, pct: float) -> bool:
    """Close within `pct` of the trailing 252-bar high (point-in-time).
    (Round 1: NOISE at both widths — kept for re-research.)"""
    highs = bars["high"].iloc[-HIGH_WINDOW:]
    return float(bars["close"].iloc[-1]) >= float(highs.max()) * (1.0 - pct)


def mom_12_1(bars: pd.DataFrame) -> float | None:
    """Trailing 12-1 month return: close 21 bars ago vs 252 bars ago.
    None (fail-closed at the filter) with insufficient history."""
    if len(bars) < MOM_LOOKBACK + 1:
        return None
    c = bars["close"]
    return float(c.iloc[-MOM_SKIP]) / float(c.iloc[-MOM_LOOKBACK]) - 1.0


def quality_mom(bars: pd.DataFrame, min_mom: float = 0.0) -> bool:
    """H4: positive (or better) 12-1 momentum. Fail-closed."""
    m = mom_12_1(bars)
    return m is not None and m > min_mom


def calm_breakout(bars: pd.DataFrame, max_gain: float) -> bool:
    """H6: the signal day's own return stays under `max_gain` — skip
    entries chasing a one-day spike. Fail-closed."""
    if len(bars) < 2:
        return False
    c = bars["close"]
    return float(c.iloc[-1]) / float(c.iloc[-2]) - 1.0 < max_gain


VARIANTS = {
    "CONTROL":            None,                       # context only
    "BASELINE_H2b":       lambda t, bars, bench: above_sma(bars),
    "H4a_mom_pos":        lambda t, bars, bench: (above_sma(bars)
                                                  and quality_mom(bars)),
    "H4b_mom_10pct":      lambda t, bars, bench: (above_sma(bars)
                                                  and quality_mom(bars, 0.10)),
    "H6a_no_spike_5pct":  lambda t, bars, bench: (above_sma(bars)
                                                  and calm_breakout(bars, 0.05)),
    "H6b_no_spike_8pct":  lambda t, bars, bench: (above_sma(bars)
                                                  and calm_breakout(bars, 0.08)),
}


def run_hypotheses(store: DataStore, setup: str = "RS-02") -> dict:
    out = {}
    for name, f in VARIANTS.items():
        train = run_backtest(store, end=TRAIN_END, active=(setup,),
                             entry_filter=f)
        test = run_backtest(store, start=TEST_START, active=(setup,),
                            entry_filter=f)
        out[name] = {
            "train": train.per_setup().get(setup),
            "test": test.per_setup().get(setup),
            "filtered": train.filtered_signals + test.filtered_signals,
        }
    return out


def summary(results: dict) -> str:
    lines = ["HYPOTHESIS STUDY — RS-02 entry filters, round 2 (H4/H6, §72)",
             f"train <= {TRAIN_END} | test >= {TEST_START} | "
             f"verdicts vs {BASELINE} (adopted doctrine)", ""]

    def fmt(s):
        if s is None:
            return "n=  0  exp=   n/a  wr=n/a "
        return (f"n={s['trades']:>3} exp={s['expectancy_r']:+.3f}R "
                f"wr={s['win_rate']:.0%}")

    for name, r in results.items():
        lines.append(f"{name:<19} train: {fmt(r['train'])}   "
                     f"test: {fmt(r['test'])}   filtered={r['filtered']}")
    lines.append("")

    base = results.get(BASELINE, {})
    bt, bs = base.get("train"), base.get("test")
    if bt and bs:
        lines.append(f"Verdicts vs {BASELINE} (adopt only if TRAIN improves "
                     "AND TEST confirms; small n = inconclusive):")
        for name, r in results.items():
            if name in ("CONTROL", BASELINE):
                continue
            t, s = r["train"], r["test"]
            if not t or not s or t["trades"] < 20 or s["trades"] < 10:
                lines.append(f"  {name}: INCONCLUSIVE (insufficient trades)")
                continue
            train_up = t["expectancy_r"] > bt["expectancy_r"]
            test_up = s["expectancy_r"] > bs["expectancy_r"]
            verdict = ("ADOPT-CANDIDATE" if train_up and test_up
                       else "REJECT (train did not improve)" if not train_up
                       else "NOISE (train improved, test did not confirm)")
            lines.append(f"  {name}: {verdict}")
    lines.append("")
    lines.append("LAW 12/20: no filter is adopted from a single pass alone — "
                 "an ADOPT-CANDIDATE gets encoded only by operator decision.")
    return "\n".join(lines)


if __name__ == "__main__":
    store = DataStore(DATA_ROOT)
    if not store.tickers():
        raise SystemExit("No data. Run: python -m mve.backfill")
    from .report import save_and_print
    save_and_print("hypotheses", summary(run_hypotheses(store)))
