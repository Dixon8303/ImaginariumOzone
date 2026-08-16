"""Hypothesis studies H1 & H2 (spec §72; MARKET_THEORY hypothesis queue).

H1 — 52-week-high proximity (George & Hwang 2004): does requiring the
     breakout to be near the trailing 252-bar high improve RS-02?
H2 — 200-day regime switch (Faber-style): does requiring the benchmark
     (or the stock itself) above its 200-day SMA improve RS-02?

Every variant runs against the unfiltered CONTROL on the same train/test
split as the exit study. Adoption rule (pre-registered, LAW 12/20):
a filter is adopted only if it beats CONTROL on TRAIN and CONFIRMS on
TEST. Fewer trades with equal expectancy is NOT an improvement.

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


def near_52wk_high(bars: pd.DataFrame, pct: float) -> bool:
    """Close within `pct` of the trailing 252-bar high (point-in-time)."""
    highs = bars["high"].iloc[-HIGH_WINDOW:]
    return float(bars["close"].iloc[-1]) >= float(highs.max()) * (1.0 - pct)


VARIANTS = {
    "CONTROL":            None,
    "H1a_high_5pct":      lambda t, bars, bench: near_52wk_high(bars, 0.05),
    "H1b_high_10pct":     lambda t, bars, bench: near_52wk_high(bars, 0.10),
    "H2a_spy_above_200":  lambda t, bars, bench: above_sma(bench),
    "H2b_stock_above_200": lambda t, bars, bench: above_sma(bars),
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
    lines = ["HYPOTHESIS STUDY — RS-02 entry filters (H1/H2, §72)",
             f"train <= {TRAIN_END} | test >= {TEST_START}", ""]

    def fmt(s):
        if s is None:
            return "n=  0  exp=   n/a  wr=n/a "
        return (f"n={s['trades']:>3} exp={s['expectancy_r']:+.3f}R "
                f"wr={s['win_rate']:.0%}")

    control = results.get("CONTROL", {})
    for name, r in results.items():
        lines.append(f"{name:<21} train: {fmt(r['train'])}   "
                     f"test: {fmt(r['test'])}   filtered={r['filtered']}")
    lines.append("")

    ct, cs = control.get("train"), control.get("test")
    if ct and cs:
        lines.append("Verdicts vs CONTROL (adopt only if TRAIN improves AND "
                     "TEST confirms; small n = inconclusive):")
        for name, r in results.items():
            if name == "CONTROL":
                continue
            t, s = r["train"], r["test"]
            if not t or not s or t["trades"] < 20 or s["trades"] < 10:
                lines.append(f"  {name}: INCONCLUSIVE (insufficient trades)")
                continue
            train_up = t["expectancy_r"] > ct["expectancy_r"]
            test_up = s["expectancy_r"] > cs["expectancy_r"]
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
