"""Foundational Risk Engine — gate composition. Spec §5–§8, §35–§38, §81–§82.

ABSOLUTE PRODUCTION RULE (§82): nothing overrides this engine. If risk
says NO, the system says NO. Fail closed on uncertainty (LAW 18).
"""
from __future__ import annotations

import math

from .config import (GateConfig, HardRiskConstants, LatencyConfig,
                     MarginConfig, ScenarioConfig, TaxConfig)
from .latency import LatencyMonitor
from .margin import MarginEngine
from .models import (AccountState, DecisionStatus, LatencyState, Mode,
                     RiskDecision, SkewState, TradeCandidate)
from .scenario import scenario_grid, worst_case
from .tax import WashSaleLedger

_BEARISH_SKEW = (SkewState.STEEP_PUT_SKEW, SkewState.EXTREME_PUT_SKEW)


class RiskEngine:
    def __init__(self,
                 risk: HardRiskConstants | None = None,
                 scenario: ScenarioConfig | None = None,
                 gates: GateConfig | None = None,
                 margin_cfg: MarginConfig | None = None,
                 tax_cfg: TaxConfig | None = None,
                 latency_cfg: LatencyConfig | None = None,
                 margin_engine: MarginEngine | None = None,
                 tax_ledger: WashSaleLedger | None = None,
                 latency_monitor: LatencyMonitor | None = None):
        self.risk = risk or HardRiskConstants()
        self.scenario_cfg = scenario or ScenarioConfig()
        self.gates = gates or GateConfig()
        self.margin_engine = margin_engine or MarginEngine(margin_cfg)
        self.tax_ledger = tax_ledger or WashSaleLedger(tax_cfg)
        self.latency = latency_monitor or LatencyMonitor(latency_cfg)

    # ------------------------------------------------------------------
    def evaluate(self, candidate: TradeCandidate, account: AccountState,
                 mode: Mode = Mode.PAPER, now: float | None = None) -> RiskDecision:
        d = RiskDecision(status=DecisionStatus.REJECT, mode=mode)

        # ── fail-closed preconditions ────────────────────────────────
        if not candidate.integrity.ok():
            return self._final(d, DecisionStatus.REJECT, "DATA_INTEGRITY")
        if not candidate.integrity.broker_healthy:
            return self._final(d, DecisionStatus.REJECT, "BROKER_HEALTH")

        lat = self.latency.state(now)
        d.latency_state = lat
        if lat is LatencyState.BLACK:
            return self._final(d, DecisionStatus.HALT, "LATENCY_BLACK")
        forced_shadow = (lat is LatencyState.RED and mode is Mode.PRODUCTION)
        if lat is LatencyState.RED and mode is Mode.PRODUCTION:
            d.mode = Mode.SHADOW
            d.reasons.append("LATENCY_RED_SHADOW_REVERT")

        if account.peak_equity > 0:
            drawdown = (account.peak_equity - account.equity) / account.peak_equity
            if drawdown >= self.risk.max_portfolio_drawdown_pct:
                return self._final(d, DecisionStatus.FREEZE, "PORTFOLIO_DRAWDOWN")

        if account.start_of_day_equity > 0:
            daily_loss = ((account.start_of_day_equity - account.equity)
                          / account.start_of_day_equity)
            if daily_loss >= self.risk.daily_loss_limit_pct:
                return self._final(d, DecisionStatus.HALT, "DAILY_LOSS")

        if candidate.macro.hard_block:
            return self._final(d, DecisionStatus.REJECT, "MACRO_EVENT")

        if account.open_positions >= self.risk.max_open_positions:
            return self._final(d, DecisionStatus.REJECT, "MAX_OPEN_POSITIONS")

        # ── scenario risk (§6) ───────────────────────────────────────
        scenarios = scenario_grid(candidate, self.scenario_cfg)
        d.scenarios = scenarios
        worst = worst_case(scenarios)
        d.worst_case_scenario = worst.name
        worst_loss = -worst.pnl_per_contract
        if worst_loss <= 0:
            # A model that cannot lose is a broken model → fail closed.
            return self._final(d, DecisionStatus.REJECT, "SCENARIO_MODEL_INVALID")

        q = candidate.option
        slippage = self.scenario_cfg.slippage_spread_fraction * q.spread * q.multiplier
        fees = self.scenario_cfg.fees_per_contract_roundtrip
        risk_per_contract = worst_loss + slippage + fees
        d.risk_per_contract = risk_per_contract

        # ── position sizing (§7) ─────────────────────────────────────
        budget = account.equity * self.risk.max_trade_risk_pct
        d.risk_budget = budget
        if risk_per_contract > budget:
            return self._final(d, DecisionStatus.REJECT, "RISK_LIMIT")

        contracts = math.floor(budget / risk_per_contract)
        contracts = min(contracts, self.risk.max_contracts_per_trade)

        entry = q.mid + self.scenario_cfg.entry_spread_fraction * q.half_spread
        cost_per_contract = entry * q.multiplier

        # Exposure caps (§4, §78): reduce quantity to fit; 0 → reject.
        ticker = candidate.underlying.ticker
        room_underlying = (self.risk.max_single_underlying_exposure_pct
                           * account.equity
                           - account.underlying_exposure.get(ticker, 0.0))
        contracts = min(contracts, self._fit(room_underlying, cost_per_contract))

        cluster = candidate.underlying.cluster
        if cluster:
            room_cluster = (self.risk.max_cluster_exposure_pct * account.equity
                            - account.cluster_exposure.get(cluster, 0.0))
            contracts = min(contracts, self._fit(room_cluster, cost_per_contract))

        room_concurrent = (self.risk.max_concurrent_risk_pct * account.equity
                           - account.open_risk_dollars)
        contracts = min(contracts, self._fit(room_concurrent, risk_per_contract))

        if contracts < 1:
            return self._final(d, DecisionStatus.REJECT, "NO_VALID_QUANTITY")

        # ── margin / buying power (§8) ───────────────────────────────
        total_cost = contracts * (cost_per_contract + fees)
        margin = self.margin_engine.evaluate(
            account, total_cost,
            is_day_trade=candidate.is_day_trade,
            holds_overnight=candidate.holds_overnight,
        )
        d.margin = margin
        if not margin.ok:
            return self._final(d, DecisionStatus.REJECT, *margin.reasons)

        # ── wash sale / tax (§36) ────────────────────────────────────
        tax = self.tax_ledger.assess(candidate.wash_sale_group, candidate.trade_date)
        d.tax = tax
        if tax.hard_block:
            return self._final(d, DecisionStatus.REJECT, "WASH_SALE_YEAR_END")

        # ── expectancy & scoring (§30, §32, §34) ─────────────────────
        penalty = candidate.base_risk_penalty + tax.penalty
        if (candidate.thesis_bullish
                and candidate.underlying.index_skew_state in _BEARISH_SKEW):
            penalty += self.gates.skew_overlay_penalty
            d.reasons.append("SKEW_HEDGING_OVERLAY")
        if lat is LatencyState.YELLOW:
            penalty += self.gates.latency_yellow_penalty

        net_score = candidate.opportunity_score - penalty
        d.net_score = net_score

        ev_r = None
        if candidate.probability is not None:
            p = candidate.probability
            friction_r = (slippage + fees) / risk_per_contract
            ev_r = (p.p_win * p.avg_win_r
                    - (1.0 - p.p_win) * p.avg_loss_r
                    - friction_r)
        d.ev_r = ev_r

        required = self.gates.min_net_score
        if lat is LatencyState.YELLOW:
            required += self.gates.yellow_score_add
            contracts = max(1, math.floor(contracts * self.gates.yellow_size_mult))
            d.reasons.append("LATENCY_YELLOW_DEGRADE")

        if net_score < required:
            return self._final(d, DecisionStatus.REJECT, "INSUFFICIENT_EDGE_SCORE")
        if ev_r is not None and ev_r < self.gates.min_expected_value_r:
            return self._final(d, DecisionStatus.REJECT, "INSUFFICIENT_EDGE_EV")

        # ── authorize ────────────────────────────────────────────────
        d.quantity = contracts
        d.total_risk = contracts * risk_per_contract
        if tax.flagged:
            d.reasons.append("WASH_SALE_FLAG")
        status = DecisionStatus.FORCE_SHADOW if forced_shadow else DecisionStatus.AUTHORIZE
        return self._final(d, status, "ALL_GATES_PASSED")

    # ------------------------------------------------------------------
    @staticmethod
    def _fit(room_dollars: float, unit_cost: float) -> int:
        if unit_cost <= 0:
            return 0
        return max(0, math.floor(room_dollars / unit_cost))

    @staticmethod
    def _final(d: RiskDecision, status: DecisionStatus, *reasons: str) -> RiskDecision:
        d.status = status
        d.reasons.extend(reasons)
        return d
