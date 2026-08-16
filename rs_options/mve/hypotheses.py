"""Hypothesis studies — RS-02 entry filters (spec §72; MARKET_THEORY queue).

Round 1 (2026-08-15, resolved): H1 52wk-high (both widths) NOISE;
H2a SPY-regime NOISE; H2b stock-above-own-200d ADOPTED into doctrine.
Round 2 (2026-08-16, resolved): H4a/H4b momentum-quality both
ADOPT-CANDIDATES with a dose-response pattern; operator ADOPTED H4b
(>= +10% 12-1 momentum). H6 spike guard: 5% NOISE, 8% REJECT.

Round 2 methodology (kept for the record) tested INCREMENTALLY on top
of the then-adopted doctrine —
every variant includes the H2b regime filter, and verdicts compare
against BASELINE_H2b, not the raw CONTROL. A filter only earns adoption
if it improves the system actually being run.

Round 3 (current): H5 earnings blackout — does skipping RS-02 signals
with an earnings announcement in the near future improve the system?
Two pre-registered widths: 3 calendar days ahead (avoid entering right
into the print) and 21 calendar days ahead (the whole expected hold).
Honest caveat, stated before the data: breakouts sometimes happen
BECAUSE of earnings momentum, so the blackout could as easily cut
winners as losers — that is why it is tested, not assumed.

Round-3 variants include the FULL adopted doctrine (H2b regime + H4b
quality) and verdicts compare against BASELINE_DOCTRINE. Requires
earnings dates on disk: run `python -m mve.earnings` first
(ALPHAVANTAGE_API_KEY env var). Tickers with no earnings file pass the
blackout untouched — correct for ETFs; for stocks it means the fetch
has not run, so fetch before judging.

Adoption rule (pre-registered, LAW 12/20): beat BASELINE_DOCTRINE on
TRAIN and CONFIRM on TEST. Fewer trades with equal expectancy is NOT
an improvement.

    python -m mve.hypotheses
"""
from __future__ import annotations

import pandas as pd

# canonical impls live in setups — adopted filters cannot drift from
# the studied ones (H2b: above_sma; H4b: mom_12_1/quality_mom)
from datetime import date as _date

from .backtest import DATA_ROOT, run_backtest
from .earnings import load_earnings
from .setups import above_sma, mom_12_1, quality_mom, rs02_entry_ok
from .store import DataStore

TRAIN_END = "2024-12-31"
TEST_START = "2025-01-01"
HIGH_WINDOW = 252               # trailing sessions ~ 52 weeks
BASELINE = "BASELINE_DOCTRINE"  # round-3 comparison baseline
BLACKOUT_SHORT = 3              # calendar days ahead (entry into the print)
BLACKOUT_HOLD = 21              # calendar days ahead (whole expected hold)


def near_52wk_high(bars: pd.DataFrame, pct: float) -> bool:
    """Close within `pct` of the trailing 252-bar high (point-in-time).
    (Round 1: NOISE at both widths — kept for re-research.)"""
    highs = bars["high"].iloc[-HIGH_WINDOW:]
    return float(bars["close"].iloc[-1]) >= float(highs.max()) * (1.0 - pct)


def calm_breakout(bars: pd.DataFrame, max_gain: float) -> bool:
    """H6: the signal day's own return stays under `max_gain` — skip
    entries chasing a one-day spike. Fail-closed."""
    if len(bars) < 2:
        return False
    c = bars["close"]
    return float(c.iloc[-1]) / float(c.iloc[-2]) - 1.0 < max_gain


def earnings_clear(earnings: dict, ticker: str, bars, days_ahead: int) -> bool:
    """True when no earnings announcement falls within `days_ahead`
    calendar days AFTER the signal date. Tickers with no earnings on
    file pass untouched (ETFs; unfetched stocks — fetch first)."""
    dates = earnings.get(ticker)
    if not dates:
        return True
    d = _date.fromisoformat(str(bars["trade_date"].iloc[-1]))
    return not any(0 <= (e - d).days <= days_ahead for e in dates)


def build_variants(earnings: dict) -> dict:
    return {
        "CONTROL":           None,                    # context only
        "BASELINE_DOCTRINE": lambda t, b, s: rs02_entry_ok(b),
        "H5a_blackout_3d":   lambda t, b, s: (rs02_entry_ok(b)
                                              and earnings_clear(
                                                  earnings, t, b, BLACKOUT_SHORT)),
        "H5b_blackout_21d":  lambda t, b, s: (rs02_entry_ok(b)
                                              and earnings_clear(
                                                  earnings, t, b, BLACKOUT_HOLD)),
    }


VARIANT_NAMES = ("CONTROL", "BASELINE_DOCTRINE",
                 "H5a_blackout_3d", "H5b_blackout_21d")


def run_hypotheses(store: DataStore, setup: str = "RS-02",
                   earnings: dict | None = None) -> dict:
    if earnings is None:
        earnings = load_earnings()
        if not earnings:
            raise SystemExit("No earnings dates on disk. "
                             "Run: python -m mve.earnings")
    out = {}
    for name, f in build_variants(earnings).items():
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
    lines = ["HYPOTHESIS STUDY — RS-02 entry filters, round 3 (H5, §72)",
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
