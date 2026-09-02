"""Autonomous daily runs — pre-open briefing and post-close trading.

Two scheduled runs (GitHub Actions), or manually from rs_options/:

    python -m paper.daily --preopen    # morning briefing, READ-ONLY
    python -m paper.daily              # post-close trading run

The pre-open run reports what yesterday's close implies and what is
already queued. It places no orders and never writes the ledger, so it
cannot double-trade against the evening run.

The post-close trading run:

1. Fetches fresh daily bars for the whole universe (Alpaca IEX, free).
2. Runs the ACTIVE_SETUPS doctrine point-in-time (`detect_all` live
   path): RS-02 breakout (200-day regime + 12-1 momentum quality) and,
   activated 2026-09-02, H-25 pullback-and-reclaim.
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
from mve.fundamentals import (load_fundamentals, next_expected_filing_window,
                              overlaps_earnings_window, trailing_net_income)
from mve.position_manager import (OpenPosition, evaluate_exit,
                                  format_exit_report)
from mve.report import save_report
from mve.rs_features import compute_features
from mve.setups import (ACTIVE_SETUPS, MAX_ENTRY_GAP, detect_all,
                        entry_limit_price)
from mve.significance import forward_track_line
from mve.universe import BENCHMARK, SECTOR_ETF, UNIVERSE, required_tickers
from mve.vix_regime import load_term_structure, ratio_on, regime_label
from mve.volume_profile import overhead_supply, point_of_control

from .growth_tracker import format_growth, growth_summary, load_equity_history
from .growth_tracker import record_equity
from .micro_sizing import (count_open_micro_positions, micro_cooloff_active,
                           micro_drawdown_paused, micro_fractional_size,
                           micro_fractional_warning, micro_mode_banner,
                           micro_override_active)
from .option_costs import collect as collect_option_costs
from .option_costs import format_costs
from .option_costs import record as record_option_costs
from .options_broker import contracts_to_buy, mid_price, select_contract

RISK_PCT = 0.01              # 1% of paper equity risked per trade
MAX_POSITION_PCT = 0.05      # 5% notional cap (mirrors HoneyDrip)
MAX_OPEN = 8                 # concurrent-position cap
# Same percentages the playbook's hard-limits table already states for
# equity notional, applied to options PREMIUM at risk (robinhood_copilot_
# playbook.md). CALIBRATE, not independently validated for this instrument.
MAX_OPTIONS_UNDERLYING_PCT = 0.05
MAX_OPTIONS_CLUSTER_PCT = 0.10
# Operator decision 2026-09-02: the paper account carried five
# hand-placed positions from before the shadow track existed; the
# operator chose to close the four losers and keep AAPL. Any ticker
# listed here that is held WITHOUT a ledger entry is closed on the
# next trading run. Manual positions never enter the ledger, so these
# closures change cash/equity but never the doctrine trade record.
# Remove a ticker from this tuple to hold it manually again.
MANUAL_CLOSE_TICKERS = ("IBM", "NVDA", "QQQ", "TGT")
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
                ticker=ticker, setup=hit["setup_id"], close=close, stop=stop,
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


def cluster_premium_at_risk(book: dict, cluster: str) -> float:
    """Sum of premium at risk (entry price x qty x 100) across open
    option positions whose underlying is in `cluster`."""
    return sum(rec["entry_price"] * rec["qty"] * 100.0
              for rec in book.values() if UNIVERSE.get(rec["ticker"]) == cluster)


def exceeds_underlying_cap(premium: float, equity: float) -> bool:
    return premium > equity * MAX_OPTIONS_UNDERLYING_PCT


def exceeds_cluster_cap(cluster_exposure: float, equity: float) -> bool:
    return cluster_exposure > equity * MAX_OPTIONS_CLUSTER_PCT


def run_option_cycle(broker, signals: list, all_bars: dict, today: str,
                     ledger: dict, fundamentals: dict | None = None) -> tuple:
    """Autonomous PAPER options: exit held contracts the doctrine says to
    close, then open new ones for today's signals.

    Options carry no bracket orders on Alpaca, so exits are not
    self-enforcing the way the equity stops are — this loop IS the exit
    mechanism, and it runs before entries so a freed slot can be reused.

    `fundamentals` (from `mve.fundamentals.load_fundamentals`) is used
    ONLY to tag each entry with the underlying's trailing net income —
    FWD-3 (docs/PREREGISTERED.md), recording only. It never gates or
    sizes a trade; omitting it (or an empty cache) tags every entry
    `None` and changes nothing else.
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
            # Exit sells the same way entries buy — limit at the mid, day
            # only (§38) — so a fresh quote is required here too. A stale
            # or missing quote means the sell is deferred to the next
            # run rather than falling back to a market order, the exact
            # thing this rule exists to prevent.
            try:
                mid = mid_price((broker.quotes(rec["ticker"]) or {})
                                .get(symbol, {}))
            except Exception as e:
                notes.append(f"{symbol}: EXIT due ({', '.join(verdict.reasons)}) "
                             f"but quote fetch failed ({e}) — retrying next run")
                continue
            if mid is None:
                notes.append(f"{symbol}: EXIT due ({', '.join(verdict.reasons)}) "
                             "but no tradable quote — retrying next run")
                continue
            broker.sell_to_close(symbol, rec["qty"], mid)
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
        # Earnings blackout (mechanism, not backtested — no historical
        # options data exists to measure it against, see RESEARCH_LOG.md).
        # An unknown cadence (fundamentals unset, or a ticker with under
        # two known filings — ETFs always land here) never gates; it can
        # only skip a trade it has real, if approximate, evidence for.
        if fundamentals:
            window = next_expected_filing_window(fundamentals, sig["ticker"],
                                                 today)
            expiry = date.fromisoformat(pick["expiration_date"])
            if overlaps_earnings_window(as_of, expiry, window):
                notes.append(
                    f"{sig['ticker']}: skipped — estimated earnings window "
                    f"{window[0]}..{window[1]} falls within the "
                    f"{pick['dte']}d hold (mechanism-based skip, see "
                    "docs/RESEARCH_LOG.md)")
                continue
        qty = contracts_to_buy(pick["mid"], equity, RISK_PCT)
        if qty < 1:
            notes.append(f"{sig['ticker']}: premium ${pick['mid'] * 100:,.0f} "
                         f"exceeds the {RISK_PCT:.0%} risk budget")
            continue
        # Portfolio-level options exposure — the same per-underlying and
        # per-cluster percentages the playbook's hard-limits table already
        # states for the equity side, applied here to premium at risk
        # rather than notional (playbook: "Max per underlying 5% of
        # equity", "Max per cluster ... 10% of equity"). At today's
        # RISK_PCT/MAX_OPEN these are non-binding defense-in-depth — a
        # single 1%-risk position can't reach 5%, and even 8 positions
        # (MAX_OPEN) in one cluster tops out at 8% of the 10% cap — but
        # they exist so a future change to either constant can't silently
        # reopen the concentration MAX_OPEN alone cannot see.
        premium = pick["mid"] * 100.0 * qty
        if exceeds_underlying_cap(premium, equity):
            notes.append(
                f"{sig['ticker']}: skipped — premium ${premium:,.0f} exceeds "
                f"the {MAX_OPTIONS_UNDERLYING_PCT:.0%}-of-equity "
                "per-underlying options cap")
            continue
        cluster = UNIVERSE.get(sig["ticker"])
        if cluster is not None:
            cluster_exposure = premium + cluster_premium_at_risk(book, cluster)
            if exceeds_cluster_cap(cluster_exposure, equity):
                notes.append(
                    f"{sig['ticker']}: skipped — {cluster} cluster options "
                    f"exposure would reach ${cluster_exposure:,.0f}, over "
                    f"the {MAX_OPTIONS_CLUSTER_PCT:.0%}-of-equity cluster cap")
                continue
        broker.buy_to_open(pick["symbol"], qty, pick["mid"])
        net_income = (trailing_net_income(fundamentals, sig["ticker"], today)
                     if fundamentals else None)
        book[pick["symbol"]] = dict(
            ticker=sig["ticker"], qty=qty, entry_price=pick["mid"],
            expiry=pick["expiration_date"], strike=float(pick["strike_price"]),
            entry_date=today, invalidation_price=sig["stop"],
            entry_underlying=sig["close"], basis=pick["basis"],
            delta=pick["delta"], spread_pct=round(pick["spread_pct"], 4),
            # FWD-3, RECORDED ONLY (docs/PREREGISTERED.md) — never reads
            # back into gating or sizing above.
            fundamental_net_income=net_income)
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
                     f"[{basis}, spread {pick['spread_pct']:.1%}, "
                     f"OI {pick['open_interest']}]")
        ni = book.get(pick["symbol"], {}).get("fundamental_net_income")
        tag = (f"${ni:,.0f} trailing net income" if ni is not None
              else "fundamentals unknown (run python -m mve.fundamentals)")
        lines.append(f"    FWD-3 tag: {tag} — recorded only, does not "
                     "gate or size this trade")
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

    # Growth tracking: one snapshot per session, reporting only. This
    # does not feed position sizing anywhere — sizing reads equity fresh
    # from the broker each run regardless (see paper/growth_tracker.py).
    record_equity(today, equity)
    growth = growth_summary(load_equity_history())

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

    # 1b. entries that never filled — the H15a cancellation actually
    # happening. An unfilled order has NO position, so without this it
    # would fall into the closure branch below and be recorded as a
    # trade that exited at an unknown price. It is not a trade at all.
    gap_cancelled = []
    for sym, rec in list(ledger["open"].items()):
        if sym in positions or not rec.get("entry_estimated"):
            continue
        if rec["entry_date"] == today or not rec.get("order_id"):
            continue                      # queued tonight, not yet open
        try:
            o = broker.order(rec["order_id"])
        except Exception:
            continue                      # unknown state: leave it alone
        if o.get("filled_avg_price"):
            continue                      # handled in step 1
        if str(o.get("status", "")).lower() in (
                "new", "accepted", "pending_new", "held", "partially_filled"):
            continue                      # still working
        broker.cancel_symbol_orders(sym)
        ledger["open"].pop(sym)
        gap_cancelled.append((sym, rec.get("entry_cap"),
                              rec.get("signal_close")))

    # 2. reconcile closures (bracket legs fired since last run)
    # `entry_estimated` still True means no fill was ever confirmed, so
    # the symbol is a working order, not a position that closed. Booking
    # one here would invent a round trip that never happened.
    closed_today = []
    for sym in [s for s, r in list(ledger["open"].items())
                if s not in positions and not r.get("entry_estimated")]:
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
                                 exit=exit_px, r=r, reason=reason,
                                 micro_override=rec.get("micro_override",
                                                        False)))
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

    # 3b. micro fractional exits — a fractional entry carries no bracket
    # (Alpaca rejects fractional quantities in bracket orders), so for
    # these positions this loop IS the stop and the target, evaluated at
    # the close like the options cycle. The sell is a market day order:
    # the universe is liquid large caps, the notional is tens of
    # dollars, and a certain exit beats pennies of spread when the rule
    # says the trade is over (the philosophy's market-order prohibition
    # is scoped to thin securities). Booked by the step-2 reconciliation
    # next run, same as time exits.
    micro_exits = []
    for sym, rec in list(ledger["open"].items()):
        if not rec.get("fractional") or rec.get("entry_estimated") \
                or sym not in positions or rec.get("closing"):
            continue
        bars = all_bars.get(sym)
        if bars is None or bars.empty:
            continue
        close = float(bars["close"].iloc[-1])
        reason = ("stop" if close <= rec["stop"]
                  else "target" if close >= rec["target"] else None)
        if reason:
            broker.cancel_symbol_orders(sym)
            broker.close_position(sym)
            rec["closing"] = today
            micro_exits.append((sym, close, reason))
    micro_exit_lines = [
        f"  MICRO EXIT: {sym} {reason.upper()} at close ${close:.2f} — "
        "market sell submitted; booked by next run's reconciliation."
        for sym, close, reason in micro_exits]

    # 3c. operator-directed cleanup of MANUAL positions (see
    # MANUAL_CLOSE_TICKERS). A listed ticker held without a ledger
    # entry is hand-placed, sits outside every stop/target, and eats a
    # MAX_OPEN slot — close it. Step 2 only books ledgered symbols, so
    # nothing here ever enters the doctrine record. Idempotent once
    # the position is gone. The closing position still counts against
    # MAX_OPEN for the rest of THIS run (the fill lands after the
    # close); the slot frees on the next run.
    manual_closes = []
    for sym in MANUAL_CLOSE_TICKERS:
        if sym in positions and sym not in ledger["open"]:
            try:
                broker.cancel_symbol_orders(sym)
                broker.close_position(sym)
                manual_closes.append(sym)
            except Exception:
                pass                      # retried next run; never fatal

    # 4. new entries
    signals = scan(all_bars)
    micro = micro_override_active(equity)
    micro_warnings = ([micro_mode_banner(equity)] + micro_exit_lines
                      if micro else micro_exit_lines)
    fundamentals = load_fundamentals()
    # Fixed-capital survival gates (docs/FIXED_CAPITAL_PHILOSOPHY.md,
    # integrated 2026-08-27): each can only PREVENT a micro entry,
    # never force or enlarge one, so the non-martingale guarantee is
    # untouched. None applies to standard doctrine sizing.
    micro_paused = None
    if micro:
        if micro_drawdown_paused(load_equity_history()):
            micro_paused = ("drawdown pause: equity is 10%+ below its "
                            "recent peak — no new micro entries until it "
                            "recovers (playbook freeze, applied to the "
                            "micro book)")
        elif micro_cooloff_active(ledger, today):
            micro_paused = ("cooling-off: last two micro trades were "
                            "losses — no new micro entries for "
                            "5 trading days (adapted two-loss shutdown)")
        if micro_paused:
            micro_warnings.append("  " + micro_paused.upper())
    placed, skipped = [], []
    for sig in signals:
        sym = sig["ticker"]
        if sym in positions or sym in ledger["open"]:
            skipped.append((sym, "already held"))
            continue
        if len(positions) + len(placed) >= MAX_OPEN:
            skipped.append((sym, "position cap"))
            continue
        if micro:
            # Operator-authorized override for accounts too small for
            # doctrine sizing — now the fixed-capital fractional
            # doctrine (see paper/micro_sizing.py). Never applied to
            # options.
            if micro_paused:
                skipped.append((sym, micro_paused))
                continue
            if count_open_micro_positions(ledger) >= 1:
                skipped.append((sym, "micro: one position at a time "
                                "(fixed-capital doctrine)"))
                continue
            # No overnight binary-event exposure during validation: skip
            # when the estimated earnings window (filing-cadence proxy —
            # same mechanism as the options gate) overlaps the expected
            # hold. Unknown cadence never gates.
            window = next_expected_filing_window(fundamentals, sym, today) \
                if fundamentals else None
            hold_end = date.fromisoformat(today) + timedelta(days=30)
            if overlaps_earnings_window(date.fromisoformat(today), hold_end,
                                        window):
                skipped.append((sym, "micro: estimated earnings window "
                                f"{window[0]}..{window[1]} inside the "
                                "expected hold — no binary-event "
                                "exposure during validation"))
                continue
            qty = micro_fractional_size(equity, sig["close"], sig["stop"])
            if qty <= 0:
                skipped.append((sym, "micro: no size satisfies the risk "
                                "ceiling + reserve floor + broker "
                                "minimum — no trade IS the decision"))
                continue
            micro_warnings += micro_fractional_warning(
                sym, equity, qty, sig["close"], sig["stop"])
        else:
            qty = position_size(equity, sig["close"], sig["stop"])
            if qty < 1:
                skipped.append((sym, "size < 1 share at 1% risk"))
                continue
        # H15a (ADOPTED): cap what doctrine will pay at the open. A
        # limit here IS the backtested cancellation — it fills at the
        # open when the open is at or below the cap, and does not fill
        # when the open gapped through.
        cap = entry_limit_price(sig["close"])
        if micro:
            try:
                order = broker.submit_fractional_limit(sym, qty, cap)
            except Exception as e:      # asset not fractionable, etc.
                skipped.append((sym, f"micro: fractional order rejected "
                                f"({e}) — no trade"))
                continue
        else:
            order = broker.submit_bracket(sym, qty, sig["stop"],
                                          sig["target"], limit_price=cap)
        placed.append((sig, qty))
        ledger["open"][sym] = dict(
            entry_date=today, entry=sig["close"], entry_estimated=True,
            entry_cap=cap, signal_close=sig["close"],
            stop=sig["stop"], target=sig["target"], qty=qty,
            order_id=order.get("id"), setup=sig["setup"],
            micro_override=micro, fractional=micro)

    # ── autonomous PAPER options (the co-pilot side, now hands-off) ──
    opt = ([], [], ["options disabled: broker has no options support"])
    if hasattr(broker, "option_positions"):
        try:
            opt = run_option_cycle(broker, signals, all_bars, today, ledger,
                                   fundamentals=fundamentals)
        except Exception as e:                  # never lose the equity run
            opt = ([], [], [f"option cycle FAILED: {e}"])

    # Cost recorder: prices the contract doctrine WOULD buy, using market
    # data only. No order, no buying power, no account permissions — so
    # it runs even when the options cycle above cannot. This is the only
    # measurement the project has of what the overlay actually costs.
    try:
        cost_rows = collect_option_costs(broker, signals, today)
        record_option_costs(cost_rows)
    except Exception:
        cost_rows = []              # never break the trading run

    save_ledger(ledger)
    option_review = review_open_options(load_open_options(), all_bars, today)
    return build_report(today, acct, positions, signals, placed, skipped,
                        closed_today, time_exits, ledger, option_review,
                        option_cycle=opt, gap_cancelled=gap_cancelled,
                        cost_rows=cost_rows, equity=equity,
                        micro_warnings=micro_warnings, growth=growth,
                        manual_closes=manual_closes)


