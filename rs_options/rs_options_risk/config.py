"""Configuration objects. Spec: §4 (hard constants), §8, §36, §38.

Every default marked CALIBRATE is a research placeholder, not a validated
production value (spec §38.3, §53, LAW 12).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HardRiskConstants:
    """Spec §4 — non-negotiable."""

    max_trade_risk_pct: float = 0.01
    max_portfolio_drawdown_pct: float = 0.10
    max_single_underlying_exposure_pct: float = 0.05

    daily_loss_limit_pct: float = 0.03          # configurable
    max_open_positions: int = 5                 # configurable
    max_concurrent_risk_pct: float = 0.03       # configurable
    max_cluster_exposure_pct: float = 0.10      # §78 correlated clusters
    max_contracts_per_trade: int = 50           # configurable


@dataclass(frozen=True)
class ScenarioConfig:
    """Spec §6 — scenario pricing, §47 execution model assumptions."""

    risk_free_rate: float = 0.04
    entry_spread_fraction: float = 0.5    # entry = mid + f * half_spread
    exit_spread_fraction: float = 0.5     # exit  = model - f * half_spread
    invalidation_overshoot_pct: float = 0.005   # Stress A (CALIBRATE)
    adverse_iv_points: float = 0.05             # Stress B: -5 vol pts (CALIBRATE)
    extra_time_decay_mult: float = 2.0          # Stress C: hold overrun
    spread_widen_mult: float = 2.0              # Stress D: liquidity failure
    slippage_spread_fraction: float = 0.5       # slippage est per §48 (CALIBRATE)
    fees_per_contract_roundtrip: float = 1.30   # CALIBRATE per broker
    trading_hours_per_day: float = 6.5


@dataclass(frozen=True)
class MarginConfig:
    """Spec §8."""

    min_bp_buffer_pct: float = 0.05       # free BP floor as pct of equity
    pdt_min_equity: float = 25_000.0
    pdt_max_day_trades_5d: int = 3        # the 4th is rejected under equity min
    enforce_gfv: bool = True
    settlement_days: int = 1              # T+1
    broker_bp_divergence_tolerance: float = 0.02  # §8 reconciliation


@dataclass(frozen=True)
class TaxConfig:
    """Spec §36. Flags for a tax professional — not tax advice."""

    profile: str = "taxable"              # taxable | mtm_475f | ira
    wash_sale_lookback_days: int = 30
    escalation_month_day: tuple = (10, 1)   # Q4 escalation window start
    hard_block_month_day: tuple = (12, 1)   # taxable hard-block start
    ira_hard_block_month_day: tuple = (11, 1)
    wash_sale_penalty: int = 2
    escalated_penalty: int = 4


@dataclass(frozen=True)
class LatencyConfig:
    """Spec §38. All thresholds CALIBRATE per broker/feed in Paper/Shadow."""

    data_age_yellow_ms: float = 250.0
    data_age_red_ms: float = 750.0
    rtt_yellow_ms: float = 300.0
    rtt_red_ms: float = 750.0
    heartbeat_red_ms: float = 5_000.0
    heartbeat_black_ms: float = 15_000.0
    clock_skew_black_ms: float = 250.0
    window_size: int = 200                # rolling sample window
    min_samples: int = 30                 # uncalibrated => RED (fail closed)
    recovery_seconds: float = 900.0       # 15 min sustained before re-arm


@dataclass(frozen=True)
class GateConfig:
    """Spec §32/§34/§35 thresholds."""

    min_net_score: int = 7
    min_expected_value_r: float = 0.10
    yellow_size_mult: float = 0.5
    yellow_score_add: int = 1
    skew_overlay_penalty: int = 2         # steep/extreme index put skew vs bullish thesis
    latency_yellow_penalty: int = 1
