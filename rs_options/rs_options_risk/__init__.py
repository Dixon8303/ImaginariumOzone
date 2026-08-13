"""rs_options_risk — foundational Risk Engine for the RS Options Research &
Execution Engine spec v2.1.

Research-stage reference implementation. Long-premium structures only.
Every threshold marked CALIBRATE is a placeholder pending Paper/Shadow
validation (spec LAW 12, §38.3).
"""
from .canary import CanaryReport, CanaryResult, run_canary_suite
from .config import (GateConfig, HardRiskConstants, LatencyConfig,
                     MarginConfig, ScenarioConfig, TaxConfig)
from .engine import RiskEngine
from .latency import LatencyMonitor
from .margin import BrokerReconciler, MarginEngine
from .models import (AccountState, AccountType, DataIntegrity, DecisionStatus,
                     LatencySample, LatencyState, MacroState, MarginImpact,
                     Mode, OptionQuote, ProbabilityEstimate, Right,
                     RiskDecision, ScenarioResult, Settlement, SkewState,
                     TaxAssessment, TaxProfile, TradeCandidate,
                     UnderlyingContext)
from .scenario import bs_delta, bs_price, scenario_grid, worst_case
from .tax import WashSaleLedger
from .vol_surface import (StrikeIV, SurfaceMetrics, classify_skew,
                          rr25_percentile, skew_metrics)

__version__ = "0.2.0"
__all__ = [
    "AccountState", "AccountType", "BrokerReconciler", "CanaryReport",
    "CanaryResult", "run_canary_suite",
    "DataIntegrity", "DecisionStatus",
    "GateConfig", "HardRiskConstants", "LatencyConfig", "LatencyMonitor",
    "LatencySample", "LatencyState", "MacroState", "MarginConfig",
    "MarginEngine", "MarginImpact", "Mode", "OptionQuote",
    "ProbabilityEstimate", "Right", "RiskDecision", "RiskEngine",
    "ScenarioConfig", "ScenarioResult", "Settlement", "SkewState",
    "StrikeIV", "SurfaceMetrics", "TaxAssessment", "TaxConfig",
    "TaxProfile", "TradeCandidate", "UnderlyingContext", "WashSaleLedger",
    "bs_delta", "bs_price", "classify_skew", "rr25_percentile",
    "scenario_grid", "skew_metrics", "worst_case",
]
