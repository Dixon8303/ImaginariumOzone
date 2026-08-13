"""Session-start canary suite. Spec §61 ("Session-Start Self-Test").

Synthetic candidates that MUST be rejected are pushed through the gate
stack before each session. Any canary that comes back authorized means
the brakes are broken → caller must trigger a Level 0 halt.

State-dependent gates (drawdown, daily loss, GFV, PDT, risk limit,
integrity, macro, edge) run against the live engine. The wash-sale
canary runs against a config-identical clone with a seeded ledger so the
live ledger is never polluted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .engine import RiskEngine
from .models import (AccountState, AccountType, DataIntegrity, MacroState,
                     Mode, OptionQuote, ProbabilityEstimate, Right,
                     Settlement, TradeCandidate, UnderlyingContext)
from .tax import WashSaleLedger


@dataclass
class CanaryResult:
    name: str
    expected: str
    status: str
    reasons: list
    ok: bool          # True = correctly NOT authorized


@dataclass
class CanaryReport:
    ok: bool
    results: list = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"CANARY SUITE: {'PASS' if self.ok else 'FAIL — LEVEL 0 HALT REQUIRED'}"]
        for r in self.results:
            mark = "ok " if r.ok else "FAIL"
            lines.append(f"  [{mark}] {r.name:<24} -> {r.status} {r.reasons}")
        return "\n".join(lines)


def _candidate(today: date, **kw) -> TradeCandidate:
    base = dict(
        underlying=UnderlyingContext(ticker="_CANARY_", price=100.0),
        option=OptionQuote(right=Right.CALL, strike=100.0, dte_days=14.0,
                           bid=2.90, ask=3.10, iv=0.35),
        setup_id="CANARY",
        invalidation_price=97.5,
        expected_hold_minutes=90.0,
        trade_date=today,
        opportunity_score=10,
        probability=ProbabilityEstimate(p_win=0.55, avg_win_r=2.0, avg_loss_r=1.0),
    )
    base.update(kw)
    return TradeCandidate(**base)


def _account(**kw) -> AccountState:
    base = dict(
        equity=100_000.0, start_of_day_equity=100_000.0, peak_equity=100_000.0,
        account_type=AccountType.MARGIN, buying_power=200_000.0,
        open_positions=0, open_risk_dollars=0.0,
    )
    base.update(kw)
    return AccountState(**base)


def run_canary_suite(engine: RiskEngine, today: date,
                     mode: Mode = Mode.PAPER) -> CanaryReport:
    cases = []

    cases.append(("DATA_INTEGRITY", engine,
                  _candidate(today, integrity=DataIntegrity(quotes_fresh=False)),
                  _account()))
    cases.append(("MACRO_HARD_BLOCK", engine,
                  _candidate(today, macro=MacroState(hard_block=True, label="CPI")),
                  _account()))
    cases.append(("RISK_LIMIT", engine, _candidate(today),
                  _account(equity=5_000.0, start_of_day_equity=5_000.0,
                           peak_equity=5_000.0)))
    cases.append(("PORTFOLIO_DRAWDOWN", engine, _candidate(today),
                  _account(equity=89_000.0, start_of_day_equity=90_000.0)))
    cases.append(("DAILY_LOSS", engine, _candidate(today),
                  _account(equity=96_500.0)))
    cases.append(("GFV_RISK", engine, _candidate(today, is_day_trade=True),
                  _account(account_type=AccountType.CASH, settled_cash=200.0,
                           pending_settlements=[Settlement(today, 50_000.0)])))
    cases.append(("PDT_LIMIT", engine, _candidate(today, is_day_trade=True),
                  _account(equity=20_000.0, start_of_day_equity=20_000.0,
                           peak_equity=20_000.0, buying_power=40_000.0,
                           day_trades_used_5d=3)))
    cases.append(("INSUFFICIENT_EDGE", engine,
                  _candidate(today, opportunity_score=2, probability=None),
                  _account()))
    cases.append(("EDGE_FASTER_THAN_PIPE", engine,
                  _candidate(today, edge_half_life_seconds=0.001),
                  _account()))

    # Wash-sale year-end canary: config-identical clone with seeded ledger.
    seeded = WashSaleLedger(engine.tax_ledger.cfg)
    dec10 = date(today.year, 12, 10)
    seeded.record_realized_loss("_CANARY_", date(today.year, 12, 1), 500.0)
    clone = RiskEngine(risk=engine.risk, scenario=engine.scenario_cfg,
                       gates=engine.gates, margin_engine=engine.margin_engine,
                       tax_ledger=seeded, latency_monitor=engine.latency)
    cases.append(("WASH_SALE_YEAR_END", clone, _candidate(dec10), _account()))

    results = []
    for name, eng, cand, acct in cases:
        decision = eng.evaluate(cand, acct, mode=mode)
        results.append(CanaryResult(
            name=name,
            expected="NOT AUTHORIZED",
            status=decision.status.value,
            reasons=list(decision.reasons),
            ok=not decision.authorized,
        ))

    return CanaryReport(ok=all(r.ok for r in results), results=results)
