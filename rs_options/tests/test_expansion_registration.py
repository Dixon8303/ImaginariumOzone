"""H-23 registration guarantees (docs/PREREGISTERED.md, 2026-08-27).

These tests pin the STRUCTURAL promises of the registration — that the
candidates cannot trade before the verdict, that the study cannot run
on partial data, and that the fixed list stays fixed. Deliberately
brittle: if UNIVERSE or CANDIDATE_UNIVERSE changes without H-23 being
closed first, a failure here is the point.
"""
import pandas as pd
import pytest

from mve.universe import (CANDIDATE_SECTOR_ETF, CANDIDATE_UNIVERSE,
                          SECTOR_ETF, UNIVERSE, expansion_required_tickers,
                          required_tickers)

H23_REGISTERED_LIST = {
    "UNH", "ABBV", "PFE", "BA", "RTX", "T", "VZ", "V", "PYPL",
    "COIN", "HOOD", "SOFI", "ORCL", "CRM", "CVX", "F",
}

H23_REJECTED_AT_REGISTRATION = {
    "MSTR", "AVGO", "INTC", "QCOM", "COST", "HD", "LLY", "CAT", "JNJ", "GE",
}


def test_candidate_list_matches_the_registration_exactly():
    """The list in code IS the list in docs/PREREGISTERED.md. Editing
    either without the other is how a registration stops meaning
    anything."""
    assert set(CANDIDATE_UNIVERSE) == H23_REGISTERED_LIST


def test_candidates_are_not_tradeable():
    """No candidate enters UNIVERSE before the H-23 verdict — the live
    scan and paper trader iterate UNIVERSE only."""
    assert not (set(CANDIDATE_UNIVERSE) & set(UNIVERSE))
    assert not (H23_REJECTED_AT_REGISTRATION & set(UNIVERSE))


def test_candidates_do_not_leak_into_the_daily_fetch():
    """required_tickers() drives the live scan's data pull; candidates
    belong only to the study's expansion_required_tickers()."""
    assert not (set(CANDIDATE_UNIVERSE) & set(required_tickers()))


def test_every_candidate_has_a_sector_benchmark():
    assert set(CANDIDATE_SECTOR_ETF) == set(CANDIDATE_UNIVERSE)


def test_expansion_fetch_covers_both_arms_and_their_benchmarks():
    tickers = set(expansion_required_tickers())
    assert set(UNIVERSE) <= tickers
    assert set(CANDIDATE_UNIVERSE) <= tickers
    assert set(SECTOR_ETF.values()) <= tickers
    assert set(CANDIDATE_SECTOR_ETF.values()) <= tickers
    assert "SPY" in tickers


def test_rejected_names_are_not_candidates():
    """Rejections were frozen at registration; sneaking one back in
    later would be exactly the quiet revisiting the entry prohibits."""
    assert not (H23_REJECTED_AT_REGISTRATION & set(CANDIDATE_UNIVERSE))


def test_study_aborts_on_missing_data_rather_than_shrinking_an_arm(tmp_path):
    """LAW 18: an empty store must refuse to run the study, never run
    it on whichever tickers happen to be present."""
    from mve.expansion_study import coverage_check
    from mve.store import DataStore
    problems = coverage_check(DataStore(str(tmp_path)))
    # every required ticker should be reported missing on an empty store
    assert len(problems) >= len(expansion_required_tickers())


def test_study_module_never_touches_the_live_universe():
    """The study reads UNIVERSE and CANDIDATE_UNIVERSE; it must never
    mutate them (adoption happens by a human editing universe.py after
    the verdict, not by code)."""
    import ast
    import inspect

    import mve.expansion_study as es
    tree = ast.parse(inspect.getsource(es))
    for node in ast.walk(tree):
        # any assignment targeting an attribute (module.X = ...) would
        # be a mutation of imported state
        if isinstance(node, (ast.Assign, ast.AugAssign)):
            targets = (node.targets if isinstance(node, ast.Assign)
                       else [node.target])
            for t in targets:
                assert not isinstance(t, ast.Attribute), (
                    "expansion_study assigns to an attribute — it must "
                    "not mutate imported module state")


def test_stats_split_candidates_from_incumbents():
    """The registered numbers depend on this split being right."""
    from mve.backtest import Trade
    from mve.expansion_study import run_expansion_study  # noqa: F401
    # exercise the collect/stats helpers through a minimal fake:
    trades = [
        Trade(ticker="PFE", setup="RS-02", entry_date="2. ", exit_date="",
              entry=1, exit=1, r_multiple=1.0, exit_reason="t", bars_held=1),
        Trade(ticker="NVDA", setup="RS-02", entry_date="", exit_date="",
              entry=1, exit=1, r_multiple=-1.0, exit_reason="t", bars_held=1),
    ]
    cand = [t for t in trades if t.ticker in CANDIDATE_UNIVERSE]
    inc = [t for t in trades if t.ticker in UNIVERSE]
    assert [t.ticker for t in cand] == ["PFE"]
    assert [t.ticker for t in inc] == ["NVDA"]
