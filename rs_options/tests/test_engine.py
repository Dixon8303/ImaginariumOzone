"""Gate-stack tests. Spec §5–§8, §35–§38, §81–§82."""
from datetime import date

from rs_options_risk import (AccountState, AccountType, DataIntegrity,
                             DecisionStatus, LatencySample, LatencyState,
                             MacroState, Mode, OptionQuote,
                             ProbabilityEstimate, Right, RiskEngine)

from conftest import make_account, make_candidate


def test_happy_path_authorizes(calibrated_engine):
    decision = calibrated_engine.evaluate(make_candidate(), make_account(),
                                          mode=Mode.PAPER)
    assert decision.status is DecisionStatus.AUTHORIZE
    assert decision.quantity >= 1
    assert decision.total_risk <= decision.risk_budget
    assert "ALL_GATES_PASSED" in decision.reasons


def test_data_integrity_fails_closed(calibrated_engine):
    candidate = make_candidate(integrity=DataIntegrity(quotes_fresh=False))
    decision = calibrated_engine.evaluate(candidate, make_account())
    assert decision.status is DecisionStatus.REJECT
    assert "DATA_INTEGRITY" in decision.reasons


def test_broker_health_rejects(calibrated_engine):
    candidate = make_candidate(integrity=DataIntegrity(broker_healthy=False))
    decision = calibrated_engine.evaluate(candidate, make_account())
    assert decision.status is DecisionStatus.REJECT
    assert "BROKER_HEALTH" in decision.reasons


def test_portfolio_drawdown_freezes(calibrated_engine):
    account = make_account(equity=89_000.0, peak_equity=100_000.0)
    decision = calibrated_engine.evaluate(make_candidate(), account)
    assert decision.status is DecisionStatus.FREEZE
    assert "PORTFOLIO_DRAWDOWN" in decision.reasons


def test_daily_loss_halts(calibrated_engine):
    account = make_account(equity=96_500.0, peak_equity=100_000.0,
                           start_of_day_equity=100_000.0)
    decision = calibrated_engine.evaluate(make_candidate(), account)
    assert decision.status is DecisionStatus.HALT
    assert "DAILY_LOSS" in decision.reasons


def test_macro_hard_block_rejects(calibrated_engine):
    candidate = make_candidate(macro=MacroState(hard_block=True, label="CPI"))
    decision = calibrated_engine.evaluate(candidate, make_account())
    assert decision.status is DecisionStatus.REJECT
    assert "MACRO_EVENT" in decision.reasons


def test_max_open_positions_rejects(calibrated_engine):
    account = make_account(open_positions=5)
    decision = calibrated_engine.evaluate(make_candidate(), account)
    assert decision.status is DecisionStatus.REJECT
    assert "MAX_OPEN_POSITIONS" in decision.reasons


def test_risk_limit_rejects_when_one_contract_exceeds_budget(calibrated_engine):
    account = make_account(equity=5_000.0, start_of_day_equity=5_000.0,
                           peak_equity=5_000.0, buying_power=10_000.0)
    decision = calibrated_engine.evaluate(make_candidate(), account)
    assert decision.status is DecisionStatus.REJECT
    assert "RISK_LIMIT" in decision.reasons


def test_underlying_exposure_cap_limits_quantity(calibrated_engine):
    account = make_account(
        underlying_exposure={"NVDA": 4_900.0}   # 5% cap on 100k = 5,000
    )
    decision = calibrated_engine.evaluate(make_candidate(), account)
    assert decision.status is DecisionStatus.REJECT
    assert "NO_VALID_QUANTITY" in decision.reasons


def test_cluster_exposure_cap_limits_quantity(calibrated_engine):
    account = make_account(
        cluster_exposure={"semis": 9_950.0}     # 10% cap on 100k = 10,000
    )
    decision = calibrated_engine.evaluate(make_candidate(), account)
    assert decision.status is DecisionStatus.REJECT
    assert "NO_VALID_QUANTITY" in decision.reasons


def test_insufficient_edge_score_rejects(calibrated_engine):
    candidate = make_candidate(opportunity_score=4)
    decision = calibrated_engine.evaluate(candidate, make_account())
    assert decision.status is DecisionStatus.REJECT
    assert "INSUFFICIENT_EDGE_SCORE" in decision.reasons


def test_negative_ev_rejects(calibrated_engine):
    candidate = make_candidate(
        probability=ProbabilityEstimate(p_win=0.30, avg_win_r=1.0, avg_loss_r=1.0)
    )
    decision = calibrated_engine.evaluate(candidate, make_account())
    assert decision.status is DecisionStatus.REJECT
    assert "INSUFFICIENT_EDGE_EV" in decision.reasons


def test_uncalibrated_latency_forces_shadow_in_production():
    engine = RiskEngine()   # no latency samples → RED (fail closed)
    decision = engine.evaluate(make_candidate(), make_account(),
                               mode=Mode.PRODUCTION)
    assert decision.status is not DecisionStatus.AUTHORIZE
    if decision.authorized:
        assert decision.status is DecisionStatus.FORCE_SHADOW


def test_latency_black_halts(calibrated_engine):
    calibrated_engine.latency.record(
        LatencySample(ts=61.0, data_age_ms=120.0, order_rtt_ms=180.0,
                      heartbeat_gap_ms=20_000.0)
    )
    decision = calibrated_engine.evaluate(make_candidate(), make_account())
    assert decision.status is DecisionStatus.HALT
    assert "LATENCY_BLACK" in decision.reasons


def test_wash_sale_year_end_hard_blocks(calibrated_engine):
    calibrated_engine.tax_ledger.record_realized_loss(
        "NVDA", date(2026, 11, 20), 800.0
    )
    candidate = make_candidate(trade_date=date(2026, 12, 5))
    decision = calibrated_engine.evaluate(candidate, make_account())
    assert decision.status is DecisionStatus.REJECT
    assert "WASH_SALE_YEAR_END" in decision.reasons


def test_telemetry_shape(calibrated_engine):
    decision = calibrated_engine.evaluate(make_candidate(), make_account())
    t = decision.to_telemetry()
    for block in ("Decision", "Risk", "Scenarios", "Scoring",
                  "Margin_Impact", "Tax", "Latency"):
        assert block in t
    assert len(t["Scenarios"]) == 5
