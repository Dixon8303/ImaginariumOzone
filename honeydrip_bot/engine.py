import os
import sys

# DOUBLE INTERLOCK — explicit second check before any imports
if os.environ.get("HONEYDRIP_ARMED") != "YES":
    sys.exit("ENGINE ABORT: HONEYDRIP_ARMED safety check failed at engine layer.")

if os.environ.get("LIVE_TRADING_ENABLED", "False").lower() == "true":
    sys.exit("ENGINE ABORT: LIVE_TRADING_ENABLED must never be True in this phase.")

# Config import triggers its own safeguard checks
from honeydrip_bot import config
from honeydrip_bot.alpaca_client import get_api
from honeydrip_bot.signal_bridge import get_signals
from honeydrip_bot.risk_manager import evaluate_risk
from honeydrip_bot.trade_logger import load_trades, log_trade


def run():
    print(f"HoneyDrip Engine starting — PAPER={config.PAPER}, LIVE_TRADING_ENABLED={config.LIVE_TRADING_ENABLED}")
    print(f"Endpoint: {config.ALPACA_BASE_URL}")

    trade_count = len(load_trades())
    print(f"Phase 1 progress: {trade_count}/{config.PHASE_1_REQUIRED_TRADES} trades logged")

    api = get_api()
    account = api.get_account()
    print(f"Paper account equity: ${account.equity}")

    signals = get_signals()
    if not signals:
        print("No signals generated. Exiting.")
        return

    for signal in signals:
        risk = evaluate_risk(signal, float(account.equity))
        if not risk["approved"]:
            print(f"Signal rejected by risk manager: {signal['ticker']} — {risk['reason']}")
            continue

        print(f"[PAPER] Would execute: {signal['action']} {risk['shares']} shares of {signal['ticker']} @ ~{signal.get('price', 'market')}")
        # NOTE: No real order submission during Phase 1.
        # To paper-trade via Alpaca API in Phase 2, uncomment:
        # api.submit_order(symbol=signal['ticker'], qty=risk['shares'],
        #                  side=signal['action'], type='market', time_in_force='day')

        log_trade({
            "ticker": signal["ticker"],
            "action": signal["action"],
            "shares": risk["shares"],
            "signal_source": signal.get("source", "honey_drip"),
            "phase": "paper",
        })


if __name__ == "__main__":
    run()
