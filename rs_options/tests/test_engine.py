"""Tests for the foundational Risk Engine (spec v2.1)."""
import math
from datetime import date, timedelta

import pytest

from rs_options_risk import (AccountState, AccountType, DataIntegrity,
                             DecisionStatus, GateConfig, LatencySample,
                             LatencyState, MacroState, Mode, OptionQuote,
                             ProbabilityEstimate, Right, RiskEngine, Settlement,
                             SkewState, StrikeIV, TaxConfig, TradeCandidate,
                             UnderlyingContext, WashSaleLedger, bs_price,
                             classify_skew, scenario_grid, skew_metrics,
                             worst_case)
from rs_options_risk.config import ScenarioConfig

JULY = date(2026, 7, 15)


# ---------------------------------------------------------------- fixtures
def make_option(**kw):
    base = dict(right=Right.CALL, strike=100.0, dte_days=14.0,
                bid=2.90, ask=3.10, iv=0.35)
    base.update(kw)
    return OptionQuote(**base)


def make_candidate(**kw):
    base = dict(
        underlying=UnderlyingContext(ticker="TCKR", price=100.0, cluster="tech"),
        option=make_option(),
        setup_id="RS-01",
        invalidation_price=97.5,
        expected_hold_minutes=90.0,
        trade_date=JULY,
        opportunity_score=8,
        probability=ProbabilityEstimate(p_win=0.45, avg_win_r=1.8, avg_loss_r=1.0),
    )
    base.update(kw)
    return TradeCandidate(**base)


def make_account(**kw):
    base = dict(
        equity=100_000.0, start_of_day_equity=100_000.0, peak_equity=100_000.0,
        account_type=AccountType.MARGIN, buying_power=200_000.0,
        day_trades_used_5d=0, open_positions=1, open_risk_dollars=500.0,
    )
    base.update(kw)
    return AccountState(**base)


def warm(engine, n=40, age=100.0, rtt=150.0):
    for i in range(n):
        engine.latency.record(LatencySample(ts=float(i), data_age_ms=age,
                                            order_rtt_ms=rtt))


def green_engine(**kw):
    e = RiskEngine(**kw)
    warm(e)
    return e


# ------------------------------------------------------------ pricing model
def test_put_call_parity():
    s, k, t, r, iv = 100.0, 95.0, 30 / 365, 0.04, 0.30
    c = bs_price(Right.CALL, s, k, t, iv, r)
    p = bs_price(Right.PUT, s, k, t, iv, r)
    assert abs((c - p) - (s - k * math.exp(-r * t))) < 1e-9


def test_scenario_grid_all_lose_and_stress_exceeds_base():
    scen = scenario_grid(make_candidate(), ScenarioConfig())
    names = [s.name for s in scen]
    assert names[0] == "BASE" and len(scen) == 5
    assert all(s.pnl_per_contract < 0 for s in scen)
    base = scen[0].pnl_per_contract
    assert worst_case(scen).pnl_per_contract <= base


# ------------------------------------------------------------ sizing (§7)
def test_authorize_and_sizing_within_budget():
    d = green_engine().evaluate(make_candidate(), make_account(), Mode.PAPER)
    assert d.status is DecisionStatus.AUTHORIZE, d.reasons
    assert d.quantity >= 1
    assert d.quantity * d.risk_per_contract <= d.risk_budget + 1e-9
    assert d.total_risk <= 0.01 * 100_000 + 1e-9


def test_reject_when_one_contract_exceeds_budget():
    acct = make_account(equity=5_000.0, start_of_day_equity=5_000.0,
                        peak_equity=5_000.0)
    d = green_engine().evaluate(make_candidate(), acct, Mode.PAPER)
    assert d.status is DecisionStatus.REJECT and "RISK_LIMIT" in d.reasons


def test_underlying_exposure_cap_blocks():
    acct = make_account(underlying_exposure={"TCKR": 4_900.0})
    d = green_engine().evaluate(make_candidate(), acct, Mode.PAPER)
    assert d.status is DecisionStatus.REJECT and "NO_VALID_QUANTITY" in d.reasons


# ------------------------------------------- portfolio-level hard gates (§4)
def test_portfolio_drawdown_freeze():
    acct = make_account(equity=89_000.0, start_of_day_equity=90_000.0,
                        peak_equity=100_000.0)
    d = green_engine().evaluate(make_candidate(), acct, Mode.PAPER)
    assert d.status is DecisionStatus.FREEZE and "PORTFOLIO_DRAWDOWN" in d.reasons


