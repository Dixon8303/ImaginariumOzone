"""Volatility context: IV rank/percentile, the volatility box, and the
uncalibrated fail-honest path (spec §23, §34, §72 Experiment I)."""
from datetime import date

import pandas as pd
import pytest

from mve.session import run_research_session
from mve.store import DataStore
from mve.telemetry import TelemetryLog
from mve.vendors import SyntheticVendor
from mve.vol_context import (EXTREME_IV_RANK, MIN_SESSIONS, IVHistory,
                             atm_iv_from_chain, iv_percentile, iv_rank,
                             volatility_penalty)

AS_OF = "2026-07-01"


def series(values):
    return pd.Series([float(v) for v in values])


# ------------------------------------------------------------ rank math
def test_iv_rank_none_when_uncalibrated():
    assert iv_rank(series([0.3] * (MIN_SESSIONS - 1)), 0.4) is None
    assert iv_percentile(series([0.3] * (MIN_SESSIONS - 1)), 0.4) is None


def test_iv_rank_and_percentile_bounds():
    hist = series([0.20 + 0.01 * i for i in range(30)])   # 0.20 .. 0.49
    assert iv_rank(hist, 0.49) == pytest.approx(100.0)
    assert iv_rank(hist, 0.20) == pytest.approx(0.0)
    assert iv_rank(hist, 0.60) == 100.0                    # clamped
    mid_rank = iv_rank(hist, 0.345)
    assert 40 < mid_rank < 60
    assert iv_percentile(hist, 0.35) == pytest.approx(100.0 * 15 / 30)


def test_iv_rank_flat_history_is_50():
    assert iv_rank(series([0.30] * 30), 0.30) == 50.0


# -------------------------------------------------------- volatility box
def test_volatility_penalty_ladder():
    assert volatility_penalty(None) == (0, "uncalibrated")
    assert volatility_penalty(10.0) == (0, "normal_iv")
    assert volatility_penalty(65.0) == (1, "rich_iv")
    assert volatility_penalty(EXTREME_IV_RANK + 5) == (2, "extreme_iv")


# ------------------------------------------------------------ atm proxy
def test_atm_iv_from_chain_uses_atm_band():
    chain = SyntheticVendor(start=date(2026, 3, 2)).chain(
        "TCKR", AS_OF, spot=100.0, iv=0.30)
    atm = atm_iv_from_chain(chain)
    assert atm is not None
    assert 0.28 <= atm <= 0.34            # near the 0.30 base, not the wings
    assert atm_iv_from_chain(pd.DataFrame()) is None


# ------------------------------------------------------- history storage
def test_iv_history_idempotent_and_point_in_time(tmp_path):
    h = IVHistory(str(tmp_path))
    for i, day in enumerate(pd.bdate_range("2026-05-01", periods=25)):
        h.record("TCKR", str(day.date()), 0.20 + 0.005 * i)
    h.record("TCKR", "2026-05-01", 0.20)              # duplicate day
    full = h.series("TCKR")
    assert len(full) == 25
    pit = h.series("TCKR", before=str(pd.bdate_range("2026-05-01", periods=25)[10].date()))
    assert len(pit) == 10                              # strictly before


# ------------------------------------------------------ session wiring
def test_session_records_iv_context_and_applies_penalty(tmp_path):
    store = DataStore(str(tmp_path / "parquet"))
    v = SyntheticVendor(start=date(2026, 3, 2), days=115)
    store.ingest_bars(v.bars("SPY", base=500.0, drift=0.0002, amp=0.015))
    store.ingest_bars(v.bars("RUNR", base=80.0, drift=0.0035, amp=0.01, phase=1.0))
    spot = float(store.bars("RUNR", end=AS_OF)["close"].iloc[-1])
    store.ingest_chains(v.chain("RUNR", AS_OF, spot, iv=0.60))   # rich premium

    # Seed 25 prior sessions of much lower IV → today's 0.60 ranks extreme.
    h = IVHistory(str(tmp_path / "parquet" / "iv_history"))
    for i, day in enumerate(pd.bdate_range("2026-05-01", periods=25)):
        h.record("RUNR", str(day.date()), 0.25 + 0.002 * i)

    telemetry = TelemetryLog(str(tmp_path / "t.jsonl"))
    run_research_session(store, universe=["RUNR"], as_of=AS_OF,
                         telemetry=telemetry, benchmark="SPY",
                         active_setups=("RS-01", "RS-02"))

    evaluations = [r for r in telemetry.records() if r["type"] == "evaluation"]
    assert evaluations
    ctx = evaluations[0]["iv_context"]
    assert ctx["label"] == "extreme_iv" and ctx["penalty"] == 2
    assert ctx["iv_rank"] == 100.0
    # Net score in the decision reflects the -2 volatility-box penalty.
    assert evaluations[0]["decision"]["Scoring"]["Net_Score"] == 8   # 10 - 2
    # Today's reading was appended for future sessions.
    assert len(h.series("RUNR")) == 26


def test_session_uncalibrated_iv_applies_no_penalty(tmp_path):
    store = DataStore(str(tmp_path / "parquet"))
    v = SyntheticVendor(start=date(2026, 3, 2), days=115)
    store.ingest_bars(v.bars("SPY", base=500.0, drift=0.0002, amp=0.015))
    store.ingest_bars(v.bars("RUNR", base=80.0, drift=0.0035, amp=0.01, phase=1.0))
    spot = float(store.bars("RUNR", end=AS_OF)["close"].iloc[-1])
    store.ingest_chains(v.chain("RUNR", AS_OF, spot, iv=0.60))

    telemetry = TelemetryLog(str(tmp_path / "t.jsonl"))
    run_research_session(store, universe=["RUNR"], as_of=AS_OF,
                         telemetry=telemetry, benchmark="SPY",
                         active_setups=("RS-01", "RS-02"))
    ctx = [r for r in telemetry.records()
           if r["type"] == "evaluation"][0]["iv_context"]
    assert ctx["label"] == "uncalibrated" and ctx["penalty"] == 0
    assert ctx["iv_rank"] is None
