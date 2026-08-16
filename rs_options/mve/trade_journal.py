"""Broker trade-history journal — Schwab / thinkorswim transactions CSV.

Reads the operator's exported transaction history (schwab.com → Accounts
→ History → Export, or thinkorswim → Monitor → Account Statement →
Export to file) and computes the same honest statistics the engine's
backtests are held to: win rate, average win vs loss, expectancy,
profit factor, max drawdown — plus net deposits, so account growth is
separated from trading P&L.

PRIVACY: the raw CSV stays in data/ (gitignored, never committed — it
contains the account number). The saved report is AGGREGATE STATISTICS
ONLY: no account numbers, no per-trade rows, no filenames.

    python -m mve.trade_journal                    # newest data/*Transactions*.csv
    python -m mve.trade_journal data/myfile.csv    # explicit path
"""
from __future__ import annotations

import csv
import glob
import os
import re
import sys
from collections import defaultdict, deque
from datetime import datetime

DATA_DIR = "data"
TRADE_ACTIONS = ("buy", "sell")          # matched as prefixes of Action
TRANSFER_HINTS = ("transfer", "wire", "journal", "moneylink", "ach",
                  "deposit", "withdrawal")
INCOME_HINTS = ("dividend", "interest", "reinvest")
OPTION_RE = re.compile(r"\d{2}/\d{2}/\d{4}\s+[\d.]+\s+[CP]\b")


def parse_money(s: str) -> float:
    """'$1,234.56' / '-$123.45' / '($123.45)' / '' -> float."""
    s = (s or "").strip()
    if not s:
        return 0.0
    neg = s.startswith("(") or "-" in s
    val = re.sub(r"[^0-9.]", "", s)
    if not val:
        return 0.0
    return -float(val) if neg else float(val)


