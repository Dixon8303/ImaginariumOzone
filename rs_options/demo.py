#!/usr/bin/env python3
"""Demo: canary self-test, then one candidate through the full gate stack.
Spec §61, §81."""
import json
from datetime import date

from rs_options_risk import (AccountState, AccountType, LatencySample, Mode,
                             OptionQuote, ProbabilityEstimate, Right,
                             RiskEngine, TradeCandidate, UnderlyingContext,
                             run_canary_suite)

engine = RiskEngine()

# Session-start self-test: prove the brakes work before trading (§61).
report = run_canary_suite(engine, today=date(2026, 8, 13))
print(report.summary())
if not report.ok:
    raise SystemExit("LEVEL 0 HALT: gate stack failed canary suite")
print()

# Calibrate the latency ladder (normally fed by the telemetry engine).
for i in range(60):
    engine.latency.record(LatencySample(ts=float(i), data_age_ms=120.0,
                                        order_rtt_ms=180.0))

candidate = TradeCandidate(
    underlying=UnderlyingContext(ticker="NVDA", price=100.0, cluster="semis"),
    option=OptionQuote(right=Right.CALL, strike=100.0, dte_days=14.0,
                       bid=2.90, ask=3.10, iv=0.35),
    setup_id="RS-02",
    invalidation_price=97.5,
    expected_hold_minutes=90.0,
    trade_date=date(2026, 8, 13),
    opportunity_score=8,
    probability=ProbabilityEstimate(p_win=0.45, avg_win_r=1.8, avg_loss_r=1.0),
)

account = AccountState(
    equity=100_000.0, start_of_day_equity=100_000.0, peak_equity=100_000.0,
    account_type=AccountType.MARGIN, buying_power=200_000.0,
    open_positions=1, open_risk_dollars=500.0,
)

decision = engine.evaluate(candidate, account, mode=Mode.PAPER)
print(json.dumps(decision.to_telemetry(), indent=2))
