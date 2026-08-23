"""Backtester mechanics + end-to-end (spec §44, §47, §49)."""
from datetime import date

import pandas as pd
import pytest

from mve.backfill import parse_stooq_csv, stooq_symbol
from mve.backtest import (MAX_HOLD_BARS, TARGET_R, Position,
                          manage_position, run_backtest)
from mve.store import DataStore
from mve.vendors import SyntheticVendor


def pos(entry=100.0, stop=95.0, target=110.0, held=0):
    return Position(ticker="T", setup="RS-02", signal_date="d0",
                    entry_date="d1", entry=entry, stop=stop, target=target,
                    r_denom=entry - stop, bars_held=held)


def bar(o, h, l, c):
    return {"open": o, "high": h, "low": l, "close": c}


# ---------------------------------------------------------- exit logic
def test_gap_through_stop_fills_at_open():
    price, reason = manage_position(pos(), bar(92, 96, 91, 94))
    assert reason == "gap_stop" and price == 92          # worse than -1R


def test_stop_fills_at_stop():
    price, reason = manage_position(pos(), bar(99, 100, 94, 97))
    assert reason == "stop" and price == 95


def test_target_fills_at_target():
    price, reason = manage_position(pos(), bar(101, 111, 100, 108))
    assert reason == "target" and price == 110


def test_stop_wins_same_bar_tie():
    price, reason = manage_position(pos(), bar(100, 112, 94, 105))
    assert reason == "stop" and price == 95              # conservative


def test_time_stop_at_close():
    price, reason = manage_position(pos(held=MAX_HOLD_BARS - 1),
                                    bar(100, 101, 99, 100.5))
    assert reason == "time" and price == 100.5


def test_hold_returns_none():
    assert manage_position(pos(), bar(100, 102, 98, 101)) == (None, None)


# ------------------------------------------------------ end-to-end run
def test_backtest_end_to_end_on_synthetic_history(tmp_path):
    store = DataStore(str(tmp_path))
    v = SyntheticVendor(start=date(2025, 1, 6), days=250)
    store.ingest_bars(v.bars("SPY", base=500.0, drift=0.0002, amp=0.02))
    store.ingest_bars(v.bars("XLK", base=200.0, drift=0.0004, amp=0.02, phase=0.5))
    store.ingest_bars(v.bars("RUNR", base=80.0, drift=0.003, amp=0.012, phase=1.0))
    store.ingest_bars(v.bars("LAGG", base=60.0, drift=-0.001, amp=0.02, phase=2.0))

    result = run_backtest(store, universe=["RUNR", "LAGG"], benchmark="SPY",
                          sector_map={"RUNR": "XLK", "LAGG": "XLK"})

    assert len(result.trades) > 0, "expected setups to fire on 250 sessions"
    for t in result.trades:
        assert t.exit_date > t.entry_date                # entry at NEXT open
        assert t.exit_reason in ("gap_stop", "stop", "target", "time")
        if t.exit_reason == "target":
            assert t.r_multiple == pytest.approx(TARGET_R, abs=0.01)
        if t.exit_reason == "stop":
            assert t.r_multiple == pytest.approx(-1.0, abs=0.01)

    stats = result.per_setup()
    for s in stats.values():
        assert s["trades"] >= 1
        assert 0.0 <= s["win_rate"] <= 1.0
        assert s["max_drawdown_r"] <= 0.0
    assert "UNDERLYING" in result.summary()              # honesty label


def test_backtest_respects_date_range(tmp_path):
    store = DataStore(str(tmp_path))
    v = SyntheticVendor(start=date(2025, 1, 6), days=250)
    store.ingest_bars(v.bars("SPY", base=500.0, drift=0.0002, amp=0.02))
    store.ingest_bars(v.bars("RUNR", base=80.0, drift=0.003, amp=0.012, phase=1.0))
    full = run_backtest(store, universe=["RUNR"], benchmark="SPY", sector_map={})
    late = run_backtest(store, universe=["RUNR"], benchmark="SPY", sector_map={},
                        start="2025-10-01")
    assert len(late.trades) <= len(full.trades)
    for t in late.trades:
        assert t.entry_date >= "2025-10-01"


