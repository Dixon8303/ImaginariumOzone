"""H-23 guarantees — post-adoption form (docs/PREREGISTERED.md).

Registered 2026-08-27, CONFIRMED by the pre-registered walk-forward and
ADOPTED by operator decision 2026-08-28 (all-or-none). These tests now
pin the ADOPTION's invariants: the cohort is exactly the registered
list (no quiet additions or removals after the fact), all 16 are
tradeable with their registered clusters and sector benchmarks, and the
names rejected at registration stayed out. Deliberately brittle: a
failure here means someone edited the universe without going through a
registration, which is the point.
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

H23_REGISTERED_CLUSTERS = {
    "UNH": "healthcare", "ABBV": "healthcare", "PFE": "healthcare",
    "BA": "industrials", "RTX": "industrials",
    "T": "telecom", "VZ": "telecom",
    "V": "payments", "PYPL": "payments",
    "COIN": "crypto_fin", "HOOD": "crypto_fin",
    "SOFI": "financials",
    "ORCL": "software", "CRM": "software",
    "CVX": "energy",
    "F": "ev_auto",
}


def test_cohort_matches_the_registration_exactly():
    """The cohort in code IS the list in docs/PREREGISTERED.md —
    adoption was all-or-none, so this must be exactly the 16."""
    assert set(CANDIDATE_UNIVERSE) == H23_REGISTERED_LIST


def test_all_sixteen_are_tradeable_with_registered_clusters():
    """Adoption means every cohort name is in UNIVERSE under the
    cluster it was registered with — a silently changed cluster would
    move it under a different §78 exposure cap."""
    for ticker, cluster in H23_REGISTERED_CLUSTERS.items():
        assert UNIVERSE.get(ticker) == cluster, (
            f"{ticker}: expected cluster {cluster!r}, "
            f"got {UNIVERSE.get(ticker)!r}")


def test_rejected_names_stayed_out():
    """The at-registration rejections were frozen; none of them may
    ride in on the adoption."""
    assert not (H23_REJECTED_AT_REGISTRATION & set(UNIVERSE))
    assert not (H23_REJECTED_AT_REGISTRATION & set(CANDIDATE_UNIVERSE))


def test_every_adopted_name_has_a_sector_benchmark():
    for ticker in H23_REGISTERED_LIST:
        assert ticker in SECTOR_ETF, f"{ticker} missing from SECTOR_ETF"
        assert SECTOR_ETF[ticker] == CANDIDATE_SECTOR_ETF[ticker]


def test_daily_fetch_covers_the_adopted_names():
    """Post-adoption, the live scan's data pull must include all 16
    plus the two sector ETFs the expansion introduced."""
    tickers = set(required_tickers())
    assert H23_REGISTERED_LIST <= tickers
    assert {"XLV", "XLI"} <= tickers


def test_expansion_fetch_is_now_the_daily_fetch():
    """With the cohort adopted, the study's fetch set collapses onto
    the live one — nothing is fetched for the study that the scan does
    not already need."""
    assert set(expansion_required_tickers()) == set(required_tickers())


def test_universe_is_thirty_eight_names():
    """22 incumbents + 16 adopted. A different count means an
    unregistered universe edit."""
    assert len(UNIVERSE) == 38


def test_study_aborts_on_missing_data_rather_than_shrinking_an_arm(tmp_path):
    """LAW 18: an empty store must refuse to run the study, never run
    it on whichever tickers happen to be present."""
    from mve.expansion_study import coverage_check
    from mve.store import DataStore
    problems = coverage_check(DataStore(str(tmp_path)))
    assert len(problems) >= len(expansion_required_tickers())


def test_study_module_never_touches_the_live_universe():
    """The study reads UNIVERSE and CANDIDATE_UNIVERSE; it must never
    mutate them (adoption happened by a human editing universe.py after
    the verdict, not by code)."""
    import ast
    import inspect

    import mve.expansion_study as es
    tree = ast.parse(inspect.getsource(es))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AugAssign)):
            targets = (node.targets if isinstance(node, ast.Assign)
                       else [node.target])
            for t in targets:
                assert not isinstance(t, ast.Attribute), (
                    "expansion_study assigns to an attribute — it must "
                    "not mutate imported module state")


def test_cohort_split_still_works_post_adoption():
    """expansion_study's cohort-vs-incumbent split keys on
    CANDIDATE_UNIVERSE membership, which adoption must not break."""
    from mve.backtest import Trade
    trades = [
        Trade(ticker="PFE", setup="RS-02", entry_date="", exit_date="",
              entry=1, exit=1, r_multiple=1.0, exit_reason="t", bars_held=1),
        Trade(ticker="NVDA", setup="RS-02", entry_date="", exit_date="",
              entry=1, exit=1, r_multiple=-1.0, exit_reason="t", bars_held=1),
    ]
    cohort = [t for t in trades if t.ticker in CANDIDATE_UNIVERSE]
    assert [t.ticker for t in cohort] == ["PFE"]
