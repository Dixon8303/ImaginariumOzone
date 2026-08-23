"""H23 Markov regime matrix — and the null that makes it readable."""
import random

import pytest

from mve.markov import (LOOKBACK, analyse, daily_returns, label_states,
                        shuffled_null, signal_strength, stationary,
                        stickiness, summary, transition_matrix)


def walk(n=3000, drift=0.0005, vol=0.012, seed=1):
    rng = random.Random(seed)
    px, out = 100.0, [100.0]
    for _ in range(n):
        px *= (1.0 + rng.gauss(drift, vol))
        out.append(px)
    return out


# ------------------------------------------------------- state labels
def test_states_follow_the_dossier_definition():
    rising = [100.0 * (1.03 ** i) for i in range(40)]     # +3%/bar
    assert set(label_states(rising)) == {1}               # all Bull
    falling = [100.0 * (0.97 ** i) for i in range(40)]
    assert set(label_states(falling)) == {-1}             # all Bear
    flat = [100.0] * 40
    assert set(label_states(flat)) == {0}                 # all Sideways


def test_states_need_a_full_window():
    assert label_states([100.0] * (LOOKBACK - 1)) == []


# -------------------------------------------------- matrix mechanics
def test_transition_rows_sum_to_one():
    m = transition_matrix(label_states(walk()))
    for row in m.values():
        assert sum(row.values()) == pytest.approx(1.0, abs=1e-9)


def test_empty_history_gives_a_defined_matrix_not_a_crash():
    m = transition_matrix([])
    assert all(sum(r.values()) == 0.0 for r in m.values())


def test_stationary_distribution_sums_to_one():
    st = stationary(transition_matrix(label_states(walk())))
    assert sum(st.values()) == pytest.approx(1.0, abs=1e-6)


def test_signal_is_bull_minus_bear():
    m = {1: {1: 0.7, 0: 0.2, -1: 0.1}, 0: {1: 0.3, 0: 0.4, -1: 0.3},
         -1: {1: 0.1, 0: 0.2, -1: 0.7}}
    assert signal_strength(m, 1) == pytest.approx(0.6)
    assert signal_strength(m, -1) == pytest.approx(-0.6)
    assert signal_strength(m, 0) == pytest.approx(0.0)
    assert signal_strength(m, 99) == 0.0          # unknown state, no signal


# ------------------------------------------------------------ THE NULL
def test_pure_noise_is_already_extremely_sticky():
    """The finding that undoes the dossier's headline: a random walk has
    no regimes at all, yet scores high stickiness purely because
    consecutive 20-day windows overlap by 19 bars."""
    s = stickiness(label_states(walk(n=5000, drift=0.0, seed=7)))
    assert s > 0.7, (
        "if noise is not sticky under this definition the whole "
        f"overlapping-window critique would be wrong; got {s:.1%}")


def test_null_brackets_noise_so_noise_does_not_beat_it():
    closes = walk(n=2500, drift=0.0, seed=11)
    real = stickiness(label_states(closes))
    null = shuffled_null(closes, trials=40, seed=5)
    assert null["p05"] <= null["mean"] <= null["p95"]
    # a random walk must NOT look informative against its own shuffle
    assert real <= null["p95"] * 1.05


def test_null_declines_on_too_little_history():
    assert shuffled_null([100.0] * 10, trials=5) == {}


def test_daily_returns_skip_zero_denominators():
    assert daily_returns([100.0, 0.0, 50.0]) == pytest.approx([-1.0])


# ------------------------------------------------------------- report
def test_analyse_reports_effective_sample_size():
    r = analyse(walk(n=2200, seed=3), "TEST")
    assert r["independent_windows"] == r["bars"] // LOOKBACK
    assert r["independent_windows"] < r["bars"]        # the correction
    assert r["excess"] is not None


def test_summary_leads_with_the_null_and_refuses_to_trade_it():
    r = analyse(walk(n=2200, seed=3), "TEST")
    text = summary([r])
    assert "WHY THE NULL IS THE WHOLE POINT" in text
    assert "random walk scores ~86%" in text
    assert "too confident" in text                     # sample-size caveat
    assert "it does not trade" in text
    assert "prohibited" in text                        # short leg, §87


def test_summary_survives_an_unanalysable_ticker():
    assert isinstance(summary([{}, None]), str)
