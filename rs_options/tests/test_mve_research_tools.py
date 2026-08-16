"""Alpaca fetcher parsing, walk-forward, exit-policy study (spec §41-§42, §51)."""
import os
from datetime import date

import pandas as pd
import pytest

from mve.alpaca_data import IntradayStore, parse_alpaca_bars
from mve.exit_study import POLICIES, run_study, simulate, summary as exit_summary
from mve.store import DataStore
from mve.vendors import SyntheticVendor
from mve.walkforward import run_walkforward, summary as wf_summary


# ------------------------------------------------------------- alpaca
def test_parse_alpaca_bars_daily_and_intraday():
    payload = {"bars": [
        {"t": "2026-08-13T13:30:00Z", "o": 100.0, "h": 101.0, "l": 99.5,
         "c": 100.5, "v": 12345},
        {"t": "2026-08-13T13:31:00Z", "o": 100.5, "h": 100.8, "l": 100.2,
         "c": 100.6, "v": 2345},
    ]}
    daily = parse_alpaca_bars(payload, "NVDA")
    assert len(daily) == 2 and "ts" not in daily.columns
    assert daily["trade_date"].iloc[0] == "2026-08-13"   # NY session date
    intraday = parse_alpaca_bars(payload, "NVDA", intraday=True)
    assert "ts" in intraday.columns
    assert parse_alpaca_bars({"bars": None}, "X").empty


def test_intraday_store_roundtrip_idempotent(tmp_path):
    store = IntradayStore(str(tmp_path))
    payload = {"bars": [{"t": f"2026-08-13T13:{m:02d}:00Z", "o": 1.0, "h": 1.1,
                         "l": 0.9, "c": 1.05, "v": 10} for m in range(30, 35)]}
    df = parse_alpaca_bars(payload, "NVDA", intraday=True)
    store.ingest(df)
    store.ingest(df)                                     # idempotent
    out = store.bars("NVDA", "2026-08-13")
    assert len(out) == 5
    assert store.days("NVDA") == ["2026-08-13"]
    assert store.bars("NVDA", "2026-08-14").empty


# ------------------------------------------------------- exit simulate
def _path(rows):
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"])


BASE = dict(entry=100.0, stop0=95.0, r_denom=5.0, entry_atr=2.0)


def test_simulate_baseline_target():
    path = _path([[101, 111, 100, 108]])
    out = simulate(path, **BASE, policy=POLICIES["baseline"])
    assert out["reason"] == "target" and out["r"] == 2.0
    assert out["mfe"] >= 2.0


def test_simulate_stop_beats_target_same_bar():
    path = _path([[100, 112, 94, 105]])
    out = simulate(path, **BASE, policy=POLICIES["baseline"])
    assert out["reason"] == "stop" and out["r"] == pytest.approx(-1.0)


def test_simulate_breakeven_ratchet_protects():
    # Bar 1 reaches +1R (105) -> stop moves to entry; bar 2 dips to 99.
    path = _path([[101, 105.5, 100.5, 105], [104, 106, 99, 100]])
    out = simulate(path, **BASE, policy=POLICIES["breakeven"])
    assert out["reason"] == "stop" and out["r"] == pytest.approx(0.0)

    base = simulate(path, **BASE, policy=POLICIES["baseline"])
    assert base["reason"] != "stop"          # baseline would still be holding


def test_simulate_atr_trail_ratchets_up():
    # Strong run then pullback: trail (close - 2*ATR) should lock in gains.
    path = _path([[101, 106, 100, 106], [107, 112, 106, 112],
                  [112, 113, 104, 105]])
    out = simulate(path, **BASE, policy=POLICIES["atr_trail"])
    assert out["reason"] in ("stop", "gap_stop")
    assert out["r"] > 0                      # exited above entry via trail


def test_simulate_time_exit():
    rows = [[100, 101, 99.5, 100.6]] * 12
    out = simulate(_path(rows), **BASE, policy=POLICIES["baseline"])
    assert out["reason"] == "time" and out["bars"] == 10


# ------------------------------------------- studies on synthetic data
@pytest.fixture
def seeded(tmp_path):
    store = DataStore(str(tmp_path))
    v = SyntheticVendor(start=date(2023, 1, 2), days=700)
    store.ingest_bars(v.bars("SPY", base=500.0, drift=0.0002, amp=0.02))
    store.ingest_bars(v.bars("NVDA", base=80.0, drift=0.003, amp=0.012, phase=1.0))
    return store


def test_walkforward_report_structure(seeded):
    splits = [("2023-01-01", "2024-06-30", "2024-07-01", "2025-12-31")]
    rows = run_walkforward(seeded, splits=splits)
    assert len(rows) == 1
    text = wf_summary(rows)
    assert "WALK-FORWARD" in text and "LAW 20" in text


def _custom_bars(ticker, closes, volumes, start="2024-06-03"):
    dates = pd.bdate_range(start, periods=len(closes)).date.astype(str)
    return pd.DataFrame({
        "ticker": ticker, "trade_date": dates,
        "open": closes, "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes], "close": closes,
        "volume": volumes,
    })


@pytest.fixture
def breakout_store(tmp_path):
    """A series engineered so RS-02 fires: steady uptrend, then a clean
    breakout bar with a volume spike, with plenty of path afterwards."""
    store = DataStore(str(tmp_path))
    n = 130
    closes, vols = [], []
    price = 100.0
    for i in range(n):
        price += 0.3
        if i == 80:
            price += 5.0                       # breakout above the 20d high
        closes.append(round(price, 2))
        vols.append(2_000_000 if i == 80 else 1_000_000)
    store.ingest_bars(_custom_bars("NVDA", closes, vols))
    store.ingest_bars(_custom_bars(
        "SPY", [500 + 0.05 * i for i in range(n)], [1_000_000] * n))
    return store


def test_exit_study_runs_all_policies(breakout_store):
    study = run_study(breakout_store)
    assert study["signals"] > 0
    for name in POLICIES:
        outs = study["results"][name]["train"] + study["results"][name]["test"]
        assert len(outs) == study["signals"]
        for o in outs:
            assert o["mfe"] >= 0 >= o["mae"]
    text = exit_summary(study)
    assert "EXIT-POLICY STUDY" in text and "baseline" in text


# ------------------------------------------------------------- reports
def test_save_report_writes_committable_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    from mve.report import save_and_print, save_report
    path = save_report("demo_study", "LINE 1\nLINE 2\n")
    assert path == os.path.join("docs", "reports", "demo_study.txt")
    text = open(path).read()
    assert text.startswith("generated: ") and "LINE 2" in text
    save_report("demo_study", "OVERWRITTEN")          # idempotent overwrite
    assert "OVERWRITTEN" in open(path).read()
    save_and_print("demo_study", "SUMMARY BODY")
    out = capsys.readouterr().out
    assert "SUMMARY BODY" in out and "git add docs/reports" in out
