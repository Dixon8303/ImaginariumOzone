"""Universe config + pick-list construction (co-pilot selection layer)."""
from datetime import date

from mve.picklist import build_picklist, format_picklist
from mve.session import run_research_session
from mve.store import DataStore
from mve.telemetry import TelemetryLog
from mve.universe import BENCHMARK, SECTOR_ETF, UNIVERSE, required_tickers
from mve.vendors import SyntheticVendor

AS_OF = "2026-07-01"          # date where RS-01 fires on the synthetic path


def test_universe_is_consistent():
    assert BENCHMARK not in UNIVERSE          # benchmark isn't a candidate
    assert set(SECTOR_ETF) <= set(UNIVERSE)   # sector map only covers universe
    req = required_tickers()
    assert BENCHMARK in req
    for t in list(UNIVERSE) + list(SECTOR_ETF.values()):
        assert t in req


def test_picklist_from_live_session(tmp_path):
    store = DataStore(str(tmp_path / "parquet"))
    v = SyntheticVendor(start=date(2026, 3, 2), days=115)
    store.ingest_bars(v.bars("SPY", base=500.0, drift=0.0002, amp=0.015))
    store.ingest_bars(v.bars("XLK", base=200.0, drift=0.0004, amp=0.015, phase=0.5))
    store.ingest_bars(v.bars("RUNR", base=80.0, drift=0.0035, amp=0.01, phase=1.0))
    spot = float(store.bars("RUNR", end=AS_OF)["close"].iloc[-1])
    store.ingest_chains(v.chain("RUNR", AS_OF, spot))

    telemetry = TelemetryLog(str(tmp_path / "t.jsonl"))
    run_research_session(store, universe=["RUNR"], as_of=AS_OF,
                         telemetry=telemetry, benchmark="SPY",
                         sector_map={"RUNR": "XLK"})

    picks = build_picklist(telemetry.records())
    assert len(picks) == 1
    p = picks[0]
    assert p["ticker"] == "RUNR" and p["setup"] == "RS-01"
    assert p["quantity"] >= 1
    assert p["est_cost"] > 0
    assert p["worst_case_loss"] > 0
    assert p["invalidation_price"] < spot
    assert "C" in p["contract"]

    text = format_picklist(picks)
    assert "RUNR" in text and "execute the pick list" in text


def test_picklist_empty_and_rejections_excluded():
    records = [
        {"type": "canary", "ok": True},
        {"type": "evaluation", "ticker": "X", "setup": "RS-01",
         "decision": {"Decision": {"Status": "REJECT", "Reasons": ["RISK_LIMIT"]}}},
        {"type": "session_summary"},
    ]
    assert build_picklist(records) == []
    assert "NO TRADE" in format_picklist([])


def test_picklist_ranked_by_net_score():
    def rec(ticker, score):
        return {"type": "evaluation", "ticker": ticker, "setup": "RS-02",
                "invalidation_price": 1.0,
                "option": {"strike": 10, "expiry": "2026-08-01",
                           "bid": 1.0, "ask": 1.1},
                "decision": {"Decision": {"Status": "AUTHORIZE"},
                             "Risk": {"Contract_Quantity": 1, "Total_Risk": 50.0,
                                      "Worst_Case_Scenario": "BASE"},
                             "Scoring": {"Net_Score": score}}}
    picks = build_picklist([rec("LOW", 7), rec("HIGH", 9)])
    assert [p["ticker"] for p in picks] == ["HIGH", "LOW"]
