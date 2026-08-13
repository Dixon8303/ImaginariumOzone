"""Wash-sale & tax gating. Spec §36.

Produces flags/penalties for the execution gate and estimates for a tax
professional. Not tax advice. Conservative default grouping: underlying
root = one substantially-identical group.
"""
from __future__ import annotations

from datetime import date, timedelta

from .config import TaxConfig
from .models import TaxAssessment, TaxProfile

_CLEAN = "normal"


class WashSaleLedger:
    def __init__(self, cfg: TaxConfig | None = None):
        self.cfg = cfg or TaxConfig()
        self._losses: dict = {}   # group -> list[(date, loss_amount>0)]

    # ------------------------------------------------------------ ledger
    def record_realized_loss(self, group: str, loss_date: date, amount: float) -> None:
        if amount <= 0:
            return
        self._losses.setdefault(group, []).append((loss_date, amount))

    def recent_loss(self, group: str, as_of: date) -> float:
        cutoff = as_of - timedelta(days=self.cfg.wash_sale_lookback_days)
        return sum(a for d, a in self._losses.get(group, ())
                   if cutoff <= d <= as_of)

    def deferred_loss_estimate(self, group: str, as_of: date) -> float:
        """Losses whose 30-day replacement window is still open."""
        return self.recent_loss(group, as_of)

    # -------------------------------------------------------------- gate
    def assess(self, group: str, trade_date: date) -> TaxAssessment:
        cfg = self.cfg
        profile = TaxProfile(cfg.profile)

        # §475(f) mark-to-market election: wash-sale rules do not apply.
        if profile is TaxProfile.MTM_475F:
            return TaxAssessment(profile, False, 0, False, 0.0, _CLEAN)

        recent = self.recent_loss(group, trade_date)
        if recent <= 0:
            return TaxAssessment(profile, False, 0, False, 0.0, _CLEAN)

        md = (trade_date.month, trade_date.day)
        hard_start = (cfg.ira_hard_block_month_day
                      if profile is TaxProfile.IRA
                      else cfg.hard_block_month_day)

        if md >= hard_start:
            # Re-entry after a lookback loss this late defers the loss
            # across the tax-year boundary → hard reject (spec §36.3.4).
            return TaxAssessment(profile, True, cfg.escalated_penalty,
                                 True, recent, "hard_block")
        if md >= cfg.escalation_month_day:
            return TaxAssessment(profile, True, cfg.escalated_penalty,
                                 False, recent, "escalation")
        return TaxAssessment(profile, True, cfg.wash_sale_penalty,
                             False, recent, _CLEAN)

    # --------------------------------------------------------- reporting
    def year_end_exposure(self, as_of: date) -> dict:
        """Groups whose open replacement windows could cross year end."""
        out = {}
        for group in self._losses:
            est = self.deferred_loss_estimate(group, as_of)
            if est > 0:
                out[group] = round(est, 2)
        return out
