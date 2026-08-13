"""Core domain objects. Spec: §6–§9, §35, §62 (telemetry shapes)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class AccountType(str, Enum):
    CASH = "cash"
    MARGIN = "margin"
    PORTFOLIO_MARGIN = "portfolio_margin"


class TaxProfile(str, Enum):
    TAXABLE = "taxable"
    MTM_475F = "mtm_475f"
    IRA = "ira"


class LatencyState(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    BLACK = "black"


class Right(str, Enum):
    CALL = "call"
    PUT = "put"


class Mode(str, Enum):
    RESEARCH = "research"
    PAPER = "paper"
    SHADOW = "shadow"
    PRODUCTION = "production"


class DecisionStatus(str, Enum):
    AUTHORIZE = "AUTHORIZE"
    FORCE_SHADOW = "FORCE_SHADOW"   # authorized signal, live transmission barred (§38)
    REJECT = "REJECT"
    FREEZE = "FREEZE"
    HALT = "HALT"


class SkewState(str, Enum):
    CALL_SKEW = "call_skew"
    FLAT = "flat"
    NORMAL_PUT_SKEW = "normal_put_skew"
    STEEP_PUT_SKEW = "steep_put_skew"
    EXTREME_PUT_SKEW = "extreme_put_skew"


@dataclass
class OptionQuote:
    right: Right
    strike: float
    dte_days: float
    bid: float
    ask: float
    iv: float                     # decimal, e.g. 0.35
    multiplier: int = 100

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float:
        return max(self.ask - self.bid, 0.0)

    @property
    def half_spread(self) -> float:
        return self.spread / 2.0

    @property
    def spread_pct(self) -> float:
        return self.spread / self.mid if self.mid > 0 else float("inf")


@dataclass
class UnderlyingContext:
    ticker: str
    price: float
    cluster: str = ""                        # §78 correlated-cluster key
    index_skew_state: SkewState = SkewState.NORMAL_PUT_SKEW  # §25 regime overlay


@dataclass
class Settlement:
    settle_date: date
    amount: float


@dataclass
class AccountState:
    equity: float
    start_of_day_equity: float
    peak_equity: float
    account_type: AccountType
    buying_power: float = 0.0                # broker-style BP (margin accounts)
    settled_cash: float = 0.0                # cash accounts
    pending_settlements: list = field(default_factory=list)   # [Settlement]
    day_trades_used_5d: int = 0
    open_positions: int = 0
    open_risk_dollars: float = 0.0
    underlying_exposure: dict = field(default_factory=dict)   # ticker -> $ premium
    cluster_exposure: dict = field(default_factory=dict)      # cluster -> $ premium

    @property
    def unsettled_total(self) -> float:
        return sum(s.amount for s in self.pending_settlements)


@dataclass
class MacroState:
    hard_block: bool = False
    label: str = ""


@dataclass
class DataIntegrity:
    quotes_fresh: bool = True
    chain_valid: bool = True
    greeks_available: bool = True
    broker_healthy: bool = True
    clock_ok: bool = True

    def ok(self) -> bool:
        return all((self.quotes_fresh, self.chain_valid,
                    self.greeks_available, self.clock_ok))


@dataclass
class ProbabilityEstimate:
    """Conditional estimates (§29) — sample/model-conditioned, not universal."""
    p_win: float
    avg_win_r: float
    avg_loss_r: float = 1.0


@dataclass
class TradeCandidate:
    underlying: UnderlyingContext
    option: OptionQuote
    setup_id: str
    invalidation_price: float
    expected_hold_minutes: float
    trade_date: date
    opportunity_score: int                    # 0-10 (§32)
    base_risk_penalty: int = 0                # §34 (macro/liquidity/etc.)
    probability: Optional[ProbabilityEstimate] = None
    macro: MacroState = field(default_factory=MacroState)
    integrity: DataIntegrity = field(default_factory=DataIntegrity)
    is_day_trade: bool = True
    holds_overnight: bool = False
    thesis_bullish: bool = True
    wash_sale_group: str = ""                 # defaults to ticker

    def __post_init__(self):
        if not self.wash_sale_group:
            self.wash_sale_group = self.underlying.ticker


@dataclass
class ScenarioResult:
    name: str
    underlying_price: float
    iv: float
    t_years: float
    exit_premium: float
    pnl_per_contract: float


@dataclass
class MarginImpact:
    ok: bool
    reasons: list
    account_type: AccountType
    bp_before: float
    bp_reduction: float
    bp_after: float
    overnight_maintenance_req: float
    settled_cash: float
    unsettled_proceeds: float
    gfv_risk: bool
    pdt_restricted: bool
    day_trades_used_5d: int


@dataclass
class TaxAssessment:
    profile: TaxProfile
    flagged: bool
    penalty: int
    hard_block: bool
    recent_loss: float
    window: str                # normal | escalation | hard_block


@dataclass
class LatencySample:
    ts: float                  # seconds (monotonic or epoch — injected, not read)
    data_age_ms: float
    order_rtt_ms: float
    heartbeat_gap_ms: float = 0.0
    clock_skew_ms: float = 0.0


@dataclass
class RiskDecision:
    status: DecisionStatus
    reasons: list = field(default_factory=list)
    mode: Optional[Mode] = None
    quantity: int = 0
    risk_budget: float = 0.0
    risk_per_contract: float = 0.0
    total_risk: float = 0.0
    worst_case_scenario: str = ""
    net_score: Optional[int] = None
    ev_r: Optional[float] = None
    scenarios: list = field(default_factory=list)
    margin: Optional[MarginImpact] = None
    tax: Optional[TaxAssessment] = None
    latency_state: Optional[LatencyState] = None

    @property
    def authorized(self) -> bool:
        return self.status in (DecisionStatus.AUTHORIZE, DecisionStatus.FORCE_SHADOW)

    def to_telemetry(self) -> dict:
        """Telemetry blocks per spec §62 (subset owned by the Risk Engine)."""
        return {
            "Decision": {
                "Status": self.status.value,
                "Reasons": list(self.reasons),
                "Mode": self.mode.value if self.mode else None,
            },
            "Risk": {
                "Risk_Budget": round(self.risk_budget, 2),
                "Risk_Per_Contract": round(self.risk_per_contract, 2),
                "Contract_Quantity": self.quantity,
                "Total_Risk": round(self.total_risk, 2),
                "Worst_Case_Scenario": self.worst_case_scenario,
            },
            "Scenarios": [
                {
                    "Name": s.name,
                    "Underlying": round(s.underlying_price, 4),
                    "IV": round(s.iv, 4),
                    "Exit_Premium": round(s.exit_premium, 4),
                    "PnL_Per_Contract": round(s.pnl_per_contract, 2),
                }
                for s in self.scenarios
            ],
            "Scoring": {
                "Net_Score": self.net_score,
                "Expected_Value_R": None if self.ev_r is None else round(self.ev_r, 4),
            },
            "Margin_Impact": None if self.margin is None else {
                "Account_Type": self.margin.account_type.value,
                "BP_Before": round(self.margin.bp_before, 2),
                "BP_Reduction": round(self.margin.bp_reduction, 2),
                "BP_After": round(self.margin.bp_after, 2),
                "Overnight_Maintenance_Req": round(self.margin.overnight_maintenance_req, 2),
                "Settled_Cash": round(self.margin.settled_cash, 2),
                "Unsettled_Proceeds": round(self.margin.unsettled_proceeds, 2),
                "Day_Trades_Used_5D": self.margin.day_trades_used_5d,
                "PDT_Restricted": self.margin.pdt_restricted,
                "GFV_Risk": self.margin.gfv_risk,
            },
            "Tax": None if self.tax is None else {
                "Tax_Profile": self.tax.profile.value,
                "Realized_Loss_30D": round(self.tax.recent_loss, 2),
                "Wash_Sale_Flag": self.tax.flagged,
                "Window": self.tax.window,
            },
            "Latency": {
                "Latency_State": self.latency_state.value if self.latency_state else None,
            },
        }
