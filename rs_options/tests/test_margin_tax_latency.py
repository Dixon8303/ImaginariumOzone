"""Margin (§8), wash-sale/tax (§36), latency ladder (§38) unit tests."""
from datetime import date

from rs_options_risk import (AccountState, AccountType, LatencySample,
                             LatencyState, TaxProfile, WashSaleLedger)
from rs_options_risk.config import LatencyConfig, TaxConfig
from rs_options_risk.latency import LatencyMonitor
from rs_options_risk.margin import MarginEngine
from rs_options_risk.models import Settlement


def cash_account(settled=5_000.0, pending=None):
    return AccountState(
        equity=5_000.0, start_of_day_equity=5_000.0, peak_equity=5_000.0,
        account_type=AccountType.CASH, settled_cash=settled,
        pending_settlements=pending or [],
    )


# ---------------------------------------------------------------- margin
def test_cash_account_insufficient_funds():
    impact = MarginEngine().evaluate(cash_account(settled=100.0), 500.0,
                                     is_day_trade=True)
    assert not impact.ok
    assert "INSUFFICIENT_FUNDS" in impact.reasons


def test_cash_account_gfv_risk_on_unsettled_day_trade():
    pending = [Settlement(settle_date=date(2026, 6, 16), amount=400.0)]
    impact = MarginEngine().evaluate(cash_account(settled=200.0, pending=pending),
                                     500.0, is_day_trade=True)
    assert not impact.ok
    assert impact.gfv_risk
    assert "GFV_RISK" in impact.reasons


def test_pdt_limit_under_25k():
    account = AccountState(
        equity=10_000.0, start_of_day_equity=10_000.0, peak_equity=10_000.0,
        account_type=AccountType.MARGIN, buying_power=20_000.0,
        day_trades_used_5d=3,
    )
    impact = MarginEngine().evaluate(account, 500.0, is_day_trade=True)
    assert not impact.ok
    assert impact.pdt_restricted
    assert "PDT_LIMIT" in impact.reasons


def test_bp_buffer_breach():
    account = AccountState(
        equity=100_000.0, start_of_day_equity=100_000.0, peak_equity=100_000.0,
        account_type=AccountType.MARGIN, buying_power=6_000.0,
    )
    impact = MarginEngine().evaluate(account, 2_000.0, is_day_trade=False)
    assert not impact.ok
    assert "BP_BUFFER_BREACH" in impact.reasons


def test_broker_reconciliation_tolerance():
    engine = MarginEngine()
    assert engine.broker_reconciliation_ok(100_000.0, 101_000.0, 100_000.0)
    assert not engine.broker_reconciliation_ok(100_000.0, 105_000.0, 100_000.0)


# ------------------------------------------------------------------ tax
def test_no_loss_no_flag():
    ledger = WashSaleLedger()
    assessment = ledger.assess("NVDA", date(2026, 6, 15))
    assert not assessment.flagged
    assert assessment.penalty == 0


def test_recent_loss_flags_with_penalty():
    ledger = WashSaleLedger()
    ledger.record_realized_loss("NVDA", date(2026, 6, 1), 500.0)
    assessment = ledger.assess("NVDA", date(2026, 6, 15))
    assert assessment.flagged
    assert assessment.penalty == 2
    assert not assessment.hard_block


def test_loss_outside_lookback_ignored():
    ledger = WashSaleLedger()
    ledger.record_realized_loss("NVDA", date(2026, 1, 5), 500.0)
    assessment = ledger.assess("NVDA", date(2026, 6, 15))
    assert not assessment.flagged


def test_q4_escalation_penalty():
    ledger = WashSaleLedger()
    ledger.record_realized_loss("NVDA", date(2026, 10, 10), 500.0)
    assessment = ledger.assess("NVDA", date(2026, 10, 20))
    assert assessment.window == "escalation"
    assert assessment.penalty == 4


def test_year_end_hard_block():
    ledger = WashSaleLedger()
    ledger.record_realized_loss("NVDA", date(2026, 11, 25), 500.0)
    assessment = ledger.assess("NVDA", date(2026, 12, 10))
    assert assessment.hard_block


def test_mtm_475f_exempt():
    ledger = WashSaleLedger(TaxConfig(profile="mtm_475f"))
    ledger.record_realized_loss("NVDA", date(2026, 12, 1), 500.0)
    assessment = ledger.assess("NVDA", date(2026, 12, 10))
    assert not assessment.flagged
    assert not assessment.hard_block
    assert assessment.profile is TaxProfile.MTM_475F


# -------------------------------------------------------------- latency
def good_sample(ts):
    return LatencySample(ts=ts, data_age_ms=100.0, order_rtt_ms=150.0)


def test_uncalibrated_reports_red():
    monitor = LatencyMonitor()
    assert monitor.state() is LatencyState.RED


def test_calibrated_good_samples_green():
    monitor = LatencyMonitor()
    for i in range(60):
        monitor.record(good_sample(float(i)))
    assert monitor.state() is LatencyState.GREEN


def test_heartbeat_black_dominates():
    monitor = LatencyMonitor()
    monitor.record(LatencySample(ts=0.0, data_age_ms=100.0, order_rtt_ms=150.0,
                                 heartbeat_gap_ms=20_000.0))
    assert monitor.state() is LatencyState.BLACK


def test_hysteresis_withholds_green_after_breach():
    cfg = LatencyConfig(recovery_seconds=900.0)
    monitor = LatencyMonitor(cfg)
    for i in range(29):
        monitor.record(good_sample(float(i)))
    assert monitor.state(now=100.0) is LatencyState.RED       # uncalibrated breach
    monitor.record(good_sample(30.0))                          # now calibrated
    for i in range(31, 60):
        monitor.record(good_sample(float(i)))
    assert monitor.state(now=200.0) is LatencyState.YELLOW    # within re-arm window
    assert monitor.state(now=100.0 + 901.0) is LatencyState.GREEN
