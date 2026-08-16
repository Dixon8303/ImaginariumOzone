"""H7 — intraday studies on minute bars (spec §72 experiment matrix).

Two documented effects, run through the same train/test discipline that
tuned the exit policy — verdicts, not vibes:

ORB      Opening-range breakout. The first N minutes define a range;
         a 1-min close above the range high goes long (below the low,
         short) at the NEXT bar's open, stop at the opposite bound,
         exit on stop or the session close. R-multiples, conservative
         fills (gap-through-stop fills at the open).

INTRADAY Gao/Han/Li/Zhou (2018) "Market intraday momentum": the sign of
MOMENTUM the first-30-minute return predicts the last-30-minute return.
         Position held only 15:30 -> close, reported in basis points.

Both include friction (CALIBRATE, default 2 bps round-trip — SPY/QQQ
class spreads). Pre-registered split: first TRAIN_FRACTION of each
ticker's sessions is TRAIN, the rest TEST (LAW 12/20 — the winner is
picked on TRAIN and must confirm on TEST; a train-only improvement is
noise). §38 still applies: nothing here is speed-competitive — entries
are on 1-min closes, not ticks.

Run after the deep backfill:

    python -m mve.alpaca_data --minute-deep
    python -m mve.intraday_study
    python -m mve.intraday_study SPY          # one ticker
"""
from __future__ import annotations

import sys

import pandas as pd

from .alpaca_data import DATA_ROOT, DEEP_TICKERS, IntradayStore

TRAIN_FRACTION = 0.70     # pre-registered chronological split
OR_MINUTES = 15           # CALIBRATE — opening-range window
FRICTION_BPS = 2.0        # CALIBRATE — round-trip cost, index-ETF class
MIN_SESSION_BARS = 100    # skip half days / broken sessions
MIN_TRAIN_N = 40          # verdict guards (intraday n is large; be strict)
MIN_TEST_N = 20

RTH_OPEN = "09:30"
RTH_LAST = "15:59"
MOMO_FIRST_END = "10:00"   # first-30-min window is [09:30, 10:00)
MOMO_LAST_START = "15:30"  # last-30-min window is [15:30, close]


def rth(bars: pd.DataFrame) -> pd.DataFrame:
    """Regular trading hours only, sorted, with an ET clock column."""
    if bars.empty:
        return bars.assign(et=pd.Series(dtype=str))
    ts = pd.to_datetime(bars["ts"], utc=True).dt.tz_convert("America/New_York")
    out = bars.assign(et=ts.dt.strftime("%H:%M"))
    out = out[(out["et"] >= RTH_OPEN) & (out["et"] <= RTH_LAST)]
    return out.sort_values("et").reset_index(drop=True)


def opening_range(day: pd.DataFrame, minutes: int = OR_MINUTES):
    """(high, low, n_bars) of the first `minutes` of the session."""
    window = day.iloc[:minutes]
    return float(window["high"].max()), float(window["low"].min()), len(window)


def orb_day(day: pd.DataFrame, or_minutes: int = OR_MINUTES,
            friction_bps: float = FRICTION_BPS) -> dict | None:
    """One session of ORB. Returns a trade dict or None (no breakout /
    unusable session). First breakout only — one trade per day."""
    day = rth(day)
    if len(day) < MIN_SESSION_BARS:
        return None
    or_high, or_low, n = opening_range(day, or_minutes)
    if n < or_minutes or or_high <= or_low:
        return None
    rest = day.iloc[or_minutes:]
    for i in range(len(rest) - 1):          # need a next bar to enter on
        close = float(rest["close"].iloc[i])
        if close > or_high:
            side, stop = 1, or_low
        elif close < or_low:
            side, stop = -1, or_high
        else:
            continue
        entry = float(rest["open"].iloc[i + 1])
        r_denom = abs(entry - stop)
        if r_denom <= 0:
            return None
        exit_px, reason = None, "close"
        for _, bar in rest.iloc[i + 1:].iterrows():
            o, h, l = float(bar["open"]), float(bar["high"]), float(bar["low"])
            if side == 1 and o <= stop or side == -1 and o >= stop:
                exit_px, reason = o, "gap_stop"
                break
            if side == 1 and l <= stop or side == -1 and h >= stop:
                exit_px, reason = stop, "stop"
                break
        if exit_px is None:
            exit_px = float(rest["close"].iloc[-1])
        r = side * (exit_px - entry) / r_denom
        r -= (friction_bps / 1e4) * entry / r_denom
        return dict(side="long" if side == 1 else "short", entry=entry,
                    exit=exit_px, r=round(r, 4), reason=reason)
    return None


