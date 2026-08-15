"""H7 — ORB + intraday-momentum studies on synthetic minute bars."""
import pandas as pd

from mve import alpaca_data
from mve.alpaca_data import IntradayStore, deep_minute_backfill
from mve.intraday_study import (FRICTION_BPS, momentum_day, opening_range,
                                orb_day, rth, run_studies, summary)

SESSION_BARS = 390          # 09:30 -> 15:59 ET, one bar per minute


def day_bars(rows, day="2025-06-02"):
    """rows of (open, high, low, close) -> one RTH session of minute bars.
    First row is 09:30 ET (13:30 UTC during EDT)."""
    base = pd.Timestamp(f"{day}T13:30:00Z")
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    df["ticker"] = "T"
    df["trade_date"] = day
    df["volume"] = 10_000
    df["ts"] = [(base + pd.Timedelta(minutes=i)).isoformat()
                for i in range(len(rows))]
    return df


def flat(n, px=100.0):
    return [[px, px + 0.3, px - 0.3, px]] * n


def pad(rows, px):
    return rows + [[px, px + 0.2, px - 0.2, px]] * (SESSION_BARS - len(rows))


# ------------------------------------------------------------------ rth
def test_rth_filters_premarket():
    day = day_bars(flat(SESSION_BARS))
    pre = day_bars(flat(1)).assign(ts="2025-06-02T13:00:00Z")   # 09:00 ET
    out = rth(pd.concat([pre, day], ignore_index=True))
    assert len(out) == SESSION_BARS
    assert out["et"].iloc[0] == "09:30" and out["et"].iloc[-1] == "15:59"


def test_opening_range():
    hi, lo, n = opening_range(rth(day_bars(flat(SESSION_BARS))), 15)
    assert n == 15 and hi == 100.3 and lo == 99.7


# ------------------------------------------------------------------ ORB
def test_orb_long_breakout_rides_to_close():
    rows = flat(15) + [[100.0, 100.7, 100.0, 100.6]]      # close > OR high
    rows.append([100.7, 100.9, 100.6, 100.8])             # entry bar, open 100.7
    rows = pad(rows, 105.0)                               # runs up, holds
    out = orb_day(day_bars(rows))
    assert out is not None and out["side"] == "long"
    assert out["reason"] == "close"
    assert out["entry"] == 100.7
    # (105 - 100.7) / (100.7 - 99.7) = 4.3R minus ~0.02R friction
    assert 4.2 < out["r"] < 4.3


def test_orb_stop_hits_at_opposite_bound():
    rows = flat(15) + [[100.0, 100.7, 100.0, 100.6]]
    rows.append([100.7, 100.8, 100.5, 100.6])             # entry bar
    rows.append([100.4, 100.5, 99.5, 99.6])               # low pierces 99.7
    out = orb_day(day_bars(pad(rows, 99.6)))
    assert out["reason"] == "stop"
    assert -1.1 < out["r"] < -1.0                          # -1R minus friction


def test_orb_gap_through_stop_fills_at_open():
    rows = flat(15) + [[100.0, 100.7, 100.0, 100.6]]
    rows.append([100.7, 100.8, 100.5, 100.6])
    rows.append([99.0, 99.2, 98.8, 99.0])                  # opens below stop
    out = orb_day(day_bars(pad(rows, 99.0)))
    assert out["reason"] == "gap_stop"
    assert out["r"] < -1.5                                 # worse than 1R


def test_orb_short_breakdown():
    rows = flat(15) + [[100.0, 100.0, 99.3, 99.4]]        # close < OR low
    rows.append([99.3, 99.4, 99.1, 99.2])                 # entry bar, open 99.3
    out = orb_day(day_bars(pad(rows, 95.0)))              # falls, holds
    assert out["side"] == "short" and out["reason"] == "close"
    # (99.3 - 95) / (100.3 - 99.3) = 4.3R minus friction
    assert 4.2 < out["r"] < 4.3


def test_orb_no_breakout_and_short_session():
    assert orb_day(day_bars(flat(SESSION_BARS))) is None   # never leaves range
    assert orb_day(day_bars(flat(50))) is None             # half day skipped


# ------------------------------------------------------------- momentum
def momentum_rows(first_end=101.0, last_end=101.5, mid=101.0):
    rows = []
    for i in range(30):                                    # 09:30 -> 09:59
        px = 100.0 + (first_end - 100.0) * (i + 1) / 30
        rows.append([px - 0.05, px + 0.1, px - 0.1, px])
    rows += [[mid, mid + 0.1, mid - 0.1, mid]] * 330       # 10:00 -> 15:29
    for i in range(30):                                    # 15:30 -> 15:59
        px = mid + (last_end - mid) * (i + 1) / 30
        rows.append([mid if i == 0 else px - 0.02, px + 0.05, px - 0.05, px])
    return rows


def test_momentum_long_signal_and_friction():
    out = momentum_day(day_bars(momentum_rows()))
    assert out["side"] == "long"
    expected = (101.5 / 101.0 - 1.0) * 1e4 - FRICTION_BPS
    assert abs(out["ret_bps"] - expected) < 1.0


def test_momentum_short_signal():
    out = momentum_day(day_bars(momentum_rows(first_end=99.0, mid=99.0,
                                              last_end=98.5)))
    assert out["side"] == "short"
    assert out["ret_bps"] > 0                              # fell as predicted


def test_momentum_skips_short_session():
    assert momentum_day(day_bars(flat(50))) is None


# ------------------------------------------- study wiring + backfill
def test_run_studies_and_summary(tmp_path):
    store = IntradayStore(str(tmp_path))
    for day in ("2025-06-02", "2025-06-03", "2025-06-04",
                "2025-06-05", "2025-06-06"):
        rows = flat(15) + [[100.0, 100.7, 100.0, 100.6]]
        rows.append([100.7, 100.9, 100.6, 100.8])
        store.ingest(day_bars(pad(rows, 105.0), day=day))
    results = run_studies(store, ["T"])
    rec = results["T"]
    assert rec["sessions"] == 5
    assert len(rec["orb"]["train"]) == 3 and len(rec["orb"]["test"]) == 2
    text = summary(results)
    assert "H7 INTRADAY STUDY" in text
    assert "INCONCLUSIVE" in text                          # n far below guards
    assert "LAW 12/20" in text


def test_deep_backfill_chunks_and_ingests(tmp_path, monkeypatch):
    calls = []

    def fake_fetch(ticker, timeframe, start, end, pause_s=0.0):
        calls.append((start, end))
        return day_bars(flat(SESSION_BARS), day="2025-06-02")

    monkeypatch.setattr(alpaca_data, "fetch_bars", fake_fetch)
    deep_minute_backfill(["T"], days=10, chunk_days=5, root=str(tmp_path))
    assert len(calls) == 2                                 # 10d in 5d chunks
    store = IntradayStore(str(tmp_path))
    assert store.days("T") == ["2025-06-02"]
    assert len(store.bars("T", "2025-06-02")) == SESSION_BARS
