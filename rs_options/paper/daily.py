"""Autonomous daily run — scan + Alpaca PAPER shadow trades + report.

Runs after each market close (GitHub Actions cron, or manually with
`python -m paper.daily` from rs_options/). What it does:

1. Fetches fresh daily bars for the whole universe (Alpaca IEX, free).
2. Runs the adopted RS-02 doctrine point-in-time: detector + 200-day
   regime + 12-1 momentum quality (`detect_all` live path).
3. PAPER-trades each surviving signal on Alpaca's paper account as the
   UNDERLYING equity: market buy queued for the next open (matching the
   backtester's next-open entry), bracket stop at the invalidation
   price and target at +3R. Time exit after 15 trading days.
4. Reviews the operator's held Robinhood options (paper/open_options.json)
   against mve.position_manager's exit rules — the co-pilot side of the
   same doctrine the equity brackets enforce automatically.
5. Writes docs/reports/paper_trading.txt — the operator-facing report:
   today's picks with entry/stop/target and the playbook's option
   guidance (for discretionary Robinhood execution), the position
   review, open positions, closed trades in R, and the cumulative
   record.

Scope (§87): this validates the SETUP SIGNAL with fake money. The
options layer stays in the co-pilot flow; nothing here touches a live
account — see alpaca_paper.PaperBroker.
"""
from __future__ import annotations

import json
import os
from datetime import date, timedelta

import pandas as pd

from mve.alpaca_data import fetch_bars
from mve.backtest import MAX_HOLD_BARS, TARGET_R
from mve.chain_select import DELTA_TARGET, DTE_RANGE, MAX_SPREAD_PCT
from mve.position_manager import (OpenPosition, evaluate_exit,
                                  format_exit_report)
from mve.report import save_report
from mve.rs_features import compute_features
from mve.setups import detect_all
from mve.universe import BENCHMARK, SECTOR_ETF, UNIVERSE, required_tickers
from mve.vix_regime import load_term_structure, ratio_on, regime_label

RISK_PCT = 0.01              # 1% of paper equity risked per trade
MAX_POSITION_PCT = 0.05      # 5% notional cap (mirrors HoneyDrip)
MAX_OPEN = 8                 # concurrent-position cap
MIN_BARS = 260               # doctrine needs 253+ bars (12-1 momentum)
HISTORY_DAYS = 420           # calendar days of bars to fetch
LEDGER_PATH = os.path.join("docs", "reports", "paper_ledger.json")
OPTIONS_PATH = os.path.join("paper", "open_options.json")


# ── ledger (committed to the repo — paper-account data only) ─────────
def load_ledger(path: str | None = None) -> dict:
    path = path or LEDGER_PATH          # resolved at call time, not import
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"open": {}, "closed": []}


def save_ledger(ledger: dict, path: str | None = None) -> None:
    path = path or LEDGER_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(ledger, f, indent=2, sort_keys=True)


def bdays_between(a: str, b: str) -> int:
    return max(0, len(pd.bdate_range(a, b)) - 1)


# ── scan ─────────────────────────────────────────────────────────────
def scan(all_bars: dict) -> list:
    """Adopted live doctrine over the universe, point-in-time on the
    latest bar. Returns signal dicts sorted by opportunity score."""
    bench = all_bars.get(BENCHMARK)
    signals = []
    if bench is None or len(bench) < MIN_BARS:
        return signals
    for ticker in UNIVERSE:
        if ticker == BENCHMARK:
            continue
        bars = all_bars.get(ticker)
        if bars is None or len(bars) < MIN_BARS:
            continue
        sector_t = SECTOR_ETF.get(ticker)
        sector = all_bars.get(sector_t) if sector_t else None
        features = compute_features(bars, bench, sector)
        for hit in detect_all(bars, features):          # live doctrine
            close, stop = hit["close"], hit["invalidation_price"]
            if close <= stop:
                continue
            signals.append(dict(
                ticker=ticker, close=close, stop=stop,
                target=round(close + TARGET_R * (close - stop), 2),
                r_denom=round(close - stop, 2),
                score=hit["opportunity_score"], rationale=hit["rationale"]))
    return sorted(signals, key=lambda s: -s["score"])


def position_size(equity: float, close: float, stop: float) -> int:
    """Shares risking RISK_PCT of equity to the stop, capped at
    MAX_POSITION_PCT notional."""
    risk = close - stop
    if risk <= 0:
        return 0
    qty = int(equity * RISK_PCT / risk)
    return max(0, min(qty, int(equity * MAX_POSITION_PCT / close)))


