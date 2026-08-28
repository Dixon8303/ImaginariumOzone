"""mve.significance — t-stats and exact loss-streak math (2026-08-28
dossier assessment, docs/RESEARCH_LOG.md)."""
import pytest

from mve.significance import (T_SIGNIFICANT, forward_track_line,
                              p_loss_streak, streak_table, t_stat,
                              years_to_t)


# ── t-statistics ─────────────────────────────────────────────────────
def test_t_stat_of_the_holdout_is_barely_significant():
    """The program's own headline: Sharpe 0.52 over 15 years lands at
    t ~= 2.0 — right at the conventional bar, not comfortably past it."""
    t = t_stat(0.52, 15.0)
    assert t == pytest.approx(2.01, abs=0.01)
    assert T_SIGNIFICANT == 2.0


def test_t_stat_undefined_cases():
    assert t_stat(None, 15.0) is None
    assert t_stat(0.5, 0.0) is None


def test_years_to_t_matches_the_dossier_arithmetic():
    """A Sharpe-0.5 forward track needs 16 years for t=2 — the number
    that reframes what the paper track is for."""
    assert years_to_t(0.5) == pytest.approx(16.0)
    assert years_to_t(1.0) == pytest.approx(4.0)
    assert years_to_t(None) is None
    assert years_to_t(0.0) is None
    assert years_to_t(-0.3) is None          # never "gets there"


# ── streak math ──────────────────────────────────────────────────────
def test_streaks_reproduce_the_dossier_examples_exactly():
    """50% win rate, 100 trades: the video's 97/81/55 claims, verified
    to the digit by the exact DP."""
    assert p_loss_streak(0.50, 4, 100) == pytest.approx(0.973, abs=0.001)
    assert p_loss_streak(0.50, 5, 100) == pytest.approx(0.810, abs=0.001)
    assert p_loss_streak(0.50, 6, 100) == pytest.approx(0.546, abs=0.001)


def test_streaks_at_rs02_win_rate():
    """At the measured 52% win rate over one expanded year (~40
    trades): 2-loss certain, 3-loss ~94%, 4-loss ~70%. This is the
    table that separates expected variance from breakage — and the
    reason the micro cool-off must be understood as a survival brake,
    not an information signal."""
    assert p_loss_streak(0.52, 2, 40) > 0.999
    assert p_loss_streak(0.52, 3, 40) == pytest.approx(0.94, abs=0.01)
    assert p_loss_streak(0.52, 4, 40) == pytest.approx(0.70, abs=0.01)


def test_streak_edge_cases():
    assert p_loss_streak(0.5, 5, 4) == 0.0       # streak longer than sample
    assert p_loss_streak(1.0, 2, 100) == 0.0     # never loses
    assert p_loss_streak(0.0, 3, 3) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        p_loss_streak(1.5, 2, 10)


def test_streak_table_shape():
    table = streak_table(0.52, 40)
    assert set(table) == {2, 3, 4, 5, 6}
    assert all(0.0 <= v <= 1.0 for v in table.values())
    # monotone: longer streaks are never MORE likely
    vals = [table[k] for k in sorted(table)]
    assert vals == sorted(vals, reverse=True)


# ── report line ──────────────────────────────────────────────────────
def test_forward_track_line_is_blunt_below_fifty():
    text = forward_track_line(7, win_rate=0.71)
    assert "proves nothing" in text
    assert "variance, not breakage" in text


def test_forward_track_line_above_fifty_still_refuses_proof():
    text = forward_track_line(80, win_rate=0.52)
    assert "far from standalone statistical proof" in text
    assert "16 YEARS" in text
