"""Option cost recorder — measure the overlay without spending anything.

The forecast has a hole in it: this project has never measured option
P&L. The backtest models the UNDERLYING, historical option chains are
paid data, and the paper options cycle needs options enabled on the
broker account before it fills anything. So the leveraged instrument the
operator actually trades has never been priced against the signal that
triggers it.

This module closes that hole with zero capital and no account
permissions. It needs only market data: at each signal it selects the
contract the doctrine WOULD buy, records the real bid/ask/mid/delta/DTE,
and re-quotes it daily until the doctrine's exit. What accumulates is:

  * the real dollar cost of a doctrine contract, per ticker — which is
    the honest answer to "how much account do I need"
  * the real spread drag, which the backtest never charged
  * eventually, the option's realized return against the stock's
    R-multiple — the missing translation between the two

Nothing here places an order or needs buying power. It fails soft: no
options subscription means no records, never a broken trading run.

    python -m paper.option_costs        # affordability report
"""
from __future__ import annotations

import json
import os
from datetime import date

from mve.chain_select import DELTA_TARGET, DTE_RANGE, MAX_SPREAD_PCT

from .options_broker import parse_occ_symbol, select_contract

COSTS_PATH = os.path.join("docs", "reports", "option_costs.jsonl")

# Doctrine risk rules, mirrored from paper.daily. Imported there rather
# than redefined so a change to sizing cannot silently desync this.
RISK_PCT = 0.01
MAX_POSITION_PCT = 0.05


def min_equity_for_share(price: float, stop_distance: float) -> float:
    """Smallest account that can buy ONE share of `price` under both
    doctrine limits. The 5% notional cap almost always binds first,
    which is why a small account places no orders at all rather than
    small ones."""
    by_risk = (stop_distance / RISK_PCT) if stop_distance > 0 else 0.0
    by_cap = price / MAX_POSITION_PCT
    return max(by_risk, by_cap)


def min_equity_for_contract(premium_per_contract: float) -> float:
    """Smallest account that can buy one option contract inside the 5%
    notional cap. Premium is per share; a contract is 100 shares."""
    return (premium_per_contract * 100.0) / MAX_POSITION_PCT


def quote_doctrine_contract(broker, ticker: str, spot: float,
                            today: str) -> dict | None:
    """The contract the doctrine would buy right now, with its real
    quote. Returns None when the chain, the quotes, or the subscription
    is unavailable — a missing quote is not a zero cost."""
    as_of = date.fromisoformat(today)
    try:
        contracts = broker.contracts(ticker, as_of)
        quotes = broker.quotes(ticker)
    except Exception:
        return None
    if not contracts or not quotes:
        return None
    pick = select_contract(contracts, spot, as_of, quotes=quotes)
    if not pick:
        return None
    q = quotes.get(pick.get("symbol"), {})
    bid, ask = q.get("bid"), q.get("ask")
    if bid is None or ask is None:
        return None
    mid = (bid + ask) / 2.0
    parsed = parse_occ_symbol(pick["symbol"]) or {}
    return {
        "as_of": today, "ticker": ticker, "spot": round(spot, 2),
        "contract": pick["symbol"],
        "strike": parsed.get("strike"), "dte": pick.get("dte"),
        "delta": pick.get("delta"), "basis": pick.get("basis"),
        "bid": bid, "ask": ask, "mid": round(mid, 4),
        "spread_pct": round((ask - bid) / mid, 4) if mid > 0 else None,
        # What it actually costs to put this trade on, in dollars.
        "cost_per_contract": round(mid * 100.0, 2),
        "min_equity_for_contract": round(min_equity_for_contract(mid), 2),
    }


def record(rows: list, path: str | None = None) -> int:
    """Append observations as JSONL. Append-only: a cost measurement is
    a fact about a moment and is never rewritten."""
    path = path or COSTS_PATH
    if not rows:
        return 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    return len(rows)


def load(path: str | None = None) -> list:
    path = path or COSTS_PATH
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue          # a torn line is skipped, not fatal
    return out


