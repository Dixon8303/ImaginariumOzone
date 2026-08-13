"""
Risk manager for the HoneyDrip Bot.

Enforces position sizing and daily loss limits before any trade is executed.
"""

from typing import Dict, Any
from honeydrip_bot.config import (
    MAX_POSITION_PCT,
    MAX_DAILY_LOSS_PCT,
    MIN_EQUITY,
    SIGNAL_MIN_CONFIDENCE,
)
from honeydrip_bot.trade_logger import load_trades


def daily_realized_loss(equity: float) -> float:
    """Sum of losses from today's closed trades (negative P&L entries)."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date().isoformat()
    trades = load_trades()
    loss = 0.0
    for t in trades:
        logged = t.get("logged_at", "")
        if logged.startswith(today):
            pnl = t.get("execution_result", {}).get("realized_pnl", 0.0)
            if pnl < 0:
                loss += abs(pnl)
    return loss


def evaluate_risk(signal: Dict[str, Any], equity: float) -> Dict[str, Any]:
    if equity < MIN_EQUITY:
        return {"approved": False, "reason": f"Equity ${equity:.2f} below minimum ${MIN_EQUITY:.2f}"}

    confidence = signal.get("confidence", 1.0)
    if confidence < SIGNAL_MIN_CONFIDENCE:
        return {"approved": False, "reason": f"Confidence {confidence:.0%} below threshold {SIGNAL_MIN_CONFIDENCE:.0%}"}

    price = signal.get("price")
    if not price or price <= 0:
        return {"approved": False, "reason": "Invalid or missing price in signal"}

    loss_today = daily_realized_loss(equity)
    max_loss = equity * MAX_DAILY_LOSS_PCT
    if loss_today >= max_loss:
        return {"approved": False, "reason": f"Daily loss limit hit: ${loss_today:.2f} >= ${max_loss:.2f} (2% of equity)"}

    max_dollars = equity * MAX_POSITION_PCT
    shares = int(max_dollars / price)
    if shares < 1:
        return {"approved": False, "reason": f"Position too small: ${max_dollars:.2f} / ${price:.2f} < 1 share"}

    return {
        "approved": True,
        "shares": shares,
        "max_dollars": round(max_dollars, 2),
        "reason": "Risk check passed",
    }
