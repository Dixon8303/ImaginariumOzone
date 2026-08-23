"""H21 robustness — cost model, Sharpe, bootstrap, and their caveats."""
from datetime import date

import pytest

from mve.backtest import run_backtest
from mve.robustness import (bootstrap, break_even_bps, run_robustness,
                            sharpe, summary)
from mve.store import DataStore
from mve.vendors import SyntheticVendor


# ---------------------------------------------------------- cost model
@pytest.fixture
def seeded(tmp_path):
    store = DataStore(str(tmp_path))
    v = SyntheticVendor(start=date(2023, 1, 2), days=500)
    store.ingest_bars(v.bars("SPY", base=500.0, drift=0.0002, amp=0.02))
    store.ingest_bars(v.bars("RUNR", base=80.0, drift=0.003, amp=0.012,
                             phase=1.0))
    return store


def test_costs_default_to_zero_so_old_verdicts_stay_comparable(seeded):
    """Charging costs by default would silently invalidate every number
    in the research log."""
    free = run_backtest(seeded, universe=["RUNR"], benchmark="SPY",
                        sector_map={})
    explicit = run_backtest(seeded, universe=["RUNR"], benchmark="SPY",
                            sector_map={}, cost_bps=0.0)
    assert [t.r_multiple for t in free.trades] == \
           [t.r_multiple for t in explicit.trades]


def test_costs_reduce_expectancy_monotonically(seeded):
    """More cost is never better. A cost model that can improve a result
    is charging it in the wrong direction."""
    prev = None
    for bps in (0.0, 10.0, 50.0, 200.0):
        res = run_backtest(seeded, universe=["RUNR"], benchmark="SPY",
                           sector_map={}, cost_bps=bps)
        s = res.per_setup().get("RS-02")
        if s is None:
            continue
        if prev is not None:
            assert s["expectancy_r"] <= prev + 1e-9
        prev = s["expectancy_r"]


def test_entry_cost_widens_risk_not_just_price(seeded):
    """Paying up at the open means MORE risk to the same stop, not just
    a worse price — the R denominator must move too."""
    free = run_backtest(seeded, universe=["RUNR"], benchmark="SPY",
                        sector_map={})
    dear = run_backtest(seeded, universe=["RUNR"], benchmark="SPY",
                        sector_map={}, cost_bps=100.0)
    if free.trades and dear.trades:
        assert dear.trades[0].entry > free.trades[0].entry


# -------------------------------------------------------------- Sharpe
def test_sharpe_scales_with_frequency_and_handles_degenerate_input():
    rs = [1.0, -0.5, 0.8, -1.0, 1.2, -0.4, 0.6, -0.9, 1.1, -0.3]
    s25 = sharpe(rs, 25.0)
    s100 = sharpe(rs, 100.0)
    assert s25 is not None and s100 is not None
    assert s100 == pytest.approx(s25 * 2.0, rel=1e-6)   # sqrt(4x) = 2x
    assert sharpe([1.0], 25.0) is None                  # n < 2
    assert sharpe([0.5] * 10, 25.0) is None             # zero variance
    assert sharpe(rs, 0.0) is None                      # no frequency


def test_sharpe_is_scale_invariant_in_risk_per_trade():
    """R doubles if you risk twice as much; Sharpe must not move, which
    is why the R-series Sharpe equals the account-return Sharpe."""
    rs = [1.0, -0.5, 0.8, -1.0, 1.2]
    assert sharpe([2 * r for r in rs], 25.0) == pytest.approx(
        sharpe(rs, 25.0), rel=1e-9)


# ----------------------------------------------------------- bootstrap
def test_bootstrap_is_deterministic_and_brackets_the_median():
    rs = [1.0, -0.5, 0.8, -1.0, 1.2, -0.4, 0.6, -0.9, 1.1, -0.3] * 4
    a = bootstrap(rs, iterations=300, seed=7)
    b = bootstrap(rs, iterations=300, seed=7)
    assert a == b                                   # reproducible
    assert a["total_p05"] <= a["total_p50"] <= a["total_p95"]
    assert a["dd_p05"] <= a["dd_p50"] <= 0          # drawdowns are negative
    assert 0.0 <= a["losing_paths"] <= 1.0


