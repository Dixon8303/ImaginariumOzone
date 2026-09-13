"""H-26 cohort guards (registered 2026-09-12 in docs/PREREGISTERED.md).

Until the study returns CONFIRMED *and* the operator adopts, these ten
names must not reach the tradeable universe, the live scan, or the
paper trader. These tests are the mechanical half of that promise.
"""
import ast
import pathlib

import pytest

from mve.h26_study import MAX_COMBINED_DRAG, MIN_TRADES, judge
from mve.universe import (CANDIDATE_UNIVERSE, H26_CANDIDATE_SECTOR_ETF,
                          H26_CANDIDATE_UNIVERSE, SECTOR_ETF, UNIVERSE,
                          h26_required_tickers, required_tickers)

COHORT = {"FCX", "NEM", "CCJ", "NEE", "SO", "DHI", "LEN", "UNP", "PLD",
          "ISRG"}


def test_cohort_is_exactly_as_registered():
    """The registration froze ten names. Not nine, not eleven."""
    assert set(H26_CANDIDATE_UNIVERSE) == COHORT


def test_clusters_are_as_registered():
    assert H26_CANDIDATE_UNIVERSE == {
        "FCX": "materials", "NEM": "materials",
        "CCJ": "energy",
        "NEE": "utilities", "SO": "utilities",
        "DHI": "homebuilders", "LEN": "homebuilders",
        "UNP": "rail",
        "PLD": "real_estate",
        "ISRG": "health_devices",
    }


def test_sector_benchmarks_are_as_registered():
    assert H26_CANDIDATE_SECTOR_ETF == {
        "FCX": "XLB", "NEM": "XLB", "CCJ": "XLE",
        "NEE": "XLU", "SO": "XLU", "DHI": "XLY", "LEN": "XLY",
        "UNP": "XLI", "PLD": "XLRE", "ISRG": "XLV",
    }


def test_candidates_are_not_tradeable():
    """The whole point of the pre-registration: no candidate may be in
    the live universe before a verdict AND an adoption decision."""
    assert COHORT & set(UNIVERSE) == set()
    assert COHORT & set(required_tickers()) == set()


def test_names_rejected_at_registration_stay_out():
    """Recorded rejections cannot be quietly promoted later."""
    rejected = {"CPPMF", "OUST", "AMBA", "CGNX", "AME", "FSLR", "LIN",
                "GLD", "NUE", "GM", "CRWD", "RCL", "CCL"}
    assert rejected & set(UNIVERSE) == set()
    assert rejected & set(H26_CANDIDATE_UNIVERSE) == set()


def test_h23_cohort_is_not_mutated():
    """H-23's set stays frozen for ITS study's reproducibility — H-26
    is a separate set, not an edit of it."""
    assert len(CANDIDATE_UNIVERSE) == 16
    assert COHORT & set(CANDIDATE_UNIVERSE) == set()


def test_fetch_set_covers_both_arms_and_the_new_etfs():
    req = set(h26_required_tickers())
    assert COHORT <= req                       # candidates
    assert set(UNIVERSE) <= req                # incumbents
    assert {"XLB", "XLU", "XLRE"} <= req       # new sector benchmarks
    assert set(SECTOR_ETF.values()) <= req


def test_new_sector_etfs_are_not_already_benchmarks():
    """XLB/XLU/XLRE are new to the program — if one were already in
    SECTOR_ETF the registration's 'new cluster' claim would be wrong."""
    assert {"XLB", "XLU", "XLRE"} & set(SECTOR_ETF.values()) == set()


def test_universe_module_declares_no_mutation_of_live_universe():
    """AST check: importing the module must not mutate UNIVERSE or
    SECTOR_ETF at import time (an .update() would adopt by accident)."""
    src = pathlib.Path("mve/universe.py").read_text()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "update" and isinstance(
                    node.func.value, ast.Name):
                assert node.func.value.id not in ("UNIVERSE", "SECTOR_ETF")


# ── the frozen criterion, as implemented ─────────────────────────────
def arm(n, exp):
    return {"trades": n, "expectancy_r": exp, "total_r": round(n * exp, 2),
            "win_rate": 0.5}


def test_judge_confirms_on_the_registered_bar():
    v = judge(arm(MIN_TRADES, 0.10), arm(800, 0.13), arm(900, 0.125))
    assert v["verdict"] == "CONFIRMED"


def test_judge_inconclusive_below_the_trade_minimum():
    v = judge(arm(MIN_TRADES - 1, 0.40), arm(800, 0.13), arm(900, 0.13))
    assert v["verdict"] == "INCONCLUSIVE"
    assert str(MIN_TRADES) in v["reason"]


def test_judge_fails_on_negative_candidates():
    v = judge(arm(200, -0.02), arm(800, 0.13), arm(900, 0.11))
    assert v["verdict"] == "FAILED"


def test_judge_fails_when_combined_drags_past_the_registered_bound():
    """Candidates positive on their own but they poison the whole
    universe — the second clause exists exactly for this."""
    v = judge(arm(200, 0.01), arm(800, 0.130), arm(900, 0.060))
    assert v["verdict"] == "FAILED"
    assert v["drag"] == pytest.approx(0.070)


def test_judge_allows_drag_exactly_at_the_bound():
    v = judge(arm(200, 0.05), arm(800, 0.130),
              arm(900, 0.130 - MAX_COMBINED_DRAG))
    assert v["verdict"] == "CONFIRMED"
