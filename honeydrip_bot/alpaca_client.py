import alpaca_trade_api as tradeapi
from honeydrip_bot.config import (
    APCA_API_KEY_ID,
    APCA_API_SECRET_KEY,
    ALPACA_BASE_URL,
    PAPER,
)


def get_api() -> tradeapi.REST:
    assert PAPER is True, "ABORT: PAPER must be True — live trading is not authorized."
    assert "paper-api" in ALPACA_BASE_URL, (
        f"ABORT: Non-paper endpoint detected: {ALPACA_BASE_URL}"
    )
    return tradeapi.REST(
        APCA_API_KEY_ID,
        APCA_API_SECRET_KEY,
        base_url=ALPACA_BASE_URL,
    )