# ── daily cycle ──────────────────────────────────────────────────────
def load_open_options(path: str | None = None) -> list:
    """Operator-maintained Robinhood option positions. Malformed entries
    are surfaced, never dropped silently — a position the review skips
    is a position nobody is watching."""
    path = path or OPTIONS_PATH
    if not os.path.exists(path):
        return []
    with open(path) as f:
        raw = json.load(f)
    positions, bad = [], []
    for row in raw.get("positions", []):
        try:
            positions.append(OpenPosition(
                ticker=row["ticker"], contract=row["contract"],
                quantity=int(row["quantity"]),
                entry_price=float(row["entry_price"]),
                expiry=date.fromisoformat(row["expiry"]),
                invalidation_price=float(row["invalidation_price"]),
                entry_date=(date.fromisoformat(row["entry_date"])
                            if row.get("entry_date") else None),
                entry_underlying=(float(row["entry_underlying"])
                                  if row.get("entry_underlying") is not None
                                  else None)))
        except (KeyError, ValueError, TypeError) as e:
            bad.append(f"{row.get('contract', row)}: {e}")
    if bad:
        raise ValueError("Unreadable entries in open_options.json — fix or "
                         "remove them:\n  " + "\n  ".join(bad))
    return positions


def review_open_options(positions: list, all_bars: dict, today: str) -> str:
    """Apply the doctrine's exit rules to each held option contract."""
    if not positions:
        return ("OPTION POSITIONS (Robinhood): none on file.\n"
                "  Add trades to paper/open_options.json to have them "
                "reviewed here each day.")
    as_of = date.fromisoformat(today)
    verdicts, unpriced = [], []
    for p in positions:
        bars = all_bars.get(p.ticker)
        if bars is None or bars.empty:
            unpriced.append(p.contract)
            continue
        price = float(bars["close"].iloc[-1])
        verdicts.append((p, evaluate_exit(p, price, as_of)))
    text = format_exit_report(verdicts)
    if unpriced:
        text += ("\n\nNOT PRICED (no bars fetched — outside the universe?): "
                 + ", ".join(unpriced))
    return text


def data_is_fresh(all_bars: dict, today: str) -> bool:
    """True only when the benchmark's latest bar IS today's session.
    Guards holidays and half-fetched runs: without this the scanner
    would re-signal yesterday's bars as if they were new."""
    bench = all_bars.get(BENCHMARK)
    if bench is None or bench.empty:
        return False
    return str(bench["trade_date"].iloc[-1]) == today


def run(broker, all_bars: dict, today: str, require_fresh: bool = True) -> str:
    if require_fresh and not data_is_fresh(all_bars, today):
        # No scan, no orders — but days-to-expiry keeps running over a
        # weekend, so held options are still reviewed against the last
        # available prices.
        review = review_open_options(load_open_options(), all_bars, today)
        return (f"PAPER SHADOW TRACK — {today}\n\n"
                "No session today (market holiday, or bars not yet "
                "published). No scan, no orders, no equity changes.\n"
                "Prices below are the last available, not today's.\n\n"
                + review)
    acct = broker.account()
    equity = float(acct["equity"])
    positions = broker.positions()
    ledger = load_ledger()

    # 1. refine estimated entries with actual fills
    for sym, rec in ledger["open"].items():
        if rec.get("entry_estimated") and rec.get("order_id"):
            try:
                o = broker.order(rec["order_id"])
                if o.get("filled_avg_price"):
                    rec["entry"] = float(o["filled_avg_price"])
                    rec["entry_estimated"] = False
            except Exception:
                pass

    # 2. reconcile closures (bracket legs fired since last run)
    closed_today = []
    for sym in [s for s in list(ledger["open"]) if s not in positions]:
        rec = ledger["open"].pop(sym)
        exit_px = None
        try:
            sells = [o for o in broker.orders(status="closed", symbols=sym,
                                              limit=10)
                     if o.get("side") == "sell" and o.get("filled_avg_price")]
            if sells:
                exit_px = float(sells[0]["filled_avg_price"])
        except Exception:
            pass
        denom = rec["entry"] - rec["stop"]
        r = round((exit_px - rec["entry"]) / denom, 3) \
            if exit_px and denom > 0 else None
        reason = ("target" if exit_px and exit_px >= rec["target"] * 0.98
                  else "stop" if exit_px and exit_px <= rec["stop"] * 1.02
                  else "time/other")
        closed_today.append(dict(ticker=sym, entry_date=rec["entry_date"],
                                 exit_date=today, entry=rec["entry"],
                                 exit=exit_px, r=r, reason=reason))
    ledger["closed"].extend(closed_today)

    # 3. time exits (held past the doctrine's 15 trading days)
    time_exits = []
    for sym, rec in list(ledger["open"].items()):
        if sym in positions and bdays_between(rec["entry_date"],
                                              today) >= MAX_HOLD_BARS:
            broker.cancel_symbol_orders(sym)
            broker.close_position(sym)
            time_exits.append(sym)
            rec["closing"] = today            # reconciled next run

    # 4. new entries
    signals = scan(all_bars)
    placed, skipped = [], []
    for sig in signals:
        sym = sig["ticker"]
        if sym in positions or sym in ledger["open"]:
            skipped.append((sym, "already held"))
            continue
        if len(positions) + len(placed) >= MAX_OPEN:
            skipped.append((sym, "position cap"))
            continue
        qty = position_size(equity, sig["close"], sig["stop"])
        if qty < 1:
            skipped.append((sym, "size < 1 share at 1% risk"))
            continue
        order = broker.submit_bracket(sym, qty, sig["stop"], sig["target"])
        placed.append((sig, qty))
        ledger["open"][sym] = dict(
            entry_date=today, entry=sig["close"], entry_estimated=True,
            stop=sig["stop"], target=sig["target"], qty=qty,
            order_id=order.get("id"), setup="RS-02")

    save_ledger(ledger)
    option_review = review_open_options(load_open_options(), all_bars, today)
    return build_report(today, acct, positions, signals, placed, skipped,
                        closed_today, time_exits, ledger, option_review)


