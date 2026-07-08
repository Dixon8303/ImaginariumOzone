"""
Risk manager for the HoneyDrip Bot.

Enforces position sizing and basic risk rules before any trade is executed.
All values are conservative defaults suitable for paper trading validation.
"""

from typing import Dict, Any

MAX_POSITION_PCT = 0.05   # max 5% of equity per position
MAX_POSITIONS = 10        # max concurrent open positions
MIN_EQUITY = 1000.0       # refuse to trade if equity drops below this


def evaluate_risk(signal: Dict[str, Any], equity: float) -> Dict[str, Any]:
    if equity < MIN_EQUITY:
        return {"approved": False, "reason": f"Equity ${equity:.2f} below minimum ${MIN_EQUITY:.2f}"}

    price = signal.get("price")
    if not price or price <= 0:
        return {"approved": False, "reason": "Invalid or missing price in signal"}

    max_dollars = equity * MAX_POSITION_PCT
    shares = int(max_dollars / price)

    if shares < 1:
        return {"approved": False, "reason": f"Position too small: {max_dollars:.2f} / {price:.2f} < 1 share"}

    return {
        "approved": True,
        "shares": shares,
        "max_dollars": max_dollars,
        "reason": "Risk check passed",
    }