def parse_date(s: str):
    """'08/15/2026' (optionally '... as of 08/14/2026') -> date."""
    s = (s or "").split(" as of")[0].strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def load_rows(path: str) -> list[dict]:
    """Tolerant CSV load: skips preamble lines until the header row
    (must contain Date, Action, Amount). Returns rows chronologically
    (the export is newest-first; full reversal restores intraday order)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        raw = list(csv.reader(f))
    header_idx = next(
        (i for i, row in enumerate(raw)
         if {"date", "action", "amount"} <= {c.strip().lower() for c in row}),
        None)
    if header_idx is None:
        raise SystemExit("Could not find the header row (Date/Action/Amount) "
                         "— is this a Schwab/thinkorswim transactions export?")
    cols = [c.strip().lower() for c in raw[header_idx]]
    rows = []
    for row in raw[header_idx + 1:]:
        if len(row) < len(cols):
            continue
        d = dict(zip(cols, (c.strip() for c in row)))
        d["_date"] = parse_date(d.get("date", ""))
        if d["_date"] is None:
            continue
        rows.append(d)
    rows.reverse()                       # newest-first file -> chronological
    rows.sort(key=lambda r: r["_date"]) # stable: keeps intraday order
    return rows


def analyze(rows: list[dict]) -> dict:
    """FIFO round-trip matching per symbol, direction-agnostic (longs and
    shorts). Per-unit cash comes from Amount/qty, so option multipliers
    and fees are included automatically."""
    lots: dict = defaultdict(deque)      # symbol -> deque of [qty, unit_cash, date]
    trades: list[dict] = []
    fees = contributions = income = 0.0

    for r in rows:
        action = r.get("action", "").lower()
        symbol = r.get("symbol", "")
        amount = parse_money(r.get("amount", ""))
        fees_row = parse_money(r.get("fees & comm", "") or r.get("fees", ""))
        if not action.startswith(TRADE_ACTIONS) or not symbol:
            if any(h in action for h in TRANSFER_HINTS):
                contributions += amount
            elif any(h in action for h in INCOME_HINTS):
                income += amount
            continue

        try:
            qty = abs(float(r.get("quantity", "0").replace(",", "")))
        except ValueError:
            continue
        if qty == 0:
            continue
        fees += abs(fees_row)
        unit_cash = (abs(amount) / qty if amount
                     else parse_money(r.get("price", ""))
                     * (100.0 if OPTION_RE.search(symbol) else 1.0))
        signed = qty if action.startswith("buy") else -qty

        book = lots[symbol]
        while signed != 0 and book and (book[0][0] > 0) != (signed > 0):
            lot = book[0]
            matched = min(abs(signed), abs(lot[0]))
            direction = 1 if lot[0] > 0 else -1        # +1 long, -1 short
            open_cash, close_cash = lot[1], unit_cash
            trades.append(dict(
                pnl=(close_cash - open_cash) * matched * direction,
                cost=open_cash * matched,
                entry=lot[2], exit=r["_date"],
            ))
            lot[0] -= matched * direction
            signed += matched * direction
            if lot[0] == 0:
                book.popleft()
        if signed != 0:
            book.append([signed, unit_cash, r["_date"]])

    open_positions = sum(1 for book in lots.values() for _ in book)
    return dict(trades=trades, fees=fees, contributions=contributions,
                income=income, open_positions=open_positions)


def _max_drawdown(pnls: list[float]) -> float:
    peak = equity = dd = 0.0
    for p in pnls:
        equity += p
        peak = max(peak, equity)
        dd = min(dd, equity - peak)
    return dd


def summary(result: dict) -> str:
    trades = sorted(result["trades"], key=lambda t: t["exit"])
    lines = ["TRADE JOURNAL — broker history, aggregate statistics only", ""]
    if not trades:
        lines.append("No closed round trips found in the file.")
        return "\n".join(lines)

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    day_trades = sum(1 for t in trades if t["entry"] == t["exit"])
    holds = [(t["exit"] - t["entry"]).days for t in trades]
    pct = [t["pnl"] / t["cost"] for t in trades if t["cost"] > 0]
    total = sum(pnls)
    monthly = defaultdict(float)
    for t in trades:
        monthly[t["exit"].strftime("%Y-%m")] += t["pnl"]

    lines += [
        f"period: {trades[0]['entry']} -> {trades[-1]['exit']}",
        f"closed round trips: {len(trades)}   day trades: {day_trades} "
        f"({day_trades / len(trades):.0%})   avg hold: "
        f"{sum(holds) / len(holds):.1f} days",
        f"open positions still on the book: {result['open_positions']}",
        "",
        f"win rate: {len(wins) / len(pnls):.0%}   "
        f"avg win: ${sum(wins) / len(wins):+,.2f}" if wins else "win rate: 0%",
    ]
    if losses:
        lines.append(f"avg loss: ${sum(losses) / len(losses):+,.2f}   "
                     f"largest loss: ${min(pnls):+,.2f}")
    lines += [
        f"expectancy: ${total / len(pnls):+,.2f}/trade"
        + (f"   ({sum(pct) / len(pct):+.1%} of position cost)" if pct else ""),
        f"profit factor: "
        + (f"{sum(wins) / abs(sum(losses)):.2f}" if losses and sum(losses) != 0
           else "n/a (no losses)"),
        f"total trading P&L: ${total:+,.2f}   fees paid: ${result['fees']:,.2f}",
        f"max drawdown (closed-trade curve): ${_max_drawdown(pnls):+,.2f}",
        f"net contributions (deposits - withdrawals): "
        f"${result['contributions']:+,.2f}   other income: "
        f"${result['income']:+,.2f}",
        "",
        "monthly P&L:",
    ]
    lines += [f"  {m}: ${monthly[m]:+,.2f}" for m in sorted(monthly)]
    lines += [
        "",
        "Read with LAW 19: winning trades do not prove an edge. Dollar",
        "expectancy here has no stop data, so R-multiples are not",
        "computable — % of position cost is the closest honest analogue.",
    ]
    if len(trades) < 50:
        lines.append(f"n={len(trades)} closed trades is below the ~50 needed "
                     "before win rate and expectancy stabilize — treat every "
                     "number above as provisional.")
    return "\n".join(lines)


def find_csv() -> str:
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*Transactions*.csv")),
                   key=os.path.getmtime)
    if not files:
        raise SystemExit(
            "No transactions CSV found. Export from Schwab/thinkorswim and "
            "put the file in rs_options/data/ — it stays local (gitignored).")
    return files[-1]


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else find_csv()
    result = analyze(load_rows(path))
    from .report import save_and_print
    save_and_print("trade_journal", summary(result))
