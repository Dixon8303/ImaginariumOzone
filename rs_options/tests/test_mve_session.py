"""End-to-end research session tests (spec §61, §81, §87)."""
from datetime import date

import pytest

from rs_options_risk import GateConfig, Mode, RiskEngine

from mve.session import CanaryFailure, run_research_session
from mve.store import DataStore
from mve.telemetry import TelemetryLog
from mve.vendors import SyntheticVendor

AS_OF = "2026-08-12"


@pytest.fixture
def seeded(tmp_path):
    store = DataStore(str(tmp_path / "parquet"))
    v = SyntheticVendor(start=date(2026, 3, 2), days=115)
    store.ingest_bars(v.bars("SPY", base=500.0, drift=0.0002, amp=0.015))
    store.ingest_bars(v.bars("XLK", base=200.0, drift=0.0004, amp=0.015, phase=0.5))
    store.ingest_bars(v.bars("RUNR", base=80.0, drift=0.0035, amp=0.01, phase=1.0))
    store.ingest_bars(v.bars("LAGG", base=60.0, drift=-0.0010, amp=0.02, phase=2.0))
    for t in ("RUNR", "LAGG"):
        spot = float(store.bars(t, end=AS_OF)["close"].iloc[-1])
        store.ingest_chains(v.chain(t, AS_OF, spot))
    return store


def run(seeded, tmp_path, **kw):
    telemetry = TelemetryLog(str(tmp_path / "telemetry.jsonl"))
    result = run_research_session(
        seeded, universe=["RUNR", "LAGG"], as_of=AS_OF, telemetry=telemetry,
        benchmark="SPY", sector_map={"RUNR": "XLK", "LAGG": "XLK"}, **kw)
    return result, telemetry


def test_session_runs_canary_first_and_scans(seeded, tmp_path):
    result, telemetry = run(seeded, tmp_path)
    assert result.canary_ok
    assert result.scanned == 2
    records = telemetry.records()
    assert records[0]["type"] == "canary" and records[0]["ok"]
    assert records[-1]["type"] == "session_summary"


def test_every_candidate_is_logged(seeded, tmp_path):
    result, telemetry = run(seeded, tmp_path)
    evaluations = [r for r in telemetry.records() if r["type"] == "evaluation"]
    assert len(evaluations) == result.candidates
    assert result.candidates == result.authorized + result.rejected
    for e in evaluations:                       # §63: forensics on every decision
        assert "decision" in e


def test_broken_gates_halt_session_before_scanning(seeded, tmp_path):
    broken = RiskEngine(gates=GateConfig(min_net_score=-100,
                                         min_expected_value_r=-100.0))
    telemetry = TelemetryLog(str(tmp_path / "t.jsonl"))
    with pytest.raises(CanaryFailure):
        run_research_session(seeded, universe=["RUNR"], as_of=AS_OF,
                             telemetry=telemetry, engine=broken)
    types = [r["type"] for r in telemetry.records()]
    assert types == ["canary"]                  # nothing scanned (§61)


def test_live_modes_are_refused(seeded, tmp_path):
    telemetry = TelemetryLog(str(tmp_path / "t.jsonl"))
    for mode in (Mode.SHADOW, Mode.PRODUCTION):
        with pytest.raises(ValueError):
            run_research_session(seeded, universe=["RUNR"], as_of=AS_OF,
                                 telemetry=telemetry, mode=mode)


def test_macro_hard_block_rejects_candidates(seeded, tmp_path):
    # CPI at 12:30 UTC on AS_OF... session runs at 15:00 UTC — outside the
    # window; use a calendar with an event at 15:00 to force the block.
    cal = tmp_path / "cal.csv"
    cal.write_text("event,timestamp_utc,tier,expected,prior\n"
                   f"CPI,{AS_OF}T15:05:00+00:00,1,0.2,0.3\n")
    result, telemetry = run(seeded, tmp_path, macro_csv=str(cal))
    if result.candidates:
        assert result.authorized == 0
        evaluations = [r for r in telemetry.records() if r["type"] == "evaluation"]
        assert any("MACRO_EVENT" in e["decision"]["Decision"]["Reasons"]
                   for e in evaluations)


def test_rejection_summary_aggregates(seeded, tmp_path):
    cal = tmp_path / "cal.csv"
    cal.write_text("event,timestamp_utc,tier,expected,prior\n"
                   f"CPI,{AS_OF}T15:05:00+00:00,1,0.2,0.3\n")
    result, telemetry = run(seeded, tmp_path, macro_csv=str(cal))
    summary = telemetry.rejection_summary()
    if result.candidates:
        assert summary.get("MACRO_EVENT", 0) >= 1