def test_daily_loss_halt():
    acct = make_account(equity=96_900.0, start_of_day_equity=100_000.0,
                        peak_equity=100_000.0)
    d = green_engine().evaluate(make_candidate(), acct, Mode.PAPER)
    assert d.status is DecisionStatus.HALT and "DAILY_LOSS" in d.reasons


def test_data_integrity_fail_closed():
    cand = make_candidate(integrity=DataIntegrity(quotes_fresh=False))
    d = green_engine().evaluate(cand, make_account(), Mode.PAPER)
    assert d.status is DecisionStatus.REJECT and "DATA_INTEGRITY" in d.reasons


def test_macro_hard_block():
    cand = make_candidate(macro=MacroState(hard_block=True, label="CPI"))
    d = green_engine().evaluate(cand, make_account(), Mode.PAPER)
    assert d.status is DecisionStatus.REJECT and "MACRO_EVENT" in d.reasons


# --------------------------------------------------------------- margin (§8)
def test_cash_gfv_reject():
    acct = make_account(
        account_type=AccountType.CASH, settled_cash=500.0,
        pending_settlements=[Settlement(JULY + timedelta(days=1), 5_000.0)],
    )
    d = green_engine().evaluate(make_candidate(is_day_trade=True), acct, Mode.PAPER)
    assert d.status is DecisionStatus.REJECT and "GFV_RISK" in d.reasons
    assert d.margin.gfv_risk


def test_cash_insufficient_funds():
    acct = make_account(account_type=AccountType.CASH, settled_cash=500.0)
    d = green_engine().evaluate(make_candidate(), acct, Mode.PAPER)
    assert d.status is DecisionStatus.REJECT and "INSUFFICIENT_FUNDS" in d.reasons


def test_pdt_reject():
    acct = make_account(equity=20_000.0, start_of_day_equity=20_000.0,
                        peak_equity=20_000.0, buying_power=40_000.0,
                        day_trades_used_5d=3, open_risk_dollars=0.0)
    d = green_engine().evaluate(make_candidate(is_day_trade=True), acct, Mode.PAPER)
    assert d.status is DecisionStatus.REJECT and "PDT_LIMIT" in d.reasons
    assert d.margin.pdt_restricted


def test_margin_impact_recorded_on_authorize():
    d = green_engine().evaluate(make_candidate(), make_account(), Mode.PAPER)
    assert d.margin.ok
    assert d.margin.bp_after == pytest.approx(d.margin.bp_before - d.margin.bp_reduction)


# ------------------------------------------------------------- tax (§36)
def test_wash_sale_penalty_blocks_marginal_trade_and_flags_strong_one():
    ledger = WashSaleLedger()
    ledger.record_realized_loss("TCKR", JULY - timedelta(days=20), 800.0)
    eng = green_engine(tax_ledger=ledger)
    d = eng.evaluate(make_candidate(opportunity_score=8), make_account(), Mode.PAPER)
    assert d.status is DecisionStatus.REJECT and "INSUFFICIENT_EDGE_SCORE" in d.reasons
    assert d.tax.flagged and d.tax.penalty == 2

    d2 = eng.evaluate(make_candidate(opportunity_score=10), make_account(), Mode.PAPER)
    assert d2.status is DecisionStatus.AUTHORIZE and "WASH_SALE_FLAG" in d2.reasons


def test_wash_sale_december_hard_block():
    dec = date(2026, 12, 10)
    ledger = WashSaleLedger()
    ledger.record_realized_loss("TCKR", date(2026, 12, 1), 500.0)
    d = green_engine(tax_ledger=ledger).evaluate(
        make_candidate(trade_date=dec, opportunity_score=10),
        make_account(), Mode.PAPER)
    assert d.status is DecisionStatus.REJECT and "WASH_SALE_YEAR_END" in d.reasons
    assert d.tax.window == "hard_block"


def test_q4_escalated_penalty():
    oct15 = date(2026, 10, 15)
    ledger = WashSaleLedger()
    ledger.record_realized_loss("TCKR", oct15 - timedelta(days=10), 300.0)
    a = ledger.assess("TCKR", oct15)
    assert a.flagged and a.penalty == 4 and not a.hard_block


def test_mtm_475f_bypasses_wash_gate():
    ledger = WashSaleLedger(TaxConfig(profile="mtm_475f"))
    ledger.record_realized_loss("TCKR", date(2026, 12, 1), 500.0)
    d = green_engine(tax_ledger=ledger).evaluate(
        make_candidate(trade_date=date(2026, 12, 10)), make_account(), Mode.PAPER)
    assert d.status is DecisionStatus.AUTHORIZE
    assert not d.tax.flagged


