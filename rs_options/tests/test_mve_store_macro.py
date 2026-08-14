"""MVE data layer + macro calendar tests (spec §46, §11-§12)."""
import os
from datetime import date, datetime, timezone

import pandas as pd
import pytest

from mve.macro_calendar import MacroEvent, event_state, load_calendar, macro_state
from mve.store import DataStore
from mve.vendors import SyntheticVendor


@pytest.fixture
def store(tmp_path):
    return DataStore(str(tmp_path / "parquet"))


@pytest.fixture
def vendor():
    return SyntheticVendor(start=date(2026, 3, 2), days=60)


# ---------------------------------------------------------------- store
def test_bar_ingest_roundtrip(store, vendor):
    bars = vendor.bars("TCKR")
    assert store.ingest_bars(bars) == len(bars)
    out = store.bars("TCKR")
    assert len(out) == len(bars)
    assert list(out["trade_date"]) == sorted(out["trade_date"])


def test_bar_ingest_idempotent(store, vendor):
    bars = vendor.bars("TCKR")
    store.ingest_bars(bars)
    store.ingest_bars(bars)                       # same batch again
    assert len(store.bars("TCKR")) == len(bars)   # no duplicates (§46)


def test_point_in_time_end_is_inclusive_and_excludes_future(store, vendor):
    bars = vendor.bars("TCKR")
    store.ingest_bars(bars)
    cutoff = bars["trade_date"].iloc[29]
    pit = store.bars("TCKR", end=cutoff)
    assert len(pit) == 30
    assert pit["trade_date"].iloc[-1] == cutoff   # no future rows (§49)


def test_chain_ingest_roundtrip(store, vendor):
    chain = vendor.chain("TCKR", "2026-05-01", spot=100.0)
    assert store.ingest_chains(chain) == len(chain)
    out = store.chain("TCKR", "2026-05-01")
    assert len(out) == len(chain)
    assert store.chain("TCKR", "2026-05-02").empty


def test_bar_gap_qa_flags_missing_week(store, vendor):
    bars = vendor.bars("TCKR")
    holey = pd.concat([bars.iloc[:20], bars.iloc[30:]])   # drop two weeks
    store.ingest_bars(holey)
    gaps = store.bar_gaps("TCKR")
    assert len(gaps) == 1
    assert int(gaps["gap_days"].iloc[0]) > 4


def test_ingest_rejects_missing_columns(store):
    with pytest.raises(ValueError):
        store.ingest_bars(pd.DataFrame({"ticker": ["X"], "close": [1.0]}))


# ------------------------------------------------------- macro calendar
def _cal():
    return [MacroEvent("CPI", datetime(2026, 8, 12, 12, 30, tzinfo=timezone.utc), 1),
            MacroEvent("Retail", datetime(2026, 8, 14, 12, 30, tzinfo=timezone.utc), 2)]


def test_event_window_tier1_hard_blocks():
    now = datetime(2026, 8, 12, 12, 25, tzinfo=timezone.utc)
    state, event = event_state(_cal(), now)
    assert state == "EVENT_WINDOW" and event.event == "CPI"
    assert macro_state(_cal(), now).hard_block


def test_pre_event_no_hard_block():
    now = datetime(2026, 8, 12, 11, 45, tzinfo=timezone.utc)
    state, _ = event_state(_cal(), now)
    assert state == "PRE_EVENT"
    assert not macro_state(_cal(), now).hard_block


def test_tier2_event_window_soft():
    now = datetime(2026, 8, 14, 12, 25, tzinfo=timezone.utc)
    ms = macro_state(_cal(), now)
    assert "Retail" in ms.label and not ms.hard_block


def test_quiet_time_none():
    now = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)
    assert event_state(_cal(), now)[0] == "NONE"
    assert macro_state(_cal(), now).label == ""


def test_load_calendar_csv(tmp_path):
    p = tmp_path / "cal.csv"
    p.write_text("event,timestamp_utc,tier,expected,prior\n"
                 "CPI,2026-08-12T12:30:00+00:00,1,0.2,0.3\n"
                 "FOMC,2026-09-16T18:00:00+00:00,1,,\n")
    events = load_calendar(str(p))
    assert [e.event for e in events] == ["CPI", "FOMC"]
    assert events[0].expected == 0.2 and events[1].expected is None