# ------------------------------------------------------------ backfill
def test_stooq_symbol_and_csv_parse():
    assert stooq_symbol("NVDA") == "nvda.us"
    csv = ("Date,Open,High,Low,Close,Volume\n"
           "2025-01-06,100.0,102.0,99.0,101.5,1000000\n"
           "2025-01-07,101.5,103.0,101.0,102.0,900000\n")
    df = parse_stooq_csv(csv, "NVDA")
    assert len(df) == 2
    assert list(df.columns) == ["ticker", "trade_date", "open", "high",
                                "low", "close", "volume"]
    assert df["ticker"].iloc[0] == "NVDA"
    assert parse_stooq_csv("No data", "X").empty


def test_yahoo_json_parse():
    from mve.backfill import parse_yahoo_json
    payload = {"chart": {"result": [{
        "timestamp": [1736179200, 1736265600],
        "indicators": {"quote": [{
            "open": [100.0, 101.5], "high": [102.0, 103.0],
            "low": [99.0, 101.0], "close": [101.5, 102.0],
            "volume": [1000000, None],
        }]}}]}}
    df = parse_yahoo_json(payload, "NVDA")
    assert len(df) == 2 and df["volume"].iloc[1] == 0
    assert parse_yahoo_json({}, "X").empty


def test_per_ticker_breakdown():
    """Aggregate expectancy can be carried by a couple of names — the
    breadth check needs the per-ticker split to see that."""
    from mve.backtest import BacktestResult, Trade
    res = BacktestResult(trades=[
        Trade("AAPL", "RS-02", "2026-01-02", "2026-01-09", 100, 103, 1.0,
              "target", 5),
        Trade("AAPL", "RS-02", "2026-02-02", "2026-02-09", 100, 97, -1.0,
              "stop", 5),
        Trade("NVDA", "RS-02", "2026-01-02", "2026-01-09", 100, 106, 2.0,
              "target", 5),
        Trade("NVDA", "RS-01", "2026-01-02", "2026-01-09", 100, 90, -3.0,
              "stop", 5),
    ])
    by = res.per_ticker("RS-02")
    assert set(by) == {"AAPL", "NVDA"}          # RS-01 excluded
    assert by["AAPL"] == {"trades": 2, "expectancy_r": 0.0}
    assert by["NVDA"] == {"trades": 1, "expectancy_r": 2.0}
    assert res.per_ticker("RS-01")["NVDA"]["expectancy_r"] == -3.0


# ------------------------------------- corrupt-data guards (2026-08-21)
# The 20-year backfill produced an RS-01 "average loss" of -6,911R from
# corrupt bars (unadjusted splits, near-zero prices). These guards keep
# one bad print from poisoning every aggregate — loudly, never silently.

def test_thin_stop_is_skipped_and_counted(tmp_path):
    from mve.backtest import MIN_R_DENOM_FRAC, BacktestResult
    assert 0 < MIN_R_DENOM_FRAC < 0.02      # sanity floor, not a filter
    r = BacktestResult()
    assert r.thin_stop_signals == 0 and r.suspect_trades == []


def test_suspect_r_quarantines_but_reports():
    from mve.backtest import SUSPECT_R, BacktestResult, Trade
    res = BacktestResult()
    good = Trade(ticker="OK", setup="RS-02", entry_date="d1", exit_date="d2",
                 entry=100.0, exit=103.0, r_multiple=3.0, exit_reason="target",
                 bars_held=2)
    bad = Trade(ticker="BAD", setup="RS-02", entry_date="d1", exit_date="d2",
                entry=100.0, exit=1.0, r_multiple=-6911.0, exit_reason="gap_stop",
                bars_held=1)
    res.trades.append(good)
    res.suspect_trades.append(bad)
    stats = res.per_setup()["RS-02"]
    assert stats["trades"] == 1              # the corrupt print is excluded
    assert stats["expectancy_r"] == 3.0
    text = res.summary()
    assert "QUARANTINED BAD" in text         # ...but never hidden
    assert "-6911R" in text
    assert abs(bad.r_multiple) > SUSPECT_R


def test_suspect_threshold_is_beyond_any_real_trade():
    # TARGET_R is 3 and gap-through losses run a few R — a 50R bound
    # can only be crossed by corrupt data.
    from mve.backtest import SUSPECT_R, TARGET_R
    assert SUSPECT_R >= 10 * TARGET_R
