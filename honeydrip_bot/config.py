import os
import sys

# Hard-coded safeguards — do not change
PAPER = True
LIVE_TRADING_ENABLED = False

# Double interlock: abort immediately if not explicitly armed
if os.environ.get("HONEYDRIP_ARMED") != "YES":
    sys.exit(
        "ABORT: HONEYDRIP_ARMED env var is not set to YES. "
        "Execution halted for safety. "
        "Set HONEYDRIP_ARMED=YES only in a confirmed paper environment."
    )

# Credentials from environment only — never hardcoded
APCA_API_KEY_ID = os.environ.get("APCA_API_KEY_ID")
APCA_API_SECRET_KEY = os.environ.get("APCA_API_SECRET_KEY")

if not APCA_API_KEY_ID or not APCA_API_SECRET_KEY:
    sys.exit(
        "ABORT: Alpaca API credentials not found in environment variables. "
        "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY before running."
    )

# Paper trading endpoint — only endpoint permitted
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
ALPACA_DATA_URL = "https://data.alpaca.markets"

# Phase 1 gate
PHASE_1_REQUIRED_TRADES = 20
