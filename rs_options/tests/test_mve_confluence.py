"""H19 confluence — vote recording, the trade join, and the report."""
from datetime import date

import pytest

from mve.confluence import (recording_filter, run_confluence, summary,
                            vote_count, vote_table)
from mve.store import DataStore
from mve.vendors import SyntheticVendor


class _T:
    def __init__(self, ticker, sig_date, r, gap=0.0, setup="RS-02"):
        self.ticker, self.signal_date = ticker, sig_date
        self.r_multiple, self.gap_pct, self.setup = r, gap, setup


class _R:
    def __init__(self, trades):
        self.trades = trades


def test_vote_count_joins_signal_votes_and_adds_gap_vote():
    votes = {("A", "2025-03-03"): {"x": True, "y": False, "z": True}}
    small_gap = _T("A", "2025-03-03", 1.0, gap=0.01)
    big_gap = _T("A", "2025-03-03", 1.0, gap=0.05)
    unknown = _T("B", "2025-03-03", 1.0, gap=0.01)
    assert vote_count(small_gap, votes) == 3      # x, z, and the gap vote
    assert vote_count(big_gap, votes) == 2        # gap vote withheld
    assert vote_count(unknown, votes) == 1        # no record -> gap only


def test_vote_table_buckets_by_count_without_merging():
    votes = {("A", "d1"): {"x": True}, ("A", "d2"): {"x": False}}
    res = _R([_T("A", "d1", 2.0, gap=0.01),      # 2 votes
              _T("A", "d2", -1.0, gap=0.01),     # 1 vote
              _T("A", "d2", 0.5, gap=0.01),      # 1 vote
              _T("A", "d9", 1.0, gap=0.01, setup="RS-01")])   # ignored
    rows = vote_table(res, votes)
    assert [(r["votes"], r["trades"]) for r in rows] == [(1, 2), (2, 1)]
    assert rows[0]["total_r"] == -0.5
    assert rows[1]["expectancy_r"] == 2.0


def test_recording_filter_applies_doctrine_and_records():
    votes = {}
    always = {"v": lambda t, b: True}
    # rs02_entry_ok fails closed on tiny history -> no record, no pass
    import pandas as pd
    bars = pd.DataFrame({"trade_date": ["2025-01-02"], "close": [100.0],
                         "open": [100.0], "high": [100.0], "low": [100.0],
                         "volume": [1e6]})
    assert not recording_filter(always, votes)("T", bars, None)
    assert votes == {}                 # a rejected signal leaves no vote


@pytest.fixture
def seeded(tmp_path):
    store = DataStore(str(tmp_path))
    v = SyntheticVendor(start=date(2023, 1, 2), days=500)
    store.ingest_bars(v.bars("SPY", base=500.0, drift=0.0002, amp=0.02))
    store.ingest_bars(v.bars("RUNR", base=80.0, drift=0.003, amp=0.012,
                             phase=1.0))
    return store


def test_run_confluence_end_to_end(seeded):
    results = run_confluence(seeded, news={}, facts={})
    assert set(results) == {"train", "test"}
    for window in results.values():
        assert set(window) == {"rubric", "votes"}
    text = summary(results)
    assert "PART A" in text and "PART B" in text
    assert "sizing by score, never" in text        # gating is ruled out
    assert "LAW 12/20" in text
