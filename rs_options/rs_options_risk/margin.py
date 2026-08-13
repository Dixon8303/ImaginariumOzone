"""Margin & buying-power engine. Spec §8.

Long-premium structures only (baseline strategy). Short-structure margin
requires validated broker-formula adapters and is prohibited until then
(spec §8, "BPR by Structure").
"""
from __future__ import annotations

from .config import MarginConfig
from .models import AccountState, AccountType, MarginImpact


class MarginEngine:
    def __init__(self, cfg: MarginConfig | None = None):
        self.cfg = cfg or MarginConfig()

    def evaluate(self, account: AccountState, cost_dollars: float,
                 is_day_trade: bool, holds_overnight: bool = False) -> MarginImpact:
        """Pre-trade Margin_Impact for a long-premium debit of `cost_dollars`
        (premium + fees, i.e., the full buying-power reduction)."""
        cfg = self.cfg
        reasons: list = []
        gfv_risk = False
        pdt_restricted = False

        if account.account_type is AccountType.CASH:
            bp_before = account.settled_cash
            unsettled = account.unsettled_total
            if cost_dollars > account.settled_cash + unsettled:
                reasons.append("INSUFFICIENT_FUNDS")
            elif cost_dollars > account.settled_cash:
                # Funding would require unsettled proceeds (T+1 ledger).
                gfv_risk = True
                if cfg.enforce_gfv:
                    # Day trade: position closes before funding settles → GFV.
                    # Otherwise still barred by "debits fund from settled cash".
                    reasons.append(
                        "GFV_RISK" if is_day_trade else "INSUFFICIENT_SETTLED_FUNDS"
                    )
            bp_after = account.settled_cash - cost_dollars
        else:
            # REG_T_MARGIN / PORTFOLIO_MARGIN
            bp_before = account.buying_power
            if (is_day_trade
                    and account.equity < cfg.pdt_min_equity
                    and account.day_trades_used_5d >= cfg.pdt_max_day_trades_5d):
                pdt_restricted = True
                reasons.append("PDT_LIMIT")
            if cost_dollars > account.buying_power:
                reasons.append("INSUFFICIENT_BUYING_POWER")
            bp_after = account.buying_power - cost_dollars
            if bp_after < cfg.min_bp_buffer_pct * account.equity:
                reasons.append("BP_BUFFER_BREACH")

        # Long options are fully paid; overnight requirement equals the debit.
        overnight_req = cost_dollars if holds_overnight else 0.0

        # De-duplicate while preserving order.
        reasons = list(dict.fromkeys(reasons))

        return MarginImpact(
            ok=not reasons,
            reasons=reasons,
            account_type=account.account_type,
            bp_before=bp_before,
            bp_reduction=cost_dollars,
            bp_after=bp_after,
            overnight_maintenance_req=overnight_req,
            settled_cash=account.settled_cash,
            unsettled_proceeds=account.unsettled_total,
            gfv_risk=gfv_risk,
            pdt_restricted=pdt_restricted,
            day_trades_used_5d=account.day_trades_used_5d,
        )

    def broker_reconciliation_ok(self, model_bp: float, broker_bp: float,
                                 equity: float) -> bool:
        """Spec §8: |model_BP − broker_BP| > tolerance → stop and reconcile."""
        if equity <= 0:
            return False
        return abs(model_bp - broker_bp) <= self.cfg.broker_bp_divergence_tolerance * equity