# --------------------------------------------------------- latency (§38)
def test_uncalibrated_monitor_forces_shadow_in_production():
    d = RiskEngine().evaluate(make_candidate(), make_account(), Mode.PRODUCTION)
    assert d.status is DecisionStatus.FORCE_SHADOW
    assert d.mode is Mode.SHADOW
    assert "LATENCY_RED_SHADOW_REVERT" in d.reasons


def test_latency_red_forces_shadow_in_production():
    eng = RiskEngine()
    warm(eng, rtt=900.0)
    d = eng.evaluate(make_candidate(), make_account(), Mode.PRODUCTION)
    assert d.latency_state is LatencyState.RED
    assert d.status is DecisionStatus.FORCE_SHADOW and d.mode is Mode.SHADOW


def test_latency_black_halts():
    eng = RiskEngine()
    eng.latency.record(LatencySample(ts=0.0, data_age_ms=50, order_rtt_ms=50,
                                     clock_skew_ms=500.0))
    d = eng.evaluate(make_candidate(), make_account(), Mode.PAPER)
    assert d.status is DecisionStatus.HALT and "LATENCY_BLACK" in d.reasons


def test_latency_yellow_halves_size_and_raises_bar():
    base_q = green_engine().evaluate(
        make_candidate(opportunity_score=9), make_account(), Mode.PAPER).quantity

    eng = RiskEngine()
    warm(eng, rtt=500.0)                      # YELLOW band
    d = eng.evaluate(make_candidate(opportunity_score=9), make_account(), Mode.PAPER)
    assert d.latency_state is LatencyState.YELLOW
    assert d.status is DecisionStatus.AUTHORIZE
    assert "LATENCY_YELLOW_DEGRADE" in d.reasons
    assert d.quantity == max(1, math.floor(base_q * 0.5))

    d2 = eng.evaluate(make_candidate(opportunity_score=8), make_account(), Mode.PAPER)
    assert d2.status is DecisionStatus.REJECT   # 8 − 1 penalty < required 8


def test_latency_hysteresis_recovery():
    eng = RiskEngine()
    warm(eng, rtt=900.0)
    assert eng.latency.state(now=1_000.0) is LatencyState.RED
    warm(eng, n=200, rtt=100.0)               # flush window with clean samples
    assert eng.latency.state(now=1_100.0) is LatencyState.YELLOW   # inside re-arm window
    assert eng.latency.state(now=2_000.0) is LatencyState.GREEN    # sustained recovery


# ------------------------------------------------------------- skew (§25)
def test_skew_overlay_penalizes_bullish_thesis():
    cand = make_candidate(
        underlying=UnderlyingContext(ticker="TCKR", price=100.0, cluster="tech",
                                     index_skew_state=SkewState.STEEP_PUT_SKEW))
    d = green_engine().evaluate(cand, make_account(), Mode.PAPER)
    assert d.status is DecisionStatus.REJECT
    assert "SKEW_HEDGING_OVERLAY" in d.reasons and "INSUFFICIENT_EDGE_SCORE" in d.reasons

    cand10 = make_candidate(
        opportunity_score=10,
        underlying=UnderlyingContext(ticker="TCKR", price=100.0, cluster="tech",
                                     index_skew_state=SkewState.STEEP_PUT_SKEW))
    d2 = green_engine().evaluate(cand10, make_account(), Mode.PAPER)
    assert d2.status is DecisionStatus.AUTHORIZE


def test_skew_metrics_and_classification():
    chain = [
        StrikeIV(-0.50, 0.30), StrikeIV(-0.25, 0.36), StrikeIV(-0.10, 0.42),
        StrikeIV(0.10, 0.26), StrikeIV(0.25, 0.28), StrikeIV(0.50, 0.30),
    ]
    m = skew_metrics(chain)
    assert m.rr25 == pytest.approx(0.28 - 0.36)
    assert m.rr25 < 0
    history = [-0.02, -0.01, -0.015, -0.03, -0.025] * 20
    assert classify_skew(m.rr25, history) in (SkewState.STEEP_PUT_SKEW,
                                              SkewState.EXTREME_PUT_SKEW)


# ------------------------------------------------------------ telemetry (§62)
def test_decision_telemetry_shape():
    d = green_engine().evaluate(make_candidate(), make_account(), Mode.PAPER)
    t = d.to_telemetry()
    assert t["Decision"]["Status"] == "AUTHORIZE"
    assert t["Risk"]["Contract_Quantity"] == d.quantity
    assert t["Margin_Impact"]["GFV_Risk"] is False
    assert t["Tax"]["Wash_Sale_Flag"] is False
    assert t["Latency"]["Latency_State"] == "green"
    assert len(t["Scenarios"]) == 5
