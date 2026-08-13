import json
import os
import sys

# Safety interlock — required in every mode
if os.environ.get("HONEYDRIP_ARMED") != "YES":
    sys.exit("ENGINE ABORT: HONEYDRIP_ARMED safety check failed at engine layer.")

from honeydrip_bot import config
from honeydrip_bot.signal_bridge import get_signals
from honeydrip_bot.risk_manager import evaluate_risk
from honeydrip_bot.trade_logger import load_trades, log_trade, phase1_status

PENDING_SIGNALS_FILE = os.path.join(os.path.dirname(__file__), "pending_signals.json")


def run():
    mode_label = "LIVE (Robinhood MCP)" if config.LIVE_TRADING_ENABLED else "PAPER (Alpaca)"
    print(f"HoneyDrip Engine — mode: {mode_label}")

    status = phase1_status()
    print(f"Phase 1 progress: {status['logged']}/{status['required']} trades logged")

    signals = get_signals()
    if not signals:
        print("No signals generated. Exiting.")
        return

    if config.LIVE_TRADING_ENABLED:
        _run_live_mcp(signals)
    else:
        _run_paper(signals)


def _run_live_mcp(signals):
    """
    Live MCP mode: evaluate risk and write approved signals to pending_signals.json.
    Claude Code reads this file and executes via the Robinhood Trading MCP.
    See honeydrip_bot/robinhood_mcp_guide.md for the execution playbook.
    """
    approved = []
    for signal in signals:
        risk = evaluate_risk(signal, equity=_get_equity_estimate())
        if not risk["approved"]:
            print(f"[REJECTED] {signal['ticker']}: {risk['reason']}")
            continue
        approved.append({**signal, "risk": risk})
        print(
            f"[APPROVED] {signal['action'].upper()} {risk['shares']} shares of "
            f"{signal['ticker']} @ ${signal.get('price', 'market')} "
            f"(confidence: {signal.get('confidence', 0):.0%})"
        )

    if not approved:
        print("All signals rejected by risk manager. No trades to execute.")
        _clear_pending()
        return

    with open(PENDING_SIGNALS_FILE, "w") as f:
        json.dump(approved, f, indent=2)

    print(f"\n{len(approved)} approved signal(s) written to pending_signals.json")
    print("Run Claude Code with Robinhood MCP connected to execute these trades.")
    print("See honeydrip_bot/robinhood_mcp_guide.md for the execution playbook.")


def _run_paper(signals):
    """Paper mode: evaluate signals against Alpaca paper account."""
    from honeydrip_bot.alpaca_client import get_api
    api = get_api()
    account = api.get_account()
    equity = float(account.equity)
    print(f"Paper account equity: ${equity:,.2f}")

    for signal in signals:
        risk = evaluate_risk(signal, equity)
        if not risk["approved"]:
            print(f"[REJECTED] {signal['ticker']}: {risk['reason']}")
            continue
        print(
            f"[PAPER] Would execute: {signal['action'].upper()} {risk['shares']} shares "
            f"of {signal['ticker']} @ ~${signal.get('price', 'market')}"
        )
        log_trade({
            "ticker": signal["ticker"],
            "action": signal["action"],
            "shares": risk["shares"],
            "signal_source": signal.get("source", "honey_drip"),
            "mode": "paper",
            "execution_result": {"status": "simulated"},
        })


def _get_equity_estimate() -> float:
    """
    Returns equity estimate for risk sizing in live MCP mode.
    Claude Code will fetch the real value from Robinhood MCP before executing.
    This estimate is used only for the pre-execution risk check in the engine.
    Override by setting HONEYDRIP_EQUITY_ESTIMATE in your environment.
    """
    estimate = os.environ.get("HONEYDRIP_EQUITY_ESTIMATE")
    if estimate:
        return float(estimate)
    print(
        "WARNING: HONEYDRIP_EQUITY_ESTIMATE not set. "
        "Using $10,000 placeholder for risk sizing. "
        "Set this to your actual account equity for accurate position sizing."
    )
    return 10_000.0


def _clear_pending():
    if os.path.exists(PENDING_SIGNALS_FILE):
        os.remove(PENDING_SIGNALS_FILE)


if __name__ == "__main__":
    run()