def build_report(today, acct, positions, signals, placed, skipped,
                 closed_today, time_exits, ledger,
                 option_review: str = "") -> str:
    lines = [f"PAPER SHADOW TRACK — RS-02 doctrine, as of {today}",
             f"paper equity: ${float(acct['equity']):,.2f}   "
             f"cash: ${float(acct['cash']):,.2f}"]
    # Volatility regime is CONTEXT ONLY — H8 is untested, so it gates
    # nothing. It tells the operator what environment the picks are in.
    ratio = ratio_on(load_term_structure(), today)
    if ratio is not None:
        lines.append(f"volatility regime: VIX/VIX3M {ratio:.3f} "
                     f"-> {regime_label(ratio)}  (context only, gates nothing)")
    lines.append("")

    lines.append(f"TODAY'S SIGNALS ({len(signals)}):")
    if not signals:
        lines.append("  none — no ticker passed breakout + regime + quality")
    for s in signals:
        lines += [f"  {s['ticker']}  close {s['close']:.2f}  "
                  f"stop {s['stop']:.2f}  target {s['target']:.2f}  "
                  f"(1R = {s['r_denom']:.2f})  score {s['score']}/10",
                  f"      {s['rationale']}",
                  f"      option guidance (Robinhood, per playbook): CALL, "
                  f"{DTE_RANGE[0]}-{DTE_RANGE[1]} DTE, delta ~{DELTA_TARGET}, "
                  f"strike near {s['close']:.0f}, spread <= "
                  f"{MAX_SPREAD_PCT:.0%}; exit on stop/target/15 sessions"]
    lines.append("")

    lines.append(f"PAPER ORDERS PLACED ({len(placed)}):")
    for sig, qty in placed:
        lines.append(f"  BUY {qty} {sig['ticker']} @ next open, "
                     f"bracket stop {sig['stop']:.2f} / "
                     f"target {sig['target']:.2f}")
    if not placed:
        lines.append("  none")
    for sym, why in skipped:
        lines.append(f"  skipped {sym}: {why}")
    if time_exits:
        lines.append(f"TIME EXITS SUBMITTED: {', '.join(time_exits)}")
    lines.append("")

    if closed_today:
        lines.append("CLOSED SINCE LAST RUN:")
        for t in closed_today:
            r_txt = f"{t['r']:+.2f}R" if t["r"] is not None else "r n/a"
            lines.append(f"  {t['ticker']}  {t['entry_date']} -> "
                         f"{t['exit_date']}  {r_txt}  ({t['reason']})")
        lines.append("")

    lines.append(f"OPEN POSITIONS ({len(positions)}):")
    for sym, p in sorted(positions.items()):
        rec = ledger["open"].get(sym, {})
        lines.append(f"  {sym}  qty {p['qty']}  "
                     f"unrealized ${float(p.get('unrealized_pl', 0)):+,.2f}  "
                     f"stop {rec.get('stop', '?')}  "
                     f"target {rec.get('target', '?')}  "
                     f"since {rec.get('entry_date', '?')}")
    if not positions:
        lines.append("  none")
    lines.append("")

    if option_review:
        lines += [option_review, ""]

    rs = [t["r"] for t in ledger["closed"] if t.get("r") is not None]
    if rs:
        wins = [r for r in rs if r > 0]
        lines += [f"CUMULATIVE RECORD: {len(rs)} closed | "
                  f"win rate {len(wins) / len(rs):.0%} | "
                  f"expectancy {sum(rs) / len(rs):+.3f}R | "
                  f"total {sum(rs):+.2f}R"]
        if len(rs) < 20:
            lines.append(f"  (n={len(rs)} — the track record starts meaning "
                         "something around 20+ closed trades)")
    else:
        lines.append("CUMULATIVE RECORD: no closed trades yet")
    lines += ["", "Paper account, fake money, §87 shadow track. Live "
              "execution remains co-pilot only — the operator's word, "
              "per trade, in Robinhood."]
    return "\n".join(lines)


def main() -> None:
    from .alpaca_paper import PaperBroker
    broker = PaperBroker()
    today = str(date.today())
    start = str(date.today() - timedelta(days=HISTORY_DAYS))
    all_bars = {}
    for t in required_tickers():
        try:
            all_bars[t] = fetch_bars(t, "1Day", start, today)
        except Exception as e:
            print(f"{t:<6} bars FAILED: {e}")
    text = run(broker, all_bars, today)
    print(text)
    path = save_report("paper_trading", text)
    print(f"\nReport saved: {path}")


if __name__ == "__main__":
    main()