def build_report(today, acct, positions, signals, placed, skipped,
                 closed_today, time_exits, ledger,
                 option_review: str = "", option_cycle=None,
                 gap_cancelled=None, cost_rows=None,
                 equity: float | None = None,
                 micro_warnings=None, growth=None,
                 manual_closes=None) -> str:
    lines = [f"PAPER SHADOW TRACK — {'/'.join(ACTIVE_SETUPS)} doctrine, "
             f"as of {today}",
             f"paper equity: ${float(acct['equity']):,.2f}   "
             f"cash: ${float(acct['cash']):,.2f}"]
    if growth:
        lines += ["", format_growth(growth)]
    if micro_warnings:
        lines += ["", *micro_warnings]
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
        lines += [f"  {s['ticker']}  [{s.get('setup', 'RS-02')}]  "
                  f"close {s['close']:.2f}  "
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

    if cost_rows is not None:
        lines += [format_costs(cost_rows, equity), ""]

    lines.append(f"PAPER ORDERS PLACED ({len(placed)}):")
    for sig, qty in placed:
        lines.append(f"  BUY {qty} {sig['ticker']} @ next open, "
                     f"limit {entry_limit_price(sig['close']):.2f} "
                     f"(H15a cap, {MAX_ENTRY_GAP:.0%} over the "
                     f"{sig['close']:.2f} close), "
                     f"bracket stop {sig['stop']:.2f} / "
                     f"target {sig['target']:.2f}")
    if not placed:
        lines.append("  none")
    for sym, why in skipped:
        lines.append(f"  skipped {sym}: {why}")
    # A cancellation nobody is told about is a trade nobody knows was
    # skipped — the adopted rule reports every time it fires.
    if gap_cancelled:
        lines.append(f"H15a GAP CANCELLATIONS ({len(gap_cancelled)}) — the "
                     "open ran past the doctrine's cap, so the order was "
                     "abandoned rather than chased:")
        for sym, cap, close in gap_cancelled:
            detail = (f" (cap {cap:.2f} vs {close:.2f} close)"
                      if cap and close else "")
            lines.append(f"  cancelled {sym}{detail}")
    if time_exits:
        lines.append(f"TIME EXITS SUBMITTED: {', '.join(time_exits)}")
    if manual_closes:
        lines.append(f"MANUAL POSITIONS CLOSED ({len(manual_closes)}) — "
                     "operator decision 2026-09-02, hand-placed positions "
                     "outside the doctrine (not booked as trades): "
                     + ", ".join(manual_closes))
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
        lines.append(forward_track_line(len(rs), len(wins) / len(rs)))
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
    for sym, rec in sorted(ledger["open"].items()):
        if rec.get("entry_estimated") and rec.get("entry_cap"):
            lines.append(f"  {sym} limit {rec['entry_cap']:.2f} — H15a cap "
                         f"({MAX_ENTRY_GAP:.0%} over the signal close). "
                         "If the open gaps past it the order does not fill "
                         "and is cancelled.")

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
