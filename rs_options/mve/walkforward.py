"""Walk-forward stability report for RS-02 (spec §51).

The RS-02 parameters were fixed a priori (not fitted to this history), so
this is a period-stability check: does the edge hold in each successive
out-of-sample-style year, or is it decaying?

    python -m mve.walkforward
"""
from __future__ import annotations

import sys

from .backtest import DATA_ROOT, run_backtest
from .store import DataStore

DEFAULT_SPLITS = [
    ("2021-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
    ("2021-01-01", "2024-12-31", "2025-01-01", "2025-12-31"),
    ("2021-01-01", "2025-12-31", "2026-01-01", "2026-12-31"),
]

MIN_TRAIN_YEARS = 3     # a test year needs at least this much history behind it
BENCHMARK = "SPY"       # its span defines the walkable range


def yearly_splits(store: DataStore) -> list:
    """Expanding-window splits over WHATEVER history is on disk. The
    hardcoded 2021+ list silently ignored the 20-year backfill — the
    deep data was downloaded and then never walked. Deriving the
    windows from the benchmark's actual span means more history
    automatically becomes more test windows: every year is tested
    against all years before it, exactly once."""
    bars = store.bars(BENCHMARK)
    if bars is None or bars.empty:
        return DEFAULT_SPLITS
    first = int(str(bars["trade_date"].min())[:4])
    last = int(str(bars["trade_date"].max())[:4])
    splits = [(f"{first}-01-01", f"{y - 1}-12-31",
               f"{y}-01-01", f"{y}-12-31")
              for y in range(first + MIN_TRAIN_YEARS, last + 1)]
    return splits or DEFAULT_SPLITS


def run_walkforward(store: DataStore, splits=None, setup: str = "RS-02") -> list:
    rows = []
    for train_start, train_end, test_start, test_end in (
            splits or yearly_splits(store)):
        train = run_backtest(store, start=train_start, end=train_end,
                             active=(setup,)).per_setup().get(setup)
        test = run_backtest(store, start=test_start, end=test_end,
                            active=(setup,)).per_setup().get(setup)
        rows.append({"train": (train_start, train_end, train),
                     "test": (test_start, test_end, test)})
    return rows


def summary(rows: list, setup: str = "RS-02") -> str:
    lines = [f"WALK-FORWARD — {setup} (fixed parameters, §51)", ""]
    holds = 0
    judged = 0
    for row in rows:
        for label in ("train", "test"):
            start, end, s = row[label]
            if s is None:
                lines.append(f"  {label:<5} {start[:4]}-{end[:4]}: no trades")
                continue
            lines.append(f"  {label:<5} {start[:4]}-{end[:4]}: n={s['trades']:>3} "
                         f"exp={s['expectancy_r']:+.3f}R wr={s['win_rate']:.0%} "
                         f"maxDD={s['max_drawdown_r']}R")
        test_stats = row["test"][2]
        if test_stats and test_stats["trades"] >= 10:
            judged += 1
            if test_stats["expectancy_r"] > 0:
                holds += 1
        lines.append("")
    if judged:
        lines.append(f"Verdict: edge held in {holds}/{judged} judged test windows "
                     f"(a window needs >=10 trades to count).")
    lines.append("LAW 20: only out-of-sample evidence earns production status.")
    return "\n".join(lines)


if __name__ == "__main__":
    store = DataStore(DATA_ROOT)
    if not store.tickers():
        raise SystemExit("No data. Run: python -m mve.backfill")
    from .report import save_and_print
    save_and_print("walkforward", summary(run_walkforward(store)))
