"""H1/H2 entry filters + H3 anchored-VWAP policy (spec §72)."""
from datetime import date

import pandas as pd
import pytest

from mve.backtest import run_backtest
from mve.exit_study import POLICIES, simulate
from mve.hypotheses import (VARIANTS, above_sma, calm_breakout, mom_12_1,
                            near_52wk_high, quality_mom, run_hypotheses,
                            summary)
from mve.store import DataStore
from mve.vendors import SyntheticVendor


def bars_from_closes(closes, volume=1_000_000):
    n = len(closes)
    return pd.DataFrame({
        "ticker": "T",
        "trade_date": pd.bdate_range("2024-01-02", periods=n).date.astype(str),
        "open": closes, "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes], "close": closes,
        "volume": [volume] * n,
    })


# ---------------------------------------------------------- H1 filter
def test_near_52wk_high_true_at_breakout():
    bars = bars_from_closes([100 + 0.1 * i for i in range(60)])
    assert near_52wk_high(bars, 0.05)          # rising series ends at high


def test_near_52wk_high_false_deep_below():
    closes = [100 + 0.5 * i for i in range(50)] + [80.0] * 10
    assert not near_52wk_high(bars_from_closes(closes), 0.05)
    assert not near_52wk_high(bars_from_closes(closes), 0.10)


# ---------------------------------------------------------- H2 filter
def test_above_sma_regime():
    up = bars_from_closes([100 + 0.1 * i for i in range(220)])
    assert above_sma(up, 200)
    down = bars_from_closes([300 - 0.5 * i for i in range(220)])
    assert not above_sma(down, 200)


def test_above_sma_fails_closed_without_history():
    assert not above_sma(bars_from_closes([100.0] * 50), 200)


# --------------------------------------------------- backtest wiring
@pytest.fixture
def seeded(tmp_path):
    store = DataStore(str(tmp_path))
    v = SyntheticVendor(start=date(2023, 1, 2), days=500)
    store.ingest_bars(v.bars("SPY", base=500.0, drift=0.0002, amp=0.02))
    store.ingest_bars(v.bars("RUNR", base=80.0, drift=0.003, amp=0.012, phase=1.0))
    return store


def test_entry_filter_blocks_and_counts(seeded):
    control = run_backtest(seeded, universe=["RUNR"], benchmark="SPY",
                           sector_map={})
    blocked = run_backtest(seeded, universe=["RUNR"], benchmark="SPY",
                           sector_map={},
                           entry_filter=lambda t, b, s: False)
    assert len(blocked.trades) == 0
    assert blocked.filtered_signals > 0        # no silent caps
    passthrough = run_backtest(seeded, universe=["RUNR"], benchmark="SPY",
                               sector_map={},
                               entry_filter=lambda t, b, s: True)
    assert len(passthrough.trades) == len(control.trades)


def test_hypothesis_study_structure(seeded):
    results = run_hypotheses(seeded)
    assert set(results) == set(VARIANTS)
    text = summary(results)
    assert "CONTROL" in text and "BASELINE_H2b" in text
    assert "H4a_mom_pos" in text and "H6a_no_spike_5pct" in text
    assert "LAW 12/20" in text


# ------------------------------------------------- H4 quality momentum
def test_mom_12_1_sign_and_fail_closed():
    up = bars_from_closes([100 * 1.002 ** i for i in range(300)])
    assert mom_12_1(up) > 0 and quality_mom(up)
    down = bars_from_closes([300 * 0.998 ** i for i in range(300)])
    assert mom_12_1(down) < 0 and not quality_mom(down)
    assert mom_12_1(bars_from_closes([100.0] * 100)) is None
    assert not quality_mom(bars_from_closes([100.0] * 100))   # fail-closed


def test_quality_mom_threshold():
    modest = bars_from_closes([100 + 0.02 * i for i in range(300)])
    assert quality_mom(modest, 0.0)               # positive drift
    assert not quality_mom(modest)                # ~+5% < adopted 10% default
    assert not quality_mom(modest, 0.50)          # and not +50%


# --------------------------------------------------- H6 spike guard
def test_calm_breakout_blocks_spike_day():
    calm = bars_from_closes([100.0] * 59 + [102.0])       # +2% day
    spike = bars_from_closes([100.0] * 59 + [109.0])      # +9% day
    assert calm_breakout(calm, 0.05)
    assert not calm_breakout(spike, 0.05)
    assert not calm_breakout(spike, 0.08)
    assert not calm_breakout(bars_from_closes([100.0]), 0.05)  # fail-closed


# ------------------------------------------------- H3 avwap policy
BASE = dict(entry=100.0, stop0=95.0, r_denom=5.0, entry_atr=2.0)


def path(rows):
    return pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"])


def test_avwap_trail_ratchets_and_locks_gains():
    # Run up for 4 bars (AVWAP rises with price), then close crashes below
    # the anchored VWAP -> exit above entry via the ratcheted floor.
    rows = [[101, 104, 100, 104, 1e6], [105, 108, 104, 108, 1e6],
            [109, 112, 108, 112, 1e6], [112, 114, 111, 113, 1e6],
            [113, 113, 101, 101, 1e6]]
    out = simulate(path(rows), **BASE, policy=POLICIES["avwap_trail"])
    assert out["reason"] in ("stop", "gap_stop")
    assert out["r"] > 0                        # exited well above entry


def test_avwap_grace_period_defers_the_floor():
    # Bar-2 dip to 99 sits BELOW the running AVWAP (~101.7) — inside the
    # grace window that must not stop the trade. The rising tail keeps
    # price above the ratcheting floor afterwards -> survives to time cap.
    rows = [[101, 103, 100, 102, 1e6], [101, 102, 99, 100, 1e6],
            [100, 103, 99, 102, 1e6]]
    px = 102.0
    for _ in range(17):
        px += 2.0
        rows.append([px - 1, px + 1, px - 1.5, px, 1e6])
    out = simulate(path(rows), **BASE, policy=POLICIES["avwap_trail"])
    assert out["reason"] == "time"             # survived to the 20-bar cap
    assert out["r"] > 0


def test_avwap_handles_missing_volume_column():
    rows = pd.DataFrame([[101, 111, 100, 108]] * 20,
                        columns=["open", "high", "low", "close"])
    out = simulate(rows, **BASE, policy=POLICIES["avwap_trail"])
    assert out["reason"] in ("stop", "gap_stop", "time")   # no crash