def momentum_day(day: pd.DataFrame,
                 friction_bps: float = FRICTION_BPS) -> dict | None:
    """One session of first-30 -> last-30 intraday momentum, in bps."""
    day = rth(day)
    if len(day) < MIN_SESSION_BARS:
        return None
    first = day[day["et"] < MOMO_FIRST_END]
    last = day[day["et"] >= MOMO_LAST_START]
    if first.empty or last.empty:
        return None
    r_first = float(first["close"].iloc[-1]) / float(first["open"].iloc[0]) - 1.0
    if r_first == 0.0:
        return None
    side = 1 if r_first > 0 else -1
    entry = float(last["open"].iloc[0])
    exit_px = float(last["close"].iloc[-1])
    bps = side * (exit_px / entry - 1.0) * 1e4 - friction_bps
    return dict(side="long" if side == 1 else "short",
                signal_bps=round(r_first * 1e4, 1), ret_bps=round(bps, 2))


def run_studies(store: IntradayStore, tickers) -> dict:
    out = {}
    for t in tickers:
        days = store.days(t)
        cut = int(len(days) * TRAIN_FRACTION)
        rec = {"sessions": len(days),
               "orb": {"train": [], "test": []},
               "momentum": {"train": [], "test": []}}
        for j, day in enumerate(days):
            window = "train" if j < cut else "test"
            bars = store.bars(t, day)
            trade = orb_day(bars)
            if trade:
                rec["orb"][window].append(trade["r"])
            m = momentum_day(bars)
            if m:
                rec["momentum"][window].append(m["ret_bps"])
        out[t] = rec
    return out


def _verdict(train: list, test: list, unit: str) -> str:
    if len(train) < MIN_TRAIN_N or len(test) < MIN_TEST_N:
        return "INCONCLUSIVE (insufficient sessions)"
    et, es = sum(train) / len(train), sum(test) / len(test)
    if et <= 0:
        return f"REJECT (train {et:+.3f}{unit} not positive)"
    if es <= 0:
        return f"NOISE (train {et:+.3f}{unit}, test {es:+.3f}{unit} did not confirm)"
    return f"CANDIDATE (train {et:+.3f}{unit}, test {es:+.3f}{unit})"


def summary(results: dict) -> str:
    lines = ["H7 INTRADAY STUDY — ORB + first-30/last-30 momentum",
             f"split: first {TRAIN_FRACTION:.0%} of sessions = TRAIN | "
             f"friction {FRICTION_BPS} bps | OR window {OR_MINUTES} min", ""]

    def stats(vals):
        if not vals:
            return "n=  0"
        exp = sum(vals) / len(vals)
        wr = sum(1 for v in vals if v > 0) / len(vals)
        return f"n={len(vals):>4} exp={exp:+8.3f} wr={wr:.0%}"

    for t, rec in results.items():
        lines.append(f"{t} — {rec['sessions']} sessions")
        for study, unit in (("orb", "R"), ("momentum", "bps")):
            tr, te = rec[study]["train"], rec[study]["test"]
            lines.append(f"  {study:<9} ({unit:>3})  train: {stats(tr)}   "
                         f"test: {stats(te)}")
            lines.append(f"            verdict: {_verdict(tr, te, unit)}")
        lines.append("")
    lines += ["A CANDIDATE is not an adoption — it earns a walk-forward pass",
              "and an operator decision first (LAW 12/20). Friction here is a",
              "constant; live spreads/slippage can only be worse (§38)."]
    return "\n".join(lines)


if __name__ == "__main__":
    store = IntradayStore(DATA_ROOT)
    tickers = sys.argv[1:] or [t for t in DEEP_TICKERS if store.days(t)]
    if not tickers or not any(store.days(t) for t in tickers):
        raise SystemExit(
            "No minute data. Run: python -m mve.alpaca_data --minute-deep")
    from .report import save_and_print
    save_and_print("intraday_study", summary(run_studies(store, tickers)))
