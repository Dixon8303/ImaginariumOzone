"""Autonomous daily runs — pre-open briefing and post-close trading.

Two scheduled runs (GitHub Actions), or manually from rs_options/:

    python -m paper.daily --preopen    # morning briefing, READ-ONLY
    python -m paper.daily              # post-close trading run

    python -m paper.daily --session-date=2026-09-25   # name the session

`--session-date` exists because a scheduled fire can be delivered after
midnight UTC while still reporting the previous session; see
`session_date_from_argv`. It defaults to the runner's date.

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
import re
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
from rs_options_risk.config import HardRiskConstants

from .growth_tracker import format_growth, growth_summary, load_equity_history
from .growth_tracker import record_equity
from .micro_sizing import (count_open_micro_positions, micro_cooloff_active,
                           micro_drawdown_paused, micro_fractional_size,
                           micro_fractional_warning, micro_mode_banner,
                           micro_override_active)
from .option_costs import collect as collect_option_costs
from .option_costs import format_costs
from .option_costs import record as record_option_costs
from .options_broker import (contracts_to_buy, mid_price, parse_occ_symbol,
                             select_contract)

RISK_PCT = 0.01              # 1% of paper equity risked per trade
# Spec §4 account limits, read from the risk engine's own constants so
# this trader and the co-pilot gate cannot drift apart. Until 2026-11-18
# neither was enforced here at standard equity — only the micro path
# checked drawdown — while the account sat 8.1% below its peak. Both
# stop NEW entries only: exits, reconciliation and cleanup always run,
# because refusing to sell is not a way to reduce risk.
_HARD_LIMITS = HardRiskConstants()
DRAWDOWN_FREEZE_PCT = _HARD_LIMITS.max_portfolio_drawdown_pct   # → FREEZE
DAILY_LOSS_HALT_PCT = _HARD_LIMITS.daily_loss_limit_pct         # → HALT
# A FREEZE holds until the operator re-arms (spec §60 Level 4). Re-arming
# means: set "rearmed_on" in this file to a date, which restarts the
# peak-equity count from that date. Editable directly on github.com.
REARM_PATH = os.path.join("paper", "risk_rearm.json")
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
# Operator decision 2026-11-18: close the positions the option cycle
# orphaned before its exit fix. Until then it erased a contract from the
# book the moment it SENT a sell, so a limit that never filled left the
# position in the account with no rule watching it; and a second evening
# run dropped a not-yet-filled buy as "reconciled", then bought it again.
# The stock lots arrived when orphaned calls expired in the money
# (inferred from report timing — no report records the exercise). None
# of these is in the ledger, so closing them changes cash and equity but
# never the doctrine trade record.
#
# DAL and CVX are listed for the same reason PFE and XOM already hold
# shares: their calls expire 2026-11-20, DAL's in the money, and if the
# last sell does not fill, exercise delivers shares nothing manages.
# A ledger-managed symbol is never touched. The decision covers these
# lots only, so it ends on ORPHAN_CLOSE_UNTIL (after the PFE 12-18 call
# could have been exercised); past it, anything left is reported
# UNMANAGED instead of being sold under this label.
ORPHAN_CLOSE = {
    "CVX261120C00220000": "exit sell never filled, then forgotten",
    "DAL261120C00080000": "exit sell never filled, then forgotten",
    "XOM261120C00185000": "exit sell never filled, then forgotten",
    "KO270115C00097500": "dropped from the book, still held",
    "PFE261218C00031000": "dropped from the book, still held",
    "PFE": "shares from an orphaned call expiring in the money",
    "XOM": "shares from an orphaned call expiring in the money",
    "DAL": "shares, if the orphaned DAL call is exercised",
    "CVX": "shares, if the orphaned CVX call is exercised",
}
ORPHAN_CLOSE_UNTIL = "2026-12-31"
# Alpaca order states that mean "not finished yet".
WORKING_ORDER_STATES = ("new", "accepted", "pending_new", "held",
                        "partially_filled", "accepted_for_bidding",
                        "pending_replace", "pending_cancel")
MIN_BARS = 260              # doctrine needs 253+ bars (12-1 momentum)
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


# OCC option symbol: root, 6-digit expiry, C/P, 8-digit strike —
# e.g. BAC261016C00062500. A plain equity ticker never matches.
OCC_SYMBOL = re.compile(r"^[A-Z]{1,6}\d{6}[CP]\d{8}$")


def is_option_symbol(sym: str) -> bool:
    return bool(OCC_SYMBOL.match(str(sym)))


def equity_positions(positions: dict) -> dict:
    """Stock-only view of the broker's position book.

    Alpaca's /v2/positions returns equity AND option contracts in one
    list. Anything that counts stock slots must filter first: the
    options overlay keeps its own book and enforces its own cap in
    run_option_cycle, so counting contracts twice silently shrinks the
    stock doctrine. Prefers the broker's own asset_class when present
    and falls back to the OCC symbol shape, so it holds for brokers
    (and test fakes) that omit the field.
    """
    return {s: p for s, p in positions.items()
            if "option" not in str(p.get("asset_class", "")).lower()
            and not is_option_symbol(s)}


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


# ── account-level limits (spec §4: drawdown FREEZE, daily-loss HALT) ──
def load_rearm_date(path: str | None = None) -> str | None:
    """The operator's re-arm date as YYYY-MM-DD, or None. A malformed
    file raises: a freeze that silently lifts because the file could not
    be read would defeat the point of having one. The value is
    normalised because it is compared against growth-log dates as text,
    and Python also accepts forms like "20261118" that sort wrongly."""
    path = path or REARM_PATH
    if not os.path.exists(path):
        return None
    with open(path) as f:
        value = json.load(f).get("rearmed_on")
    if not value:
        return None
    if not isinstance(value, str):
        raise ValueError(f"rearmed_on must be a date in quotes, got {value!r}")
    return date.fromisoformat(value).isoformat()


def account_gate(history: list, equity: float, today: str,
                 rearmed_on: str | None = None,
                 frozen_since: str | None = None) -> dict:
    """Whether NEW entries are allowed this session.

    Peak is the highest recorded equity since inception (or since the
    operator's re-arm date) including this run's. The daily loss is
    measured against the last session recorded BEFORE today, so a
    second run in the same evening reads the same baseline as the first.

    A FREEZE latches (spec §60 Level 4). Once tripped it is recorded as
    `frozen_since` and holds — even if equity climbs back under the line
    — until the operator sets a re-arm date on or after it. Returns the
    `frozen_since` the caller must persist.
    """
    if rearmed_on and rearmed_on > today:
        raise ValueError(f"rearmed_on {rearmed_on} is after the session "
                         f"{today} — a future date would switch the freeze "
                         "off until then")
    since = [h for h in history
             if (not rearmed_on or h["date"] >= rearmed_on)
             and h["date"] <= today]
    peak_row = max(since, key=lambda h: h["equity"], default=None)
    peak, peak_date = equity, today
    if peak_row and peak_row["equity"] > equity:
        peak, peak_date = peak_row["equity"], peak_row["date"]
    drawdown = (peak - equity) / peak if peak > 0 else 0.0

    before = [h for h in history if h["date"] < today]
    prev = before[-1]["equity"] if before else None
    daily_loss = ((prev - equity) / prev) if prev else 0.0

    # Rounded before comparing: equity is in cents, and float division
    # puts an exact 10.00% drawdown at 0.09999…, which must still freeze.
    tripped = round(drawdown, 6) >= DRAWDOWN_FREEZE_PCT
    latched = bool(frozen_since) and (not rearmed_on
                                      or rearmed_on < frozen_since)
    frozen = tripped or latched
    if latched:
        since_date = frozen_since
    elif tripped:
        since_date = today
    else:
        since_date = None
    halted = round(daily_loss, 6) >= DAILY_LOSS_HALT_PCT
    reason = None
    if frozen:
        reason = (f"FREEZE since {since_date}: equity is {drawdown:.1%} "
                  f"below its ${peak:,.2f} peak ({peak_date}); the limit is "
                  f"{DRAWDOWN_FREEZE_PCT:.0%} — no new entries until the "
                  f"operator re-arms in {REARM_PATH}")
    elif halted:
        reason = (f"HALT: down {daily_loss:.1%} on the session, at or past "
                  f"the {DAILY_LOSS_HALT_PCT:.0%} daily limit — no new "
                  "entries today")
    return dict(blocked=bool(reason), frozen=frozen, halted=halted,
                reason=reason, drawdown=drawdown, peak=peak,
                peak_date=peak_date, daily_loss=daily_loss, prev=prev,
                frozen_since=since_date)


def resolve_gate(ledger: dict, history: list, equity: float,
                 today: str) -> dict:
    """account_gate with the operator's re-arm file and the persisted
    latch, failing closed on entries — never on exits — when either the
    file or the history cannot be used. Updates ledger["risk_freeze"]."""
    frozen_since = (ledger.get("risk_freeze") or {}).get("since")
    problem = None
    try:
        rearmed_on = load_rearm_date()
        gate = account_gate(history, equity, today, rearmed_on, frozen_since)
    except Exception as e:
        problem = e
        try:        # still measure the account, without the bad re-arm
            gate = account_gate(history, equity, today, None, frozen_since)
        except Exception:
            gate = dict(frozen=False, halted=False, drawdown=0.0,
                        peak=equity, peak_date=today, daily_loss=0.0,
                        prev=None, frozen_since=frozen_since)
    if gate["frozen_since"]:
        ledger["risk_freeze"] = {"since": gate["frozen_since"]}
    else:
        ledger.pop("risk_freeze", None)
    if problem is not None:
        gate["blocked"] = True
        gate["reason"] = (f"LIMITS UNREADABLE: {problem} — no new entries "
                          f"until {REARM_PATH} and the growth log can be "
                          "read")
    return gate


def format_account_gate(gate: dict) -> str:
    line = (f"RISK LIMITS: drawdown {gate['drawdown']:.1%} of the "
            f"{DRAWDOWN_FREEZE_PCT:.0%} freeze (peak ${gate['peak']:,.2f} "
            f"on {gate['peak_date']})")
    if gate["prev"] is not None:
        line += (f" | session {0.0 - gate['daily_loss'] + 0.0:+.1%} vs the "
                 f"{DAILY_LOSS_HALT_PCT:.0%} daily halt")
    if gate["blocked"]:
        line += "\n  ENTRIES BLOCKED — " + gate["reason"]
    return line


def contract_mid(broker, underlying: str, symbol: str) -> float | None:
    """Mid for one held contract. The chain call returns one page of at
    most 1,000 contracts, so a far-dated contract on a deep chain can be
    absent from it; ask for it by name before giving up. Errors from the
    chain call propagate (the caller reports them); the by-name lookup is
    a fallback and fails quietly to None."""
    mid = mid_price((broker.quotes(underlying) or {}).get(symbol, {}))
    if mid is None and hasattr(broker, "contract_quote"):
        try:
            mid = mid_price((broker.contract_quote(symbol) or {})
                            .get(symbol, {}))
        except Exception:
            mid = None
    return mid


# ── broker positions the doctrine does not manage ────────────────────
def held_qty(position: dict, fallback: int) -> int:
    """Contracts/shares the broker actually holds. Exits sell this, not
    the book's number, so a duplicate fill can never be left behind."""
    try:
        return int(float(position["qty"]))
    except (KeyError, TypeError, ValueError):
        return fallback


def orphan_close_active(today: str) -> bool:
    return today <= ORPHAN_CLOSE_UNTIL


def close_orphans(broker, positions: dict, ledger: dict, today: str) -> tuple:
    """Close the operator-listed ORPHAN_CLOSE positions. Options sell
    limit-at-mid, day only (§38), exactly like a doctrine exit; stock
    closes the way MANUAL_CLOSE_TICKERS does. A symbol already sent this
    session — or with a sell already working at the broker — is skipped,
    so a duplicate evening run cannot double-sell. Anything that fails
    is retried next run and never stops the run."""
    sent, notes = [], []
    closing = ledger.setdefault("orphan_closing", {})
    if not orphan_close_active(today):
        return sent, notes
    managed = set(ledger["open"]) | set(ledger.get("options", {}))
    selling = {o.get("symbol") for o in _open_orders(broker)
               if o.get("side") == "sell"}
    for sym, why in ORPHAN_CLOSE.items():
        if sym not in positions:
            closing.pop(sym, None)
            continue
        if sym in managed or closing.get(sym) == today:
            continue
        qty = held_qty(positions[sym], 0)
        if qty < 1:
            continue
        try:
            if is_option_symbol(sym):
                if sym in selling:
                    closing[sym] = today      # already working; say so
                    continue
                mid = contract_mid(broker, parse_occ_symbol(sym)["ticker"],
                                   sym)
                if mid is None:
                    notes.append(f"{sym}: no tradable quote — close "
                                 "retried next run")
                    continue
                broker.sell_to_close(sym, qty, mid)
                how = f"limit {mid:.2f}"
            else:
                broker.cancel_symbol_orders(sym)
                broker.close_position(sym)
                how = "market, at the next open"
        except Exception as e:
            notes.append(f"{sym}: close failed ({_error_text(e)}) — retried "
                         "next run")
            continue
        closing[sym] = today
        sent.append((sym, qty, how, why))
    return sent, notes


def format_orphans(positions: dict, ledger: dict, today: str,
                   notes: list) -> list:
    """The orphan section, built from what is still HELD and when its
    close went out — not from what this run happened to send — so both
    evening runs print the same text and the digest does not ping twice."""
    if not orphan_close_active(today):
        return []
    held = [s for s in ORPHAN_CLOSE if s in positions
            and s not in ledger["open"] and s not in ledger.get("options", {})]
    if not held:
        return []
    closing = ledger.get("orphan_closing", {})
    lines = [f"ORPHANED POSITIONS ({len(held)} held) — closing, operator "
             "decision 2026-11-18. Left behind by the option cycle before "
             "its exit fix; not booked as trades:"]
    for sym in held:
        state = (f"close sent {closing[sym]}" if sym in closing
                 else "close NOT sent yet")
        lines.append(f"  {sym}  qty {positions[sym].get('qty')}  {state}  "
                     f"({ORPHAN_CLOSE[sym]})")
    lines += [f"  note: {n}" for n in notes]
    return lines


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


def _order_state(broker, order_id) -> dict | None:
    """The broker's view of one order, or None when it cannot be read
    (no id, a fake without order lookup, or an API error)."""
    if not order_id or not hasattr(broker, "order"):
        return None
    try:
        return broker.order(order_id) or None
    except Exception:
        return None


def _status(order: dict | None) -> str:
    return str((order or {}).get("status", "")).lower()


def _underlying(symbol) -> str | None:
    parsed = parse_occ_symbol(str(symbol or ""))
    return parsed["ticker"] if parsed else None


def _open_orders(broker) -> list:
    """Orders still working at the broker, or [] when unreadable."""
    if not hasattr(broker, "orders"):
        return []
    try:
        return [o for o in (broker.orders(status="open", limit=500) or [])
                if not o.get("status") or _status(o) in WORKING_ORDER_STATES]
    except Exception:
        return []


def _error_text(e: Exception) -> str:
    """Alpaca puts the reason in the HTTP error BODY; urllib's message
    drops it ("HTTP Error 403: Forbidden")."""
    try:
        body = e.read().decode()[:200]          # urllib HTTPError
        return f"{e}: {body}" if body else str(e)
    except Exception:
        return str(e)


UNFILLED_EXIT = ("gone without the exit sell filling — expired, exercised "
                 "or closed by hand")


def _closure(broker, symbol: str, rec: dict) -> tuple:
    """The `closed` row for a book contract the broker no longer holds.

    A doctrine exit is booked only when a sell actually filled; P&L adds
    up every sell sent for the contract (re-sends, partial fills and
    surplus sales), and the quantity shown is what those sells filled.
    A contract that vanished while its exit sell sat unfilled expired,
    was exercised, or was closed by hand, and is labelled so."""
    sell = rec.get("sell_pending") or {}
    filled, cash, readable = 0.0, 0.0, False
    ids = list(rec.get("sell_order_ids") or [])
    if sell.get("order_id") and sell["order_id"] not in ids:
        ids.append(sell["order_id"])
    for oid in ids:
        o = _order_state(broker, oid)
        if o is None:
            continue
        readable = True
        q = float(o.get("filled_qty") or 0)
        if q and o.get("filled_avg_price") is not None:
            filled += q
            cash += q * float(o["filled_avg_price"])
    if sell.get("kind") != "exit":
        return (symbol, rec, None, "reconciled")
    if filled:
        pl = round((cash - filled * rec["entry_price"]) * 100.0, 2)
        return (symbol, rec, {"realized_pl": pl, "qty": int(filled)},
                tuple(sell["reasons"]))
    return (symbol, rec, None, UNFILLED_EXIT if readable else "reconciled")


def run_option_cycle(broker, signals: list, all_bars: dict, today: str,
                     ledger: dict, fundamentals: dict | None = None,
                     blocked_reason: str | None = None) -> tuple:
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

    `blocked_reason` (the account FREEZE/HALT) suppresses new entries
    only. Exits always run.

    A contract stays in the book until the broker no longer holds it.
    Sending a sell is not closing a position: a day-only limit that does
    not fill expires at the close, and until 2026-11-18 the book forgot
    the contract the moment the sell went out, leaving it in the account
    with no rule watching it. `closed` now holds confirmed closes only;
    a sell that was merely sent is reported in `notes` and retried each
    session until the position is gone.
    """
    as_of = date.fromisoformat(today)
    book = ledger.setdefault("options", {})
    held = broker.option_positions()
    closed, opened, notes = [], [], []

    # The broker's working orders are the truth a stale ledger checkout
    # cannot be: a backup run queued behind the first run starts from
    # the commit before the first run's ledger landed.
    open_orders = _open_orders(broker)
    selling = {o.get("symbol") for o in open_orders if o.get("side") == "sell"}
    buying = {_underlying(o.get("symbol")) for o in open_orders
              if o.get("side") == "buy"}

    # ── exits first ──────────────────────────────────────────────────
    for symbol in list(book):
        rec = book[symbol]
        sell = rec.get("sell_pending")
        if symbol not in held:
            # A buy not yet filled is not a vanished position. Tonight's
            # buy counts even without the flag: records written by the
            # code before 2026-11-18 never carried it.
            if rec.get("entry_pending") or rec.get("entry_date") == today:
                if rec.get("entry_date") == today:
                    rec["entry_pending"] = True
                    continue          # bought tonight; fills at the open
                o = _order_state(broker, rec.get("entry_order_id"))
                if o is not None and _status(o) in WORKING_ORDER_STATES:
                    continue          # still working (a daytime run)
                if o is None or not float(o.get("filled_qty") or 0):
                    del book[symbol]
                    notes.append(f"{symbol}: entry order "
                                 + ("never filled" if o is not None
                                    else "not held and unreadable")
                                 + " — dropped, not a trade")
                    continue
            closed.append(_closure(broker, symbol, rec))
            del book[symbol]
            continue
        rec.pop("entry_pending", None)                  # it filled
        if symbol in selling or (sell and sell.get("date") == today):
            continue                  # a sell for it is already working
        qty_held = held_qty(held[symbol], rec["qty"])
        if qty_held < rec["qty"]:
            notes.append(f"{symbol}: broker holds {qty_held}, book said "
                         f"{rec['qty']} — book corrected")
            rec["qty"] = qty_held
        # An exit the doctrine has decided STICKS until the broker no
        # longer holds the contract. A stop that fired yesterday is not
        # undone by today's bounce, and a missing bar is no reason to
        # stop selling.
        exit_due = bool(sell and sell.get("kind") == "exit")
        reasons = list(sell["reasons"]) if exit_due else []
        bars = all_bars.get(rec["ticker"])
        if bars is None or bars.empty:
            if not exit_due:
                notes.append(f"{symbol}: no underlying bars — NOT evaluated")
                continue
        else:
            position = OpenPosition(
                ticker=rec["ticker"], contract=symbol, quantity=rec["qty"],
                entry_price=rec["entry_price"],
                expiry=date.fromisoformat(rec["expiry"]),
                invalidation_price=rec["invalidation_price"],
                entry_date=date.fromisoformat(rec["entry_date"]),
                entry_underlying=rec["entry_underlying"])
            verdict = evaluate_exit(position, float(bars["close"].iloc[-1]),
                                    as_of)
            if verdict.must_exit:
                exit_due = True
                reasons += [r for r in verdict.reasons if r not in reasons]
        # More held than the book sized for is a duplicate fill (the
        # second-run double buy). Sell the surplus; the trade the
        # doctrine sized stays under its rules.
        excess = qty_held - rec["qty"]
        if exit_due or excess > 0:
            what = ("EXIT due (" + ", ".join(reasons) + ")" if exit_due
                    else f"{excess} contract(s) over the sized {rec['qty']}")
            # Exit sells the same way entries buy — limit at the mid, day
            # only (§38) — so a fresh quote is required here too. A stale
            # or missing quote means the sell is deferred to the next
            # run rather than falling back to a market order, the exact
            # thing this rule exists to prevent.
            try:
                mid = contract_mid(broker, rec["ticker"], symbol)
            except Exception as e:
                notes.append(f"{symbol}: {what} but quote fetch failed "
                             f"({e}) — retrying next run")
                continue
            if mid is None:
                notes.append(f"{symbol}: {what} but no tradable quote — "
                             "retrying next run")
                continue
            qty = qty_held if exit_due else excess
            # One rejected order must not cost every exit after it: until
            # 2026-11-18 an unguarded rejection here aborted the cycle.
            try:
                order = broker.sell_to_close(symbol, qty, mid) or {}
            except Exception as e:
                notes.append(f"{symbol}: {what} but the sell was rejected "
                             f"({_error_text(e)}) — retrying next run")
                continue
            if order.get("id"):
                rec.setdefault("sell_order_ids", []).append(order["id"])
            rec["sell_pending"] = dict(
                kind="exit" if exit_due else "excess", date=today, qty=qty,
                limit=round(mid, 4), order_id=order.get("id"),
                reasons=reasons)
            notes.append(f"{symbol}: SELL SENT {qty}x limit {mid:.2f} — "
                         f"{what}. Booked when the broker confirms the "
                         "position is gone; re-sent each session until "
                         "then.")
        elif sell and sell.get("kind") == "excess":
            rec.pop("sell_pending")       # surplus sold; nothing pending

    # ── entries ──────────────────────────────────────────────────────
    if blocked_reason:
        if signals:
            notes.append(f"no option entries — {blocked_reason}")
        return opened, closed, notes
    equity = float(broker.account()["equity"])
    # Slots: everything held, plus buys still waiting for the open, less
    # contracts with an exit sent THIS session. A stale exit marker whose
    # re-send failed frees nothing; neither does a surplus sale.
    waiting = [s for s, r in book.items()
               if r.get("entry_pending") and s not in held]
    exiting = [s for s, r in book.items() if s in held
               and (r.get("sell_pending") or {}).get("kind") == "exit"
               and r["sell_pending"].get("date") == today]
    open_count = len(held) + len(waiting) - len(exiting)
    # Underlyings with contracts the broker holds outside the book
    # (orphans, hand trades). Buying there could pick the very contract
    # being sold, and a holding would then be mistaken for the fill.
    foreign = {_underlying(s) for s in held if s not in book}
    for sig in signals:
        if open_count >= MAX_OPEN:
            break
        if any(r["ticker"] == sig["ticker"] for r in book.values()):
            continue                                # one contract per name
        if sig["ticker"] in buying:
            notes.append(f"{sig['ticker']}: a buy is already working at "
                         "the broker — not buying again")
            continue
        if sig["ticker"] in foreign:
            notes.append(f"{sig['ticker']}: the account holds a contract "
                         "on it outside the book — no new entry until it "
                         "is gone")
            continue
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
        try:
            order = broker.buy_to_open(pick["symbol"], qty, pick["mid"]) or {}
        except Exception as e:
            notes.append(f"{sig['ticker']}: buy rejected "
                         f"({_error_text(e)}) — no entry")
            continue
        net_income = (trailing_net_income(fundamentals, sig["ticker"], today)
                     if fundamentals else None)
        book[pick["symbol"]] = dict(
            ticker=sig["ticker"], qty=qty, entry_price=pick["mid"],
            expiry=pick["expiration_date"], strike=float(pick["strike_price"]),
            # Not held until the open fills it. Kept in the book meanwhile
            # so a second run this session neither drops it nor buys the
            # name again (both happened before 2026-11-18).
            entry_pending=True, entry_order_id=order.get("id"),
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
        if position and position.get("realized_pl") is not None:
            pnl = f"  P&L ${float(position['realized_pl']):+,.2f}"
        elif position:
            pnl = f"  P&L ${float(position.get('unrealized_pl', 0)):+,.2f}"
        why = (", ".join(reasons) if isinstance(reasons, tuple) else reasons)
        qty = (position or {}).get("qty", rec["qty"])
        if isinstance(reasons, tuple):
            lines.append(f"  CLOSED {qty}x {symbol}{pnl}  ({why}) — sold; "
                         "the broker no longer holds it")
        else:
            lines.append(f"  GONE   {rec['qty']}x {symbol}  ({why})")
    if not opened and not closed:
        lines.append("  no option trades today")

    if book:
        lines.append(f"  holding {len(book)}:")
        for symbol, rec in sorted(book.items()):
            state = ""
            if rec.get("entry_pending"):
                state = "  [buy queued for the open]"
            elif rec.get("sell_pending"):
                s = rec["sell_pending"]
                state = (f"  [{s['kind']} sell sent {s['date']}, "
                         f"{s['qty']}x limit {s['limit']:.2f} — not yet "
                         "filled]")
            lines.append(f"    {symbol}  {rec['qty']}x @ "
                         f"${rec['entry_price']:.2f}  since {rec['entry_date']}"
                         f"  stop-if-underlying <= "
                         f"{rec['invalidation_price']:.2f}{state}")
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
    # Spec §4 account limits. Gates NEW entries only (step 4 and the
    # options cycle); everything that reduces risk still runs.
    gate = resolve_gate(ledger, load_equity_history(), equity, today)

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

    # 3d. positions the option cycle orphaned (ORPHAN_CLOSE, operator
    # decision 2026-11-18). Never booked as trades.
    orphan_sent, orphan_notes = close_orphans(broker, positions, ledger,
                                              today)

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
    # MAX_OPEN is the STOCK doctrine's cap and must count stocks only.
    # Alpaca's /v2/positions returns equity and option contracts in one
    # list, so the raw dict double-counts the options overlay, which
    # already enforces MAX_OPEN against its own book inside
    # run_option_cycle. Left uncorrected the two tracks share one cap:
    # on 2026-09-08 five held contracts plus seven stocks tripped the
    # cap at 12 and all three H-25 signals were skipped while a stock
    # slot was actually free.
    equity_open = equity_positions(positions)
    for sig in signals:
        sym = sig["ticker"]
        if sym in positions or sym in ledger["open"]:
            skipped.append((sym, "already held"))
            continue
        if gate["blocked"]:
            skipped.append((sym, gate["reason"]))
            continue
        if len(equity_open) + len(placed) >= MAX_OPEN:
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
                                   fundamentals=fundamentals,
                                   blocked_reason=gate["reason"])
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
                        manual_closes=manual_closes, risk_gate=gate,
                        orphan_closes=(orphan_sent, orphan_notes))


def build_report(today, acct, positions, signals, placed, skipped,
                 closed_today, time_exits, ledger,
                 option_review: str = "", option_cycle=None,
                 gap_cancelled=None, cost_rows=None,
                 equity: float | None = None,
                 micro_warnings=None, growth=None,
                 manual_closes=None, risk_gate=None,
                 orphan_closes=None) -> str:
    lines = [f"PAPER SHADOW TRACK — {'/'.join(ACTIVE_SETUPS)} doctrine, "
             f"as of {today}",
             f"paper equity: ${float(acct['equity']):,.2f}   "
             f"cash: ${float(acct['cash']):,.2f}"]
    if risk_gate:
        lines.append(format_account_gate(risk_gate))
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
    if orphan_closes is not None:
        lines += format_orphans(positions, ledger, today, orphan_closes[1])
    lines.append("")

    if closed_today:
        lines.append("CLOSED SINCE LAST RUN:")
        for t in closed_today:
            r_txt = f"{t['r']:+.2f}R" if t["r"] is not None else "r n/a"
            lines.append(f"  {t['ticker']}  {t['entry_date']} -> "
                         f"{t['exit_date']}  {r_txt}  ({t['reason']})")
        lines.append("")

    # The count that matters for entries is the STOCK count — option
    # contracts appear in the same broker book but are capped by the
    # options cycle against its own list.
    stock_open = equity_positions(positions)
    lines.append(f"OPEN POSITIONS ({len(positions)}) — "
                 f"{len(stock_open)} of {MAX_OPEN} stock slots used, "
                 f"{len(positions) - len(stock_open)} option contracts:")
    unmanaged = []
    for sym, p in sorted(positions.items()):
        head = (f"  {sym}  qty {p['qty']}  "
                f"unrealized ${float(p.get('unrealized_pl', 0)):+,.2f}  ")
        rec = ledger["open"].get(sym)
        opt = ledger.get("options", {}).get(sym)
        if rec:
            lines.append(head + f"stop {rec.get('stop', '?')}  "
                         f"target {rec.get('target', '?')}  "
                         f"since {rec.get('entry_date', '?')}")
        elif opt:
            lines.append(head + "option, stop-if-underlying <= "
                         f"{opt['invalidation_price']:.2f}  "
                         f"since {opt['entry_date']}")
        elif sym in ORPHAN_CLOSE and orphan_close_active(today):
            sent_on = ledger.get("orphan_closing", {}).get(sym)
            lines.append(head + "ORPHAN — "
                         + (f"close sent {sent_on}" if sent_on
                            else "close NOT sent yet")
                         + " (operator decision 2026-11-18)")
        else:
            # A position no rule watches is a position nobody is
            # watching. Say so instead of printing "stop ?".
            unmanaged.append(sym)
            lines.append(head + "UNMANAGED — not in the ledger; no stop, "
                         "target or exit rule applies")
    if not positions:
        lines.append("  none")
    if unmanaged:
        lines.append(f"  WARNING: {len(unmanaged)} unmanaged position(s): "
                     + ", ".join(unmanaged)
                     + ". Nothing in this system will exit them.")
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


def session_date_from_argv(argv: list) -> str:
    """The SESSION being reported, which is not always the runner's date.

    GitHub delivers scheduled fires late — observed by hours — so an
    after-close run can land past midnight UTC. Such a run is still
    reporting the previous session, and dating it by the runner's calendar
    day made `data_is_fresh` compare the wrong day: on 2026-09-25 every
    fire either arrived before the close or after midnight, so that session
    was never scanned, ordered, or exited at all.

    Explicit `--session-date=YYYY-MM-DD` wins; otherwise the runner's date,
    so every existing caller keeps its current behaviour.
    """
    for arg in argv:
        if arg.startswith("--session-date="):
            value = arg.split("=", 1)[1]
            date.fromisoformat(value)      # reject a malformed date loudly
            return value
    return str(date.today())


def main() -> None:
    import sys
    from .options_broker import PaperOptionsBroker
    preopen = "--preopen" in sys.argv
    broker = PaperOptionsBroker()
    today = session_date_from_argv(sys.argv)
    start = str(date.fromisoformat(today) - timedelta(days=HISTORY_DAYS))
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
    print(f"\nReport saved: {save_report(name, text, stamp=today)}")


if __name__ == "__main__":
    main()
