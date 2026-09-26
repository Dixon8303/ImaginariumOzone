"""Daily trading brief generator — equity status, positions, P&L, signals."""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

try:
    from honeydrip_bot.alpaca_client import get_api
except ImportError:
    def get_api():
        raise RuntimeError("Alpaca API not available — install requirements: pip install -r honeydrip_bot/requirements.txt")

from honeydrip_bot.trade_logger import load_trades


def get_account_snapshot() -> Dict[str, Any]:
    """Fetch current account state from Alpaca."""
    try:
        api = get_api()
        account = api.get_account()
        positions = api.list_positions()
        return {
            "equity": float(account.equity),
            "cash": float(account.cash),
            "buying_power": float(account.buying_power),
            "portfolio_value": float(account.portfolio_value),
            "daytrading_buying_power": float(account.daytrading_buying_power),
            "positions": [
                {
                    "symbol": p.symbol,
                    "qty": float(p.qty),
                    "avg_fill_price": float(p.avg_fill_price),
                    "current_price": float(p.current_price),
                    "side": p.side,
                    "market_value": float(p.market_value),
                    "unrealized_pl": float(p.unrealized_pl),
                    "unrealized_plpc": float(p.unrealized_plpc),
                }
                for p in positions
            ],
        }
    except Exception as e:
        return {"error": str(e)}


def get_today_trades(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get all trades from today."""
    if "error" in snapshot:
        return []
    trades = load_trades()
    today = datetime.now().date()
    return [
        t for t in trades
        if datetime.fromisoformat(t["logged_at"]).date() == today
    ]


def get_recent_trades(days: int = 5) -> List[Dict[str, Any]]:
    """Get trades from the past N days."""
    trades = load_trades()
    cutoff = datetime.now() - timedelta(days=days)
    return [
        t for t in trades
        if datetime.fromisoformat(t["logged_at"]) >= cutoff
    ]


def calculate_session_stats(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate P&L and performance metrics."""
    if "error" in snapshot:
        return {}
    trades = get_today_trades(snapshot)
    equity = snapshot["equity"]

    position_pl = sum(p["unrealized_pl"] for p in snapshot["positions"])
    total_positions = len(snapshot["positions"])

    return {
        "equity": equity,
        "cash": snapshot["cash"],
        "buying_power": snapshot["buying_power"],
        "unrealized_pl": position_pl,
        "num_positions": total_positions,
        "trades_today": len(trades),
        "approved_signals": len([t for t in trades if t.get("execution_result", {}).get("status") == "executed"]),
    }


def format_positions_table(snapshot: Dict[str, Any]) -> str:
    """Format positions as a readable table."""
    if "error" in snapshot or not snapshot.get("positions"):
        return "No open positions."

    positions = snapshot["positions"]
    lines = ["OPEN POSITIONS\n" + "=" * 80]
    lines.append(
        f"{'Ticker':<8} {'Qty':>8} {'Avg Price':>12} {'Current':>12} "
        f"{'P&L':>12} {'%':>8}"
    )
    lines.append("-" * 80)

    for p in positions:
        pl_color = "+" if p["unrealized_pl"] >= 0 else ""
        lines.append(
            f"{p['symbol']:<8} {p['qty']:>8.0f} ${p['avg_fill_price']:>11.2f} "
            f"${p['current_price']:>11.2f} {pl_color}${p['unrealized_pl']:>10.2f} "
            f"{p['unrealized_plpc']:>7.1%}"
        )

    return "\n".join(lines)


def format_today_trades(snapshot: Dict[str, Any]) -> str:
    """Format today's trades."""
    trades = get_today_trades(snapshot)
    if not trades:
        return "No trades today."

    lines = ["TODAY'S SIGNALS & TRADES\n" + "=" * 80]
    for trade in trades:
        logged_at = datetime.fromisoformat(trade["logged_at"]).strftime("%H:%M:%S")
        lines.append(
            f"[{logged_at}] {trade['action'].upper():>4} "
            f"{trade['shares']:>4.0f} × {trade['ticker']:<6} | "
            f"Source: {trade.get('signal_source', 'unknown')} | "
            f"Mode: {trade.get('mode', 'unknown')}"
        )
    return "\n".join(lines)


def format_weekly_summary() -> str:
    """7-day performance summary."""
    trades = get_recent_trades(days=7)
    if not trades:
        return "No trades in the past 7 days."

    lines = ["7-DAY SUMMARY\n" + "=" * 80]
    by_day = {}
    for trade in trades:
        day = datetime.fromisoformat(trade["logged_at"]).date()
        if day not in by_day:
            by_day[day] = []
        by_day[day].append(trade)

    for day in sorted(by_day.keys(), reverse=True):
        day_trades = by_day[day]
        lines.append(f"{day}: {len(day_trades)} trades")

    return "\n".join(lines)


def generate_brief() -> str:
    """Generate the full daily brief."""
    snapshot = get_account_snapshot()
    stats = calculate_session_stats(snapshot)

    lines = [
        "╔════════════════════════════════════════════════════════════════════╗",
        "║                      HoneyDrip Daily Brief                         ║",
        "╚════════════════════════════════════════════════════════════════════╝\n",
    ]

    if "error" in snapshot:
        lines.append(f"ERROR: Unable to fetch account data — {snapshot['error']}")
    else:
        lines.append("ACCOUNT STATUS")
        lines.append("=" * 80)
        lines.append(f"Equity:                    ${stats['equity']:>15,.2f}")
        lines.append(f"Cash Available:            ${stats['cash']:>15,.2f}")
        lines.append(f"Buying Power:              ${stats['buying_power']:>15,.2f}")
        lines.append(f"Unrealized P&L:            ${stats['unrealized_pl']:>15,.2f}")
        lines.append(f"Open Positions:            {stats['num_positions']:>15}")
        lines.append("")

        lines.append(format_positions_table(snapshot))
        lines.append("")
        lines.append(format_today_trades(snapshot))
        lines.append("")
        lines.append(format_weekly_summary())

    lines.append("\n" + "=" * 80)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

    return "\n".join(lines)


def save_brief(content: str, output_dir: str = "honeydrip_bot/briefs") -> str:
    """Save brief to a timestamped file."""
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(
        output_dir,
        f"brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    with open(filename, "w") as f:
        f.write(content)
    return filename


if __name__ == "__main__":
    brief = generate_brief()
    print(brief)
    filepath = save_brief(brief)
    print(f"\n✓ Brief saved to {filepath}")
