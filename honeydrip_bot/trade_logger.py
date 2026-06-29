import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "trade_log.json")
PHASE_1_REQUIRED = 20


def log_trade(trade: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    trades = load_trades()
    trade["logged_at"] = datetime.now(timezone.utc).isoformat()
    trades.append(trade)
    with open(LOG_FILE, "w") as f:
        json.dump(trades, f, indent=2)
    count = len(trades)
    print(f"Trade logged. Phase 1 progress: {count}/{PHASE_1_REQUIRED}")
    if count >= PHASE_1_REQUIRED:
        print("PHASE 1 COMPLETE: 20 trades logged. Ready to assess Live-Readiness Gate.")


def load_trades() -> List[Dict[str, Any]]:
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE) as f:
        return json.load(f)


def phase1_status() -> Dict[str, Any]:
    trades = load_trades()
    count = len(trades)
    return {
        "logged": count,
        "required": PHASE_1_REQUIRED,
        "remaining": max(0, PHASE_1_REQUIRED - count),
        "complete": count >= PHASE_1_REQUIRED,
    }
