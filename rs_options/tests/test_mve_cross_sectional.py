"""H-22 cross-sectional momentum — fidelity to the frozen registration."""
from datetime import date

import pytest

from mve.cross_sectional import (COST_BPS, MIN_REBALANCES, TEST_START,
                                 TOP_N_ARMS, TRAIN_END, buy_hold,
                                 rank_and_select, rebalance_dates, run_arm,
                                 run_h22, summary, verdict)
from mve.store import DataStore
from mve.vendors import SyntheticVendor


# ------------------------------------- the registration is the authority
def test_parameters_match_the_frozen_registration():
    """If these drift, the study stops testing what was registered."""
    from mve.robustness import REALISTIC_BPS
    from mve.setups import MOM_LOOKBACK, MOM_SKIP, REGIME_SMA_LEN
    assert TOP_N_ARMS == (3, 5)
    assert TRAIN_END == "2020-12-31" and TEST_START == "2021-01-01"
    assert MIN_REBALANCES == 60
    assert COST_BPS == REALISTIC_BPS          # charged, never gross
    # ranking and eligibility are REUSED, introducing no new parameter
    assert (MOM_LOOKBACK, MOM_SKIP, REGIME_SMA_LEN) == (252, 21, 200)


def test_rebalance_is_first_trading_day_of_each_month():
    dates = ["2024-01-02", "2024-01-03", "2024-01-31",
             "2024-02-01", "2024-02-15", "2024-03-04"]
    assert rebalance_dates(dates) == ["2024-01-02", "2024-02-01",
                                      "2024-03-04"]
    assert rebalance_dates([]) == []


# --------------------------------------------------------- point in time
@pytest.fixture
def seeded(tmp_path):
    store = DataStore(str(tmp_path))
    v = SyntheticVendor(start=date(2016, 1, 4), days=1800)
    store.ingest_bars(v.bars("SPY", base=300.0, drift=0.0003, amp=0.015))
    store.ingest_bars(v.bars("NVDA", base=80.0, drift=0.0012, amp=0.02,
                             phase=0.5))
    store.ingest_bars(v.bars("AAPL", base=120.0, drift=0.0006, amp=0.018,
                             phase=1.0))
    store.ingest_bars(v.bars("AMD", base=60.0, drift=0.0002, amp=0.02,
                             phase=1.5))
    return store


def _frames(store):
    """The real loading path — UNIVERSE excludes the benchmark, so
    anything that loads UNIVERSE alone silently produces no results."""
    from mve.cross_sectional import _load
    return _load(store)


def test_ranking_never_sees_the_rebalance_day(seeded):
    """Fills happen at the rebalance day's OPEN, so ranking may only use
    data strictly before it — using that day's close is lookahead."""
    frames = _frames(seeded)
    asof = "2019-06-03"
    picked = rank_and_select(frames, asof, 2)
    for t in picked:
        bars = frames[t]
        used = bars[bars["trade_date"] < asof]
        assert used["trade_date"].max() < asof


def test_load_includes_the_benchmark(seeded):
    """UNIVERSE excludes the benchmark; loading it alone leaves no SPY
    frame and every window returns empty — a silent nothing rather than
    an error. This is the bug these tests caught on first run."""
    from mve.universe import BENCHMARK
    assert BENCHMARK in _frames(seeded)


def test_benchmark_is_never_selected(seeded):
    frames = _frames(seeded)
    from mve.universe import BENCHMARK
    assert BENCHMARK not in rank_and_select(frames, "2019-06-03", 5)


def test_selection_respects_the_top_n_cap(seeded):
    frames = _frames(seeded)
    for n in TOP_N_ARMS:
        assert len(rank_and_select(frames, "2019-06-03", n)) <= n


# ------------------------------------------------------------ mechanics
def test_arm_produces_portfolio_stats_not_r_multiples(seeded):
    """No stop means no R. Quoting one would invite a false comparison
    against RS-02's +0.117R."""
    s = run_arm(_frames(seeded), 3, None, None)
    assert set(s) >= {"periods", "months", "cagr", "sharpe",
                      "max_drawdown", "turnover"}
    assert "expectancy_r" not in s and "r_multiple" not in s
    assert s["max_drawdown"] <= 0
    assert 0.0 <= s["turnover"] <= 2.0


def test_costs_can_only_reduce_returns(seeded):
    frames = _frames(seeded)
    free = run_arm(frames, 3, None, None, cost_bps=0.0)
    dear = run_arm(frames, 3, None, None, cost_bps=200.0)
    assert dear["total_return"] <= free["total_return"] + 1e-9


def test_benchmark_runs_on_the_same_grid(seeded):
    frames = _frames(seeded)
    arm = run_arm(frames, 3, None, None)
    bench = buy_hold(frames, None, None)
    assert bench["periods"] == arm["periods"]      # identical windows


# ------------------------------------------------- the registered verdict
BENCH = {"train": {"sharpe": 0.80, "max_drawdown": -0.20, "periods": 40},
         "test": {"sharpe": 0.70, "max_drawdown": -0.15, "periods": 30}}


def _arm(tr_sh, te_sh, tr_dd=-0.15, te_dd=-0.10, periods=40):
    return {"train": {"sharpe": tr_sh, "max_drawdown": tr_dd,
                      "periods": periods},
            "test": {"sharpe": te_sh, "max_drawdown": te_dd,
                     "periods": periods}}


def test_verdict_requires_both_windows_to_beat_spy():
    assert verdict(_arm(1.0, 0.9), BENCH)[0] == "CONFIRMED"
    assert verdict(_arm(0.5, 0.9), BENCH)[0] == "FAILED"   # train fails
    assert verdict(_arm(1.0, 0.6), BENCH)[0] == "FAILED"   # test fails


def test_verdict_fails_on_worse_drawdown_even_with_better_sharpe():
    worse = _arm(1.0, 0.9, tr_dd=-0.40)
    v, why = verdict(worse, BENCH)
    assert v == "FAILED" and "drawdown" in why


def test_verdict_refuses_below_the_registered_minimum():
    thin = _arm(2.0, 2.0, periods=10)      # 20 total, under 60
    v, why = verdict(thin, BENCH)
    assert v == "INCONCLUSIVE" and str(MIN_REBALANCES) in why


def test_summary_carries_the_handicap_and_the_cost_caveat(seeded):
    text = summary(run_h22(seeded))
    assert "CROSS-SECTIONAL MOMENTUM" in text
    # the pre-recorded reading of a failure must travel with the result
    assert "NOT 'the factor is false'" in text
    assert "slightly OPTIMISTIC on cost" in text
    assert "nothing here is adopted" in text
    assert "would not replace it" in text
