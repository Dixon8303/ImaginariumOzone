import os
import sys

# Execution mode — set HONEYDRIP_MODE=live_mcp for Robinhood agentic trading
# Defaults to "paper" (Alpaca paper endpoint) if not set
HONEYDRIP_MODE = os.environ.get("HONEYDRIP_MODE", "paper")  # "paper" | "live_mcp"
PAPER = (HONEYDRIP_MODE != "live_mcp")
LIVE_TRADING_ENABLED = (HONEYDRIP_MODE == "live_mcp")

# Safety interlock — always required regardless of mode
if os.environ.get("HONEYDRIP_ARMED") != "YES":
    sys.exit(
        "ABORT: HONEYDRIP_ARMED env var is not set to YES. "
        "Set HONEYDRIP_ARMED=YES in your shell before running."
    )

# Alpaca paper endpoint — used in paper mode only
APCA_API_KEY_ID = os.environ.get("APCA_API_KEY_ID")
APCA_API_SECRET_KEY = os.environ.get("APCA_API_SECRET_KEY")

if HONEYDRIP_MODE == "paper":
    if not APCA_API_KEY_ID or not APCA_API_SECRET_KEY:
        sys.exit(
            "ABORT: Paper mode requires Alpaca credentials. "
            "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY, or switch to HONEYDRIP_MODE=live_mcp."
        )

ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
ALPACA_DATA_URL = "https://data.alpaca.markets"

# Risk limits — apply in both modes
MAX_POSITION_PCT = 0.05       # max 5% of equity per position
MAX_DAILY_LOSS_PCT = 0.02     # hard stop if daily loss exceeds 2% of equity
MIN_EQUITY = 1000.0           # refuse to trade below this equity floor
SIGNAL_MIN_CONFIDENCE = 0.60  # reject signals below 60% confidence

# Phase 1 gate (manual trade log count)
PHASE_1_REQUIRED_TRADES = 20