def test_bootstrap_declines_to_speak_on_tiny_samples():
    assert bootstrap([1.0, -1.0, 0.5], iterations=100) == {}


def test_break_even_finds_the_zero_crossing():
    rows = [{"cost_bps": 0.0, "expectancy_r": 0.10},
            {"cost_bps": 10.0, "expectancy_r": 0.05},
            {"cost_bps": 20.0, "expectancy_r": -0.05}]
    assert break_even_bps(rows) == pytest.approx(15.0, abs=0.1)
    rising = [{"cost_bps": 0.0, "expectancy_r": 0.10},
              {"cost_bps": 10.0, "expectancy_r": 0.09}]
    assert break_even_bps(rising) is None           # never crosses


# -------------------------------------------------------------- report
def test_summary_carries_the_bootstrap_caveat():
    """A bootstrap drawdown read as the worst case is worse than no
    bootstrap at all — the caveat must travel with the number."""
    r = {"costs": [{"cost_bps": 0.0, "trades": 100, "expectancy_r": 0.10,
                    "total_r": 10.0, "rs": [0.1] * 100}],
         "break_even_bps": 15.0, "trades_per_year": 25.0,
         "sharpe_gross": 0.65,
         "sharpe_net": 0.42, "net_bps": 5.0, "net_expectancy": 0.095,
         "bootstrap": {"iterations": 2000, "total_p05": -5.0,
                       "total_p50": 10.0, "total_p95": 25.0,
                       "losing_paths": 0.12, "dd_p05": -30.0,
                       "dd_p50": -12.0, "observed_total": 8.0,
                       "observed_dd": -14.0}}
    text = summary(r)
    assert "FLOOR on the risk, never a cap" in text
    assert "serial correlation" in text
    assert "BREAK-EVEN" in text and "15 bps" in text
    assert "nothing here is adopted" in text
    # a distribution without the observed value is unreadable
    assert "observed +8.00" in text and "observed -14.00" in text
    # net must be reported, not just the flattering gross figure
    assert "0.42 NET" in text and "gross is the anchor" in text


def test_run_robustness_end_to_end(seeded):
    out = run_robustness(seeded)
    assert set(out) >= {"costs", "break_even_bps", "trades_per_year",
                        "sharpe_gross", "bootstrap"}
    assert out["costs"][0]["cost_bps"] == 0.0        # gross is the anchor
    assert isinstance(summary(out), str)


def test_bootstrap_reports_the_observed_path_alongside_the_distribution():
    rs = [1.0, -0.5, 0.8, -1.0, 1.2, -0.4, 0.6, -0.9, 1.1, -0.3] * 4
    b = bootstrap(rs, iterations=200, seed=3)
    assert b["observed_total"] == pytest.approx(sum(rs), abs=0.01)
    assert b["observed_dd"] <= 0
    # the observed path should sit inside the distribution it came from
    assert b["total_p05"] <= b["observed_total"] <= b["total_p95"]


def test_cost_is_charged_after_the_gap_check_not_before(seeded):
    """The H15a rule tests what the MARKET did. Charging slippage first
    would cancel fills that really would have filled just under the cap,
    which showed up as trade counts wobbling with the cost level."""
    from mve.setups import MAX_ENTRY_GAP
    counts = []
    for bps in (0.0, 2.0, 5.0, 10.0):
        res = run_backtest(seeded, universe=["RUNR"], benchmark="SPY",
                           sector_map={}, max_gap_pct=MAX_ENTRY_GAP,
                           cost_bps=bps)
        counts.append(len([t for t in res.trades if t.setup == "RS-02"]))
    assert len(set(counts)) == 1, (
        f"cost changed which signals were taken: {counts}")
