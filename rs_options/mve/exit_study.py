"""Exit-policy study for RS-02 (spec §41-§42 MAE/MFE research).

Motivation from the first real backtest: 119/160 RS-02 exits were TIME
exits averaging +0.33R — the fixed +2R target rarely got hit, suggesting
the exit leaves money on the table. This study replays every historical
RS-02 signal and evaluates alternative exit policies on the SAME paths,
reporting train (<= 2024) and test (>= 2025) windows separately so the
winner is judged out-of-sample, not picked by hindsight.

Policies (all CALIBRATE):
  baseline   stop at invalidation, +2R target, 10-bar time exit
  wide       stop at invalidation, +3R target, 15-bar time exit
  atr_trail  no fixed target; stop ratchets to close - 2*ATR(14); 20-bar cap
  breakeven  baseline + stop moves to entry once +1R trades

    python -m mve.exit_study
"""
from __future__ import annotations

import sys

import pandas as pd

from .backtest import DATA_ROOT
from .rs_features import compute_features
from .setups import detect_all
from .store import DataStore
from .universe import BENCHMARK, SECTOR_ETF, UNIVERSE

TRAIN_END = "2024-12-31"
ATR_LEN = 14
MIN_HISTORY = 60

POLICIES = {
    "baseline": dict(target_r=2.0, max_hold=10, atr_trail=None, breakeven_at=None),
    "wide": dict(target_r=3.0, max_hold=15, atr_trail=None, breakeven_at=None),
    "atr_trail": dict(target_r=None, max_hold=20, atr_trail=2.0, breakeven_at=None),
    "breakeven": dict(target_r=2.0, max_hold=10, atr_trail=None, breakeven_at=1.0),
    # H3 — anchored VWAP from the entry day as a trailing floor (§2.1 of
    # MARKET_THEORY: institutional cost basis of the breakout). DAILY-BAR
    # APPROXIMATION (typical price x volume); minute-precision AVWAP comes
    # when enough intraday history accumulates. Grace bars let the level
    # establish before it can stop the trade out.
    "avwap_trail": dict(target_r=None, max_hold=20, atr_trail=None,
                        breakeven_at=None, avwap=True, avwap_grace=3),
}


def atr(bars: pd.DataFrame, length: int = ATR_LEN) -> float:
    h, l, c = bars["high"], bars["low"], bars["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()],
                   axis=1).max(axis=1)
    return float(tr.rolling(length).mean().iloc[-1])


def simulate(path: pd.DataFrame, entry: float, stop0: float, r_denom: float,
             entry_atr: float, policy: dict) -> dict:
    """Replay one signal's forward path under one exit policy.
    Same conservative rules as the backtester: gap-through-stop fills at
    the open; stop beats target on the same bar."""
    stop = stop0
    target = (entry + policy["target_r"] * r_denom
              if policy["target_r"] else None)
    mfe = mae = 0.0
    cum_pv = cum_v = 0.0            # anchored-VWAP accumulators (H3)
    for i, (_, bar) in enumerate(path.iterrows(), start=1):
        mfe = max(mfe, (bar["high"] - entry) / r_denom)
        mae = min(mae, (bar["low"] - entry) / r_denom)
        if bar["open"] <= stop:
            return dict(r=(bar["open"] - entry) / r_denom, reason="gap_stop",
                        bars=i, mfe=mfe, mae=mae)
        if bar["low"] <= stop:
            return dict(r=(stop - entry) / r_denom, reason="stop",
                        bars=i, mfe=mfe, mae=mae)
        if target and bar["high"] >= target:
            return dict(r=policy["target_r"], reason="target",
                        bars=i, mfe=mfe, mae=mae)
        # end-of-bar stop ratchets (never loosen)
        if policy["breakeven_at"] and (bar["high"] - entry) / r_denom >= policy["breakeven_at"]:
            stop = max(stop, entry)
        if policy["atr_trail"]:
            stop = max(stop, float(bar["close"]) - policy["atr_trail"] * entry_atr)
        if policy.get("avwap"):
            typical = (float(bar["high"]) + float(bar["low"])
                       + float(bar["close"])) / 3.0
            vol = float(bar.get("volume", 0.0) or 1.0)
            cum_pv += typical * vol
            cum_v += vol
            if cum_v > 0 and i >= policy.get("avwap_grace", 3):
                stop = max(stop, cum_pv / cum_v)
        if i >= policy["max_hold"]:
            return dict(r=(float(bar["close"]) - entry) / r_denom, reason="time",
                        bars=i, mfe=mfe, mae=mae)
    last = float(path["close"].iloc[-1])
    return dict(r=(last - entry) / r_denom, reason="end_of_data",
                bars=len(path), mfe=mfe, mae=mae)


