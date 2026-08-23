"""Autonomous daily runs — pre-open briefing and post-close trading.

Two scheduled runs (GitHub Actions), or manually from rs_options/:

    python -m paper.daily --preopen    # morning briefing, READ-ONLY
    python -m paper.daily              # post-close trading run

The pre-open run reports what yesterday's close implies and what is
already queued. It places no orders and never writes the ledger, so it
cannot double-trade against the evening run.

The post-close trading run:

1. Fetches fresh daily bars for the whole universe (Alpaca IEX, free).
2. Runs the adopted RS-02 doctrine point-in-time: detector + 200-day
   regime + 12-1 momentum quality (`detect_all` live path).
3. PAPER-trades each surviving signal on Alpaca's paper account as the
   UNDERLYING equity: market buy queued for the next open (matching the
   backtester's next-open entry), bracket stop at the invalidation
   price and target at +3R. Time exit after 15 trading days.
4. PAPER-trades OPTIONS on the same signals, autonomously: selects the
   contract (delta when greeks are available, moneyness proxy when not),
   buys limit-at-mid, and sells when position_manager says to. Options
   carry no bracket orders, so this loop IS the exit mechanism. This is
   also the only place the project measures option P&L at all.
5. Reviews the operator's held Robinhood options (paper/open_options.json)
   against the same exit rules — the co-pilot side of the doctrine.
6. Writes docs/reports/paper_trading.txt — the operator-facing report:
   today's picks with entry/stop/target and the playbook's option
   guidance (for discretionary Robinhood execution), the position
   review, open positions, closed trades in R, and the cumulative
   record.

Scope (§87): fake money throughout. Live execution stays co-pilot —
the operator's word, per trade, in Robinhood. Nothing here can reach a
live account: alpaca_paper.PaperBroker hard-codes the paper endpoint.
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
from mve.volume_profile import overhead_supply, point_of_control

from .options_broker import contracts_to_buy, select_contract

RISK_PCT = 0.01              # 1% of paper equity risked per trade
MAX_POSITION_PCT = 0.05      # 5% notional cap (mirrors HoneyDrip)
MAX_OPEN = 8                 # concurrent-position cap
MIN_BARS = 260               # doctrine needs 253+ bars (12-1 momentum)
HISTORY_DAYS = 420           # calendar days of bars to fetch
MAX_BAR_AGE_DAYS = 4         # pre-open: yesterday's close is
                             # correct; a week old is broken
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
            overhead = overhead_supply(bars)
            signals.append(dict(
                ticker=ticker, close=close, stop=stop,
                target=round(close + TARGET_R * (close - stop), 2),
                r_denom=round(close - stop, 2),
                score=hit["opportunity_score"], rationale=hit["rationale"],
                overhead=overhead, poc=point_of_control(bars)))
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
                                  else None),
                score=(int(row["score"]) if row.get("score") is not None
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


def run_option_cycle(broker, signals: list, all_bars: dict, today: str,
                     ledger: dict) -> tuple:
    """Autonomous PAPER options: exit held contracts the doctrine says to
    close, then open new ones for today's signals.

    Options carry no bracket orders on Alpaca, so exits are not
    self-enforcing the way the equity stops are — this loop IS the exit
    mechanism, and it runs before entries so a freed slot can be reused.
    """
    as_of = date.fromisoformat(today)
    book = ledger.setdefault("options", {})
    held = broker.option_positions()
    closed, opened, notes = [], [], []

    # ── exits first ──────────────────────────────────────────────────
    for symbol in list(book):
        rec = book[symbol]
        if symbol not in held:                      # already gone
            closed.append((symbol, rec, None, "reconciled"))
            del book[symbol]
            continue
        bars = all_bars.get(rec["ticker"])
        if bars is None or bars.empty:
            notes.append(f"{symbol}: no underlying bars — NOT evaluated")
            continue
        position = OpenPosition(
            ticker=rec["ticker"], contract=symbol, quantity=rec["qty"],
            entry_price=rec["entry_price"],
            expiry=date.fromisoformat(rec["expiry"]),
            invalidation_price=rec["invalidation_price"],
            entry_date=date.fromisoformat(rec["entry_date"]),
            entry_underlying=rec["entry_underlying"])
        verdict = evaluate_exit(position, float(bars["close"].iloc[-1]), as_of)
        if verdict.must_exit:
            broker.sell_to_close(symbol, rec["qty"])
            closed.append((symbol, rec, held[symbol], verdict.reasons))
            del book[symbol]

    # ── entries ──────────────────────────────────────────────────────
    equity = float(broker.account()["equity"])
    open_count = len(held) - len(closed)
    for sig in signals:
        if open_count >= MAX_OPEN:
            break
        if any(r["ticker"] == sig["ticker"] for r in book.values()):
            continue                                # one contract per name
        try:
            contracts = broker.contracts(sig["ticker"], as_of)
            quotes = broker.quotes(sig["ticker"])
        except Exception as e:
            notes.append(f"{sig['ticker']}: chain unavailable ({e})")
            continue
        pick = select_contract(contracts, sig["close"], as_of, quotes)
        if pick is None:
            notes.append(f"{sig['ticker']}: no contract met DTE/spread/delta")
            continue
        qty = contracts_to_buy(pick["mid"], equity, RISK_PCT)
        if qty < 1:
            notes.append(f"{sig['ticker']}: premium ${pick['mid'] * 100:,.0f} "
                         f"exceeds the {RISK_PCT:.0%} risk budget")
            continue
        broker.buy_to_open(pick["symbol"], qty, pick["mid"])
        book[pick["symbol"]] = dict(
            ticker=sig["ticker"], qty=qty, entry_price=pick["mid"],
            expiry=pick["expiration_date"], strike=float(pick["strike_price"]),
            entry_date=today, invalidation_price=sig["stop"],
            entry_underlying=sig["close"], basis=pick["basis"],
            delta=pick["delta"], spread_pct=round(pick["spread_pct"], 4))
        opened.append((pick, qty))
        open_count += 1

    return opened, closed, notes


def format_option_cycle(cycle, ledger: dict) -> str:
    """Operator-facing summary of the autonomous options track."""
    opened, closed, notes = cycle
    book = ledger.get("options", {})
    lines = ["PAPER OPTIONS (Alpaca, autonomous):"]

    for pick, qty in opened:
        basis = ("delta %.2f" % pick["delta"] if pick["delta"] is not None
                 else "moneyness proxy — no greeks in this data plan")
        lines.append(f"  BOUGHT {qty}x {pick['symbol']}  "
                     f"@ ${pick['mid']:.2f} (${pick['mid'] * 100 * qty:,.0f})  "
                     f"{pick['dte']}d  strike {float(pick['strike_price']):.2f}  "
                     f"[{basis}, spread {pick['spread_pct']:.1%}]")
    for symbol, rec, position, reasons in closed:
        pnl = ""
        if position:
            pnl = f"  P&L ${float(position.get('unrealized_pl', 0)):+,.2f}"
        why = (", ".join(reasons) if isinstance(reasons, tuple) else reasons)
        lines.append(f"  SOLD   {rec['qty']}x {symbol}{pnl}  ({why})")
    if not opened and not closed:
        lines.append("  no option trades today")

    if book:
        lines.append(f"  holding {len(book)}:")
        for symbol, rec in sorted(book.items()):
            lines.append(f"    {symbol}  {rec['qty']}x @ "
                         f"${rec['entry_price']:.2f}  since {rec['entry_date']}"
                         f"  stop-if-underlying <= "
                         f"{rec['invalidation_price']:.2f}")
    for note in notes:
        lines.append(f"  note: {note}")
    return "\n".join(lines)


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

    # ── autonomous PAPER options (the co-pilot side, now hands-off) ──
    opt = ([], [], ["options disabled: broker has no options support"])
    if hasattr(broker, "option_positions"):
        try:
            opt = run_option_cycle(broker, signals, all_bars, today, ledger)
        except Exception as e:                  # never lose the equity run
            opt = ([], [], [f"option cycle FAILED: {e}"])

    save_ledger(ledger)
    option_review = review_open_options(load_open_options(), all_bars, today)
    return build_report(today, acct, positions, signals, placed, skipped,
                        closed_today, time_exits, ledger, option_review,
                        option_cycle=opt)


def build_report(today, acct, positions, signals, placed, skipped,
                 closed_today, time_exits, ledger,
                 option_review: str = "", option_cycle=None) -> str:
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
                  ("      volume profile: "
                   + (f"{s['overhead']:.0%} of 60d volume sits ABOVE here"
                      if s.get("overhead") is not None else "not computable")
                   + (f", heaviest at {s['poc']:.2f}" if s.get("poc") else "")
                   + "  (context only, gates nothing)"),
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

    if option_cycle:
        lines += [format_option_cycle(option_cycle, ledger), ""]

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


def bars_are_current(all_bars: dict, today: str,
                     max_age_days: int = MAX_BAR_AGE_DAYS) -> bool:
    """Pre-open: the newest bar is YESTERDAY's close, which is exactly the
    point-in-time information the signal is allowed to use. Guard only
    against genuinely stale data (a long weekend is fine, a week is not)."""
    bench = all_bars.get(BENCHMARK)
    if bench is None or bench.empty:
        return False
    age = (date.fromisoformat(today)
           - date.fromisoformat(str(bench["trade_date"].iloc[-1]))).days
    return 0 <= age <= max_age_days


def preopen_report(broker, all_bars: dict, today: str) -> str:
    """Morning briefing, BEFORE the bell. Read-only by construction: it
    places no orders and never writes the ledger, so it cannot
    double-trade against the evening run. It tells the operator what the
    close-of-yesterday data implies and what is already queued."""
    if not bars_are_current(all_bars, today):
        return (f"PRE-OPEN SCAN — {today}\n\n"
                "Bars are stale or missing — no briefing. The evening run "
                "will retry with fresh data.")

    bench_date = str(all_bars[BENCHMARK]["trade_date"].iloc[-1])
    acct = broker.account()
    positions = broker.positions()
    ledger = load_ledger()
    signals = scan(all_bars)

    lines = [f"PRE-OPEN SCAN — {today} (signals from the {bench_date} close)",
             f"paper equity: ${float(acct['equity']):,.2f}", ""]

    ratio = ratio_on(load_term_structure(), today)
    if ratio is not None:
        lines += [f"volatility regime: VIX/VIX3M {ratio:.3f} -> "
                  f"{regime_label(ratio)}  (context only, gates nothing)", ""]

    lines.append(f"CANDIDATES FOR TODAY ({len(signals)}):")
    if not signals:
        lines.append("  none — nothing passed breakout + regime + quality")
    for s in signals:
        held = " [already held]" if s["ticker"] in positions else ""
        lines += [f"  {s['ticker']}  ref close {s['close']:.2f}  "
                  f"stop {s['stop']:.2f}  target {s['target']:.2f}  "
                  f"(1R = {s['r_denom']:.2f})  score {s['score']}/10{held}",
                  f"      {s['rationale']}",
                  ("      volume profile: "
                   + (f"{s['overhead']:.0%} of 60d volume sits ABOVE here"
                      if s.get("overhead") is not None else "not computable")
                   + (f", heaviest at {s['poc']:.2f}" if s.get("poc") else "")
                   + "  (context only, gates nothing)"),
                  f"      option guidance: CALL, {DTE_RANGE[0]}-{DTE_RANGE[1]} "
                  f"DTE, delta ~{DELTA_TARGET}, strike near "
                  f"{s['close']:.0f}, spread <= {MAX_SPREAD_PCT:.0%}"]
    lines.append("")

    queued = [s for s in ledger["open"].values() if s.get("entry_estimated")]
    lines.append(f"ORDERS QUEUED FOR THE OPEN ({len(queued)}): "
                 + (", ".join(sorted(k for k, v in ledger["open"].items()
                                     if v.get("entry_estimated"))) or "none"))

    lines += ["", f"OPEN POSITIONS ({len(positions)}):"]
    for sym, p in sorted(positions.items()):
        rec = ledger["open"].get(sym, {})
        lines.append(f"  {sym}  qty {p['qty']}  "
                     f"unrealized ${float(p.get('unrealized_pl', 0)):+,.2f}  "
                     f"stop {rec.get('stop', '?')} / "
                     f"target {rec.get('target', '?')}")
    if not positions:
        lines.append("  none")

    lines += ["", review_open_options(load_open_options(), all_bars, today),
              "", "Read-only briefing — no orders placed by this run. "
              "The evening run trades and keeps the record."]
    return "\n".join(lines)


def main() -> None:
    import sys
    from .options_broker import PaperOptionsBroker
    preopen = "--preopen" in sys.argv
    broker = PaperOptionsBroker()
    today = str(date.today())
    start = str(date.today() - timedelta(days=HISTORY_DAYS))
    all_bars = {}
    for t in required_tickers():
        try:
            all_bars[t] = fetch_bars(t, "1Day", start, today)
        except Exception as e:
            print(f"{t:<6} bars FAILED: {e}")
    if preopen:
        text = preopen_report(broker, all_bars, today)
        name = "premarket_scan"
    else:
        text = run(broker, all_bars, today)
        name = "paper_trading"
    print(text)
    print(f"\nReport saved: {save_report(name, text)}")


if __name__ == "__main__":
    main()
