"""H20 virgin-data holdout — window discipline and verdict wording."""
from datetime import date

import pytest

from mve.holdout import GAP_LIMIT, HOLDOUT_END, run_holdout, summary
from mve.hypotheses import TRAIN_END
from mve.store import DataStore
from mve.vendors import SyntheticVendor


def test_holdout_window_predates_every_prior_verdict():
    # Prior rounds trained on <= TRAIN_END, so anything after HOLDOUT_END
    # has already been looked at. The holdout must end strictly before.
    assert HOLDOUT_END < TRAIN_END
    assert GAP_LIMIT == 0.02          # the tested threshold, never re-tuned


@pytest.fixture
def seeded(tmp_path):
    store = DataStore(str(tmp_path))
    v = SyntheticVendor(start=date(2015, 1, 2), days=1300)
    store.ingest_bars(v.bars("SPY", base=200.0, drift=0.0002, amp=0.02))
    store.ingest_bars(v.bars("RUNR", base=80.0, drift=0.003, amp=0.012,
                             phase=1.0))
    return store


def test_run_holdout_structure(seeded):
    r = run_holdout(seeded)
    assert set(r) == {"baseline", "score", "gap_filtered", "gap_dose",
                      "thin_stops", "quarantined"}
    assert set(r["score"]) == {"<=7", "8", "9", "10"}
    # the gap filter can only remove fills, never add them
    if r["baseline"] and r["gap_filtered"]:
        assert r["gap_filtered"]["trades"] <= r["baseline"]["trades"]


def test_summary_states_its_own_limits(seeded):
    text = summary(run_holdout(seeded))
    assert "VIRGIN-DATA HOLDOUT" in text
    assert "CANDIDATE 1" in text and "CANDIDATE 2" in text
    # the two disciplines that make this test meaningful
    assert "failure is evidence, not proof" in text
    assert "no longer virgin" in text
    # a threshold effect must not be reported as the registered shape
    assert "threshold effect, which is a different claim" in text


def test_score_verdict_requires_populated_buckets():
    thin = {"baseline": {"trades": 3, "expectancy_r": 0.1, "win_rate": 0.5},
            "score": {k: {"trades": 1, "expectancy_r": 0.0}
                      for k in ("<=7", "8", "9", "10")},
            "gap_filtered": None, "gap_dose": [], "thin_stops": 0,
            "quarantined": 0}
    assert "INCONCLUSIVE" in summary(thin)


def test_gap_verdict_needs_expectancy_and_total_together():
    # Average up, total down is the H5 failure — must NOT confirm.
    base = {"trades": 100, "expectancy_r": 0.10, "win_rate": 0.5}
    worse_total = {"trades": 60, "expectancy_r": 0.15, "win_rate": 0.5}
    text = summary({"baseline": base, "score": {}, "gap_filtered": worse_total,
                    "gap_dose": [], "thin_stops": 0, "quarantined": 0})
    assert "DOES NOT CONFIRM" in text
    better = {"trades": 98, "expectancy_r": 0.15, "win_rate": 0.5}
    text2 = summary({"baseline": base, "score": {}, "gap_filtered": better,
                     "gap_dose": [], "thin_stops": 0, "quarantined": 0})
    assert "CONFIRMS" in text2 and "DOES NOT CONFIRM" not in text2