def collect_signals(store: DataStore, setup: str = "RS-02") -> list:
    """Point-in-time signal replay (same discipline as the backtester)."""
    universe = [t for t in UNIVERSE if t != BENCHMARK]
    all_bars = {t: store.bars(t) for t in
                set(universe) | {BENCHMARK} | set(SECTOR_ETF.values())}
    bench = all_bars[BENCHMARK]
    signals = []
    for ticker in universe:
        df = all_bars.get(ticker)
        if df is None or len(df) < MIN_HISTORY:
            continue
        last_exit_idx = -1
        for i in range(MIN_HISTORY, len(df) - 1):
            if i <= last_exit_idx:
                continue                      # one position at a time
            d = df["trade_date"].iloc[i]
            bars = df.iloc[: i + 1]
            bench_slice = bench[bench["trade_date"] <= d]
            if len(bench_slice) < MIN_HISTORY:
                continue
            sector_t = SECTOR_ETF.get(ticker)
            sector = (all_bars[sector_t][all_bars[sector_t]["trade_date"] <= d]
                      if sector_t in all_bars else None)
            hits = detect_all(bars, compute_features(bars, bench_slice, sector),
                              active=(setup,))
            if not hits:
                continue
            hit = hits[0]
            entry = float(df["open"].iloc[i + 1])
            r_denom = entry - hit["invalidation_price"]
            if r_denom <= 0:
                continue
            signals.append(dict(
                ticker=ticker, date=d, entry=entry,
                stop=hit["invalidation_price"], r_denom=r_denom,
                entry_atr=atr(bars), path=df.iloc[i + 1:i + 26],
            ))
            last_exit_idx = i + 25            # coarse spacing guard
    return signals


def run_study(store: DataStore) -> dict:
    signals = collect_signals(store)
    results: dict = {name: {"train": [], "test": []} for name in POLICIES}
    for sig in signals:
        window = "train" if sig["date"] <= TRAIN_END else "test"
        for name, policy in POLICIES.items():
            out = simulate(sig["path"], sig["entry"], sig["stop"],
                           sig["r_denom"], sig["entry_atr"], policy)
            results[name][window].append(out)
    return {"signals": len(signals), "results": results}


def summary(study: dict) -> str:
    lines = [f"EXIT-POLICY STUDY — RS-02, {study['signals']} signals "
             f"(train <= {TRAIN_END}, test after)", ""]
    for name, windows in study["results"].items():
        parts = [f"{name:<10}"]
        for label in ("train", "test"):
            rs = [o["r"] for o in windows[label]]
            if rs:
                exp = sum(rs) / len(rs)
                wr = sum(1 for r in rs if r > 0) / len(rs)
                parts.append(f"{label}: n={len(rs):>3} exp={exp:+.3f}R wr={wr:.0%}")
            else:
                parts.append(f"{label}: no signals")
        lines.append("   ".join(parts))
    all_train = study["results"]["baseline"]["train"]
    if all_train:
        mfe = sum(o["mfe"] for o in all_train) / len(all_train)
        mae = sum(o["mae"] for o in all_train) / len(all_train)
        lines += ["", f"Path shape (train, baseline horizon): avg MFE {mfe:+.2f}R, "
                      f"avg MAE {mae:+.2f}R — how far winners run vs how deep "
                      f"trades sink before resolving (§42)."]
    lines += ["", "Pick the winner on TRAIN, confirm on TEST. If they disagree,",
              "the improvement is noise — keep the baseline (LAW 12/20)."]
    return "\n".join(lines)


if __name__ == "__main__":
    store = DataStore(DATA_ROOT)
    if not store.tickers():
        raise SystemExit("No data. Run: python -m mve.backfill")
    from .report import save_and_print
    save_and_print("exit_study", summary(run_study(store)))
