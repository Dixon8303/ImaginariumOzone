"""Tests for v0.2 hardening: reconciler, edge-half-life gate, canaries,
rejection forensics. Spec v2.2 §8, §38, §61, §63."""
from datetime import date

from rs_options_risk import (BrokerReconciler, DecisionStatus, LatencySample,
                             Mode, RiskEngine, run_canary_suite)
from rs_options_risk.config import GateConfig
from tests.test_engine import green_engine, make_account, make_candidate, warm

TODAY = date(2026, 8, 13)


# ------------------------------------------------- broker reconciliation (§8)
def test_reconciler_effective_bp_is_lower_of_two():
    r = BrokerReconciler()
    assert r.effective_bp(50_000.0) == 50_000.0          # no broker read yet
    r.update(model_bp=50_000.0, broker_bp=42_000.0, ts=0.0, equity=100_000.0)
    assert r.effective_bp(50_000.0) == 42_000.0
    assert r.effective_bp(40_000.0) == 40_000.0


def test_reconciler_debounce_warn_then_halt():
    r = BrokerReconciler()
    eq = 100_000.0
    # tolerance = 2% of equity = 2,000; divergence 5,000 breaches
    assert r.update(50_000.0, 45_000.0, 1.0, eq) == BrokerReconciler.WARN
    assert r.update(50_000.0, 45_000.0, 2.0, eq) == BrokerReconciler.WARN
    assert r.update(50_000.0, 45_000.0, 3.0, eq) == BrokerReconciler.HALT


def test_reconciler_resets_on_agreement():
    r = BrokerReconciler()
    eq = 100_000.0
    r.update(50_000.0, 45_000.0, 1.0, eq)
    r.update(50_000.0, 45_000.0, 2.0, eq)
    assert r.update(50_000.0, 49_500.0, 3.0, eq) == BrokerReconciler.OK
    assert r.update(50_000.0, 45_000.0, 4.0, eq) == BrokerReconciler.WARN


def test_reconciler_stale_broker_data():
    r = BrokerReconciler()
    assert r.broker_data_stale(now=100.0)                 # never polled
    r.update(50_000.0, 50_000.0, ts=100.0, equity=100_000.0)
    assert not r.broker_data_stale(now=120.0)
    assert r.broker_data_stale(now=200.0)                 # > 30s default


# --------------------------------------------- latency class discipline (§38)
def test_edge_faster_than_pipe_rejected():
    # warm(): age=100, rtt=150 → pipe ≈ 250ms; required = 10× = 2.5s
    d = green_engine().evaluate(
        make_candidate(edge_half_life_seconds=1.0), make_account(), Mode.PAPER)
    assert d.status is DecisionStatus.REJECT
    assert "EDGE_FASTER_THAN_PIPE" in d.reasons


def test_slow_edge_passes_pipe_gate():
    d = green_engine().evaluate(
        make_candidate(edge_half_life_seconds=60.0), make_account(), Mode.PAPER)
    assert d.status is DecisionStatus.AUTHORIZE
    assert d.gate_margins["edge_half_life_margin_ms"] > 0


def test_declared_fast_edge_with_uncalibrated_pipe_fails_closed():
    d = RiskEngine().evaluate(
        make_candidate(edge_half_life_seconds=1.0), make_account(), Mode.PAPER)
    assert d.status is DecisionStatus.REJECT
    assert "EDGE_HALF_LIFE_UNVERIFIABLE" in d.reasons


# ------------------------------------------------------------- canaries (§61)
def test_canary_suite_passes_on_healthy_engine():
    report = run_canary_suite(RiskEngine(), TODAY)
    assert report.ok, report.summary()
    assert len(report.results) == 10
    assert all(r.ok for r in report.results)


def test_canary_suite_catches_broken_gates():
    # Sabotage the edge thresholds: the INSUFFICIENT_EDGE canary must slip
    # through and the suite must fail — proving canaries detect broken brakes.
    broken = RiskEngine(gates=GateConfig(min_net_score=-100,
                                         min_expected_value_r=-100.0))
    report = run_canary_suite(broken, TODAY)
    assert not report.ok
    failed = {r.name for r in report.results if not r.ok}
    assert "INSUFFICIENT_EDGE" in failed


# ------------------------------------------------- rejection forensics (§63)
def test_gate_margins_recorded_on_authorize():
    d = green_engine().evaluate(make_candidate(), make_account(), Mode.PAPER)
    gm = d.gate_margins
    assert gm["risk_headroom_per_contract"] > 0
    assert gm["score_margin"] >= 0
    assert gm["ev_margin_r"] >= 0
    assert gm["bp_headroom"] > 0
    assert "Gate_Margins" in d.to_telemetry()


def test_gate_margins_show_distance_on_rejection():
    d = green_engine().evaluate(
        make_candidate(opportunity_score=5), make_account(), Mode.PAPER)
    assert d.status is DecisionStatus.REJECT
    assert d.gate_margins["score_margin"] == -2.0         # 5 − required 7
