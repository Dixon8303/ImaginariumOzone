"""H18 combination study — composition, overlap bookkeeping, report."""
from datetime import date

import pytest

from mve.combinations import (compose, run_combos, split_members, summary,
                              trade_keys, trade_r)
from mve.hypotheses import GAP_VARIANTS
from mve.store import DataStore
from mve.vendors import SyntheticVendor


class _T:
    def __init__(self, ticker, entry_date, r, setup="RS-02"):
        self.ticker, self.entry_date = ticker, entry_date
        self.r_multiple, self.setup = r, setup


class _R:
    def __init__(self, trades):
        self.trades = trades


# ------------------------------------------------------ helpers

def test_trade_keys_and_r_are_setup_scoped():
    res = _R([_T("A", "2025-01-02", 1.5), _T("B", "2025-01-03", -1.0),
              _T("C", "2025-01-04", 9.0, setup="RS-01")])
    assert trade_keys(res) == {("A", "2025-01-02"), ("B", "2025-01-03")}
    assert trade_r(res)[("B", "2025-01-03")] == -1.0
    assert ("C", "2025-01-04") not in trade_r(res)


def test_compose_requires_every_member_to_pass():
    yes = lambda t, b, s: True                              # noqa: E731
    no = lambda t, b, s: False                              # noqa: E731
    assert compose([yes, yes])("T", None, None)
    assert not compose([yes, no])("T", None, None)


def test_split_members_extracts_gap_and_keeps_tightest():
    variants = {"F": lambda t, b, s: True}
    entry, gap = split_members(["F", "H15a_gap_2pct"], variants)
    assert gap == GAP_VARIANTS["H15a_gap_2pct"]
    assert entry("T", None, None)
    # two gap members -> the tighter (smaller) tolerance binds
    _, gap2 = split_members(["H15a_gap_2pct", "H15b_gap_1pct"], variants)
    assert gap2 == GAP_VARIANTS["H15b_gap_1pct"]


# -------------------------------------------------- integration

@pytest.fixture
def seeded(tmp_path):
    store = DataStore(str(tmp_path))
    v = SyntheticVendor(start=date(2023, 1, 2), days=500)
    store.ingest_bars(v.bars("SPY", base=500.0, drift=0.0002, amp=0.02))
    store.ingest_bars(v.bars("RUNR", base=80.0, drift=0.003, amp=0.012,
                             phase=1.0))
    return store


def test_run_combos_structure_and_bookkeeping(seeded):
    results = run_combos(seeded, news={}, facts={}, sweep=False,
                         families=("H14a_close_top30",))
    assert set(results) == {"baseline", "singles", "combos", "sweep"}
    assert results["sweep"] == []
    # gap primary always rides along with the family primaries
    assert set(results["singles"]) == {"H14a_close_top30", "H15a_gap_2pct"}
    for s in results["singles"].values():
        # removed trades are baseline trades, so their keys must all
        # exist in the baseline set — the accounting cannot invent one.
        assert s["removed"] <= results["baseline"]["keys"]
    combo = results["combos"]["H11a_overhead_10pct+H15a_gap_2pct"]
    assert combo["removed"] <= results["baseline"]["keys"]


def test_pair_sweep_rows_have_both_windows(seeded):
    results = run_combos(seeded, news={}, facts={}, sweep=True,
                         families=("H14a_close_top30",))
    assert len(results["sweep"]) == 1          # one family x the gap primary
    row = results["sweep"][0]
    assert "H14a_close_top30 + H15a_gap_2pct" == row["pair"]
    assert "train" in row and "test" in row


def test_summary_reads_as_a_report(seeded):
    text = summary(run_combos(seeded, news={}, facts={}, sweep=True,
                              families=("H14a_close_top30",)))
    assert "COMBINATION STUDY" in text
    assert "WHAT EACH FILTER REMOVES" in text
    assert "PAIRWISE OVERLAP" in text
    assert "PRE-REGISTERED COMBINATIONS" in text
    assert "PAIR SWEEP — DIAGNOSTIC ONLY" in text
    assert "LAW 12/20" in text
    # the sweep is never allowed to present itself as adoptable
    assert "Nothing below is adoptable" in text