def collect(broker, signals: list, today: str) -> list:
    """One observation per signal. Never raises into the trading run."""
    rows = []
    for sig in signals:
        try:
            row = quote_doctrine_contract(broker, sig["ticker"],
                                          sig["close"], today)
        except Exception:
            row = None
        if row:
            row["stock_stop"] = sig.get("stop")
            row["stock_r_denom"] = sig.get("r_denom")
            rows.append(row)
    return rows


def format_costs(rows: list, equity: float | None = None) -> str:
    """The operator-facing answer to 'what can I actually afford'."""
    if not rows:
        return ("OPTION COST RECORDER: no quotes today (no signals, or the "
                "account has no options data subscription). Nothing "
                "recorded — a missing quote is not a zero cost.")
    lines = [f"OPTION COST RECORDER ({len(rows)} contracts priced) — "
             "no orders, no buying power used:"]
    for r in sorted(rows, key=lambda x: x["cost_per_contract"]):
        delta = (f"delta {r['delta']:.2f}" if r.get("delta") is not None
                 else f"~{r['basis']}")
        spread = (f"{r['spread_pct']:.1%}" if r.get("spread_pct") is not None
                  else "n/a")
        flag = "" if (r.get("spread_pct") or 0) <= MAX_SPREAD_PCT \
            else "  SPREAD OVER DOCTRINE CAP"
        lines.append(
            f"  {r['ticker']:<6} {r['contract']}  {delta}  "
            f"{r['dte']}d  mid {r['mid']:.2f}  spread {spread}{flag}")
        lines.append(
            f"         costs ${r['cost_per_contract']:,.2f} per contract; "
            f"needs ${r['min_equity_for_contract']:,.0f} equity to buy one "
            f"inside the {MAX_POSITION_PCT:.0%} position cap")
    cheapest = min(rows, key=lambda x: x["cost_per_contract"])
    lines += ["",
              f"  cheapest doctrine contract today: {cheapest['ticker']} at "
              f"${cheapest['cost_per_contract']:,.2f}"]
    if equity is not None:
        afford = [r for r in rows
                  if r["cost_per_contract"] <= equity * MAX_POSITION_PCT]
        lines.append(
            f"  at ${equity:,.2f} equity you can buy {len(afford)} of "
            f"{len(rows)} inside the position cap")
        if not afford:
            lines.append(
                f"  -> ${cheapest['min_equity_for_contract']:,.0f} is the "
                "account size this doctrine needs for its cheapest trade "
                "today. Below that the correct number of contracts is "
                "zero, and the engine placing none is the risk rules "
                "working, not a bug.")
    lines.append(f"  (doctrine contract: delta ~{DELTA_TARGET}, "
                 f"{DTE_RANGE[0]}-{DTE_RANGE[1]} DTE, spread <= "
                 f"{MAX_SPREAD_PCT:.0%})")
    return "\n".join(lines)


def main() -> None:
    rows = load()
    if not rows:
        raise SystemExit(
            "No option costs recorded yet. They accumulate automatically "
            "on each evening run:\n  python -m paper.daily")
    by_ticker = {}
    for r in rows:
        by_ticker.setdefault(r["ticker"], []).append(r["cost_per_contract"])
    print(f"OPTION COST HISTORY — {len(rows)} observations, "
          f"{len(by_ticker)} tickers\n")
    print(f"{'ticker':<8}{'obs':>5}{'cheapest':>12}{'median':>12}"
          f"{'dearest':>12}{'equity needed':>16}")
    for t, costs in sorted(by_ticker.items()):
        s = sorted(costs)
        med = s[len(s) // 2]
        print(f"{t:<8}{len(s):>5}${s[0]:>11,.0f}${med:>11,.0f}"
              f"${s[-1]:>11,.0f}${min_equity_for_contract(s[0] / 100):>15,.0f}")
    allc = sorted(r["cost_per_contract"] for r in rows)
    print(f"\nCheapest doctrine contract ever recorded: ${allc[0]:,.2f} "
          f"-> needs ${min_equity_for_contract(allc[0] / 100):,.0f} equity "
          f"inside the {MAX_POSITION_PCT:.0%} cap.")


if __name__ == "__main__":
    main()
