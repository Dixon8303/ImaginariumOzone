import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rs_options_risk import (AccountState, AccountType, LatencySample,
                             OptionQuote, ProbabilityEstimate, Right,
                             RiskEngine, TradeCandidate, UnderlyingContext)


def make_candidate(**overrides) -> TradeCandidate:
    defaults = dict(
        underlying=UnderlyingContext(ticker="NVDA", price=100.0, cluster="semis"),
        option=OptionQuote(right=Right.CALL, strike=100.0, dte_days=14.0,
                           bid=2.90, ask=3.10, iv=0.35),
        setup_id="RS-02",
        invalidation_price=97.5,
        expected_hold_minutes=90.0,
        trade_date=date(2026, 6, 15),
        opportunity_score=8,
        probability=ProbabilityEstimate(p_win=0.45, avg_win_r=1.8, avg_loss_r=1.0),
    )
    defaults.update(overrides)
    return TradeCandidate(**defaults)


def make_account(**overrides) -> AccountState:
    defaults = dict(
        equity=100_000.0,
        start_of_day_equity=100_000.0,
        peak_equity=100_000.0,
        account_type=AccountType.MARGIN,
        buying_power=200_000.0,
        open_positions=1,
        open_risk_dollars=500.0,
    )
    defaults.update(overrides)
    return AccountState(**defaults)


@pytest.fixture
def calibrated_engine() -> RiskEngine:
    engine = RiskEngine()
    for i in range(60):
        engine.latency.record(
            LatencySample(ts=float(i), data_age_ms=120.0, order_rtt_ms=180.0)
        )
    return engine
