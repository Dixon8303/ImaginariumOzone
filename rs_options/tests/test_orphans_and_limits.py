"""The option cycle stranded seven positions; the account limits were
never enforced. These pin both fixes (2026-11-18).

1. Stranded positions. The cycle erased a contract from its book the
   moment it SENT a sell. A day-only limit that did not fill expired at
   the close and left the contract in the account with no rule watching
   it. Separately, a second evening run (the 22:10 UTC backup) found the
   evening's buy not yet filled, dropped it as "reconciled", and bought
   the name again — two fills, one book entry, double the sized risk.
   By the 2026-11-17 report seven positions were unmanaged, carrying
   $3,921 of a $4,405 open loss.

2. Account limits. The spec's 10% drawdown FREEZE and 3% daily-loss HALT
   existed in the risk engine and the playbook but not in this trader,
   which sat 8.1% below its peak with nothing to stop new entries.
"""
import json

import pandas as pd
import pytest

from paper import daily
from paper.daily import (DAILY_LOSS_HALT_PCT, DRAWDOWN_FREEZE_PCT,
                         ORPHAN_CLOSE, account_gate, close_orphans,
                         load_ledger, load_rearm_date, run, save_ledger)

SESSION = "2026-11-18"
NEXT = "2026-11-19"
SYMBOL = "KO270115C00100000"


def book_entry(qty=2, **extra):
    rec = dict(ticker="KO", qty=qty, entry_price=3.175, expiry="2027-01-15",
               strike=100.0, entry_date="2026-11-16",
               invalidation_price=95.67, entry_underlying=99.605,
               basis="delta", delta=0.54, spread_pct=0.05)
    rec.update(extra)
    return rec


def ko_bars(close):
    return {"KO": pd.DataFrame({"trade_date": [SESSION], "close": [close]})}


class OptBroker:
    """Fake broker for the option cycle: positions with real `qty`, and
    order lookups that answer from a table."""

    def __init__(self, positions=None, orders=None, bid=3.0, ask=3.2,
                 equity=100_000.0):
        self._positions = positions or {}
        self._orders = orders or {}
        self._bid, self._ask, self._equity = bid, ask, equity
        self.bought, self.sold = [], []

    def account(self):
        return {"equity": str(self._equity), "cash": str(self._equity)}

    def option_positions(self):
        return self._positions

    def quotes(self, underlying):
        syms = list(self._positions) + [SYMBOL, "KO270115C00102500"]
        return {s: {"bid": self._bid, "ask": self._ask, "delta": 0.55}
                for s in syms}

    def contracts(self, underlying, as_of, limit=200):
        return [{"symbol": "KO270115C00102500", "type": "call",
                 "strike_price": "102.5", "expiration_date": "2027-01-15",
                 "open_interest": "900"}]

    def order(self, order_id):
        if order_id not in self._orders:
            raise RuntimeError("unknown order")
        return self._orders[order_id]

    def buy_to_open(self, symbol, qty, limit_price):
        self.bought.append((symbol, qty, limit_price))
        return {"id": f"buy-{len(self.bought)}"}

    def sell_to_close(self, symbol, qty, limit_price):
        self.sold.append((symbol, qty, limit_price))
        return {"id": f"sell-{len(self.sold)}"}


def held(qty):
    return {SYMBOL: {"qty": str(qty), "unrealized_pl": "-62.00"}}


# ── 1a. a sent sell is not a close ────────────────────────────────────
def test_unfilled_exit_is_resent_next_session_not_forgotten():
    ledger = {"open": {}, "closed": [], "options": {SYMBOL: book_entry()}}
    below = ko_bars(95.0)                     # under invalidation 95.67
    b1 = OptBroker(positions=held(2))
    _, closed, _ = daily.run_option_cycle(b1, [], below, SESSION, ledger)
    assert b1.sold == [(SYMBOL, 2, pytest.approx(3.1))]
    assert closed == [] and SYMBOL in ledger["options"]

    # The limit never filled; the broker still holds both contracts.
    b2 = OptBroker(positions=held(2), bid=2.6, ask=2.8)
    _, closed, notes = daily.run_option_cycle(b2, [], below, NEXT, ledger)
    assert b2.sold == [(SYMBOL, 2, pytest.approx(2.7))], \
        "re-sent at the new session's mid"
    assert closed == []
    assert ledger["options"][SYMBOL]["sell_pending"]["date"] == NEXT


def test_second_run_same_session_does_not_sell_twice():
    ledger = {"open": {}, "closed": [], "options": {SYMBOL: book_entry()}}
    below = ko_bars(95.0)
    broker = OptBroker(positions=held(2))
    daily.run_option_cycle(broker, [], below, SESSION, ledger)
    daily.run_option_cycle(broker, [], below, SESSION, ledger)  # 22:10 backup
    assert len(broker.sold) == 1


def test_confirmed_exit_books_the_sell_fill():
    ledger = {"open": {}, "closed": [], "options": {SYMBOL: book_entry(
        sell_pending=dict(kind="exit", date=SESSION, qty=2, limit=3.1,
                          order_id="s1", reasons=["INVALIDATION"]))}}
    broker = OptBroker(orders={"s1": {"filled_avg_price": "3.00",
                                      "filled_qty": "2"}})
    _, closed, _ = daily.run_option_cycle(broker, [], ko_bars(95.0), NEXT,
                                          ledger)
    sym, rec, pos, reasons = closed[0]
    assert sym == SYMBOL and reasons == ("INVALIDATION",)
    assert pos["realized_pl"] == pytest.approx((3.00 - 3.175) * 2 * 100)
    assert SYMBOL not in ledger["options"]
    text = daily.format_option_cycle(([], closed, []), ledger)
    assert "CLOSED 2x" in text and "confirmed" in text


def test_exit_sells_what_the_broker_holds_not_what_the_book_says():
    """KO270115C00100000: book 2, broker 4 (the double buy). An exit that
    sold the book's 2 would strand the other 2 exactly as before."""
    ledger = {"open": {}, "closed": [], "options": {SYMBOL: book_entry(2)}}
    broker = OptBroker(positions=held(4))
    daily.run_option_cycle(broker, [], ko_bars(95.0), SESSION, ledger)
    assert broker.sold[0][1] == 4


def test_surplus_from_a_double_buy_is_sold_and_the_trade_kept():
    ledger = {"open": {}, "closed": [], "options": {SYMBOL: book_entry(2)}}
    broker = OptBroker(positions=held(4))
    _, closed, notes = daily.run_option_cycle(broker, [], ko_bars(99.0),
                                              SESSION, ledger)
    assert broker.sold == [(SYMBOL, 2, pytest.approx(3.1))]
    assert closed == []
    rec = ledger["options"][SYMBOL]
    assert rec["qty"] == 2 and rec["sell_pending"]["kind"] == "excess"
    # Once the surplus fills, the pending marker clears and nothing sells.
    later = OptBroker(positions=held(2))
    daily.run_option_cycle(later, [], ko_bars(99.0), NEXT, ledger)
    assert later.sold == [] and "sell_pending" not in ledger["options"][SYMBOL]


def test_book_corrects_down_to_a_partial_fill():
    ledger = {"open": {}, "closed": [], "options": {SYMBOL: book_entry(4)}}
    broker = OptBroker(positions=held(3))
    _, _, notes = daily.run_option_cycle(broker, [], ko_bars(99.0),
                                         SESSION, ledger)
    assert ledger["options"][SYMBOL]["qty"] == 3
    assert any("book corrected" in n for n in notes)


# ── 1b. a pending buy is not a vanished position ─────────────────────
def signal():
    return dict(ticker="KO", close=99.6, stop=95.67, target=111.4,
                r_denom=3.93, score=8, rationale="test")


def test_backup_run_neither_drops_nor_rebuys_a_pending_entry():
    """The exact 2026-11-16 shape: buy at 21:35 UTC, backup at 22:10 UTC
    finds nothing held yet. It must keep the entry and must not buy the
    name a second time."""
    ledger = {"open": {}, "closed": []}
    broker = OptBroker()                          # nothing fills tonight
    daily.run_option_cycle(broker, [signal()], {}, SESSION, ledger)
    daily.run_option_cycle(broker, [signal()], {}, SESSION, ledger)
    assert len(broker.bought) == 1
    (sym, rec), = ledger["options"].items()
    assert rec["entry_pending"] and rec["entry_order_id"] == "buy-1"


def test_pending_entry_clears_when_it_fills():
    ledger = {"open": {}, "closed": [], "options": {SYMBOL: book_entry(
        entry_pending=True, entry_order_id="b1", entry_date=SESSION)}}
    broker = OptBroker(positions=held(2))
    daily.run_option_cycle(broker, [], ko_bars(99.0), NEXT, ledger)
    assert "entry_pending" not in ledger["options"][SYMBOL]


def test_entry_that_never_filled_is_dropped_and_not_booked():
    ledger = {"open": {}, "closed": [], "options": {SYMBOL: book_entry(
        entry_pending=True, entry_order_id="b1", entry_date=SESSION)}}
    broker = OptBroker(orders={"b1": {"status": "expired",
                                      "filled_qty": "0"}})
    _, closed, notes = daily.run_option_cycle(broker, [], {}, NEXT, ledger)
    assert ledger["options"] == {} and closed == []
    assert any("never filled" in n for n in notes)


def test_entry_slots_count_pending_buys():
    """Buys queued for the open hold a slot even though nothing is held
    yet; otherwise a second run could buy past MAX_OPEN."""
    book = {f"X{i}": book_entry(ticker=f"T{i}", entry_pending=True,
                                entry_order_id=f"b{i}", entry_date=SESSION)
            for i in range(daily.MAX_OPEN)}
    ledger = {"open": {}, "closed": [], "options": book}
    broker = OptBroker()
    daily.run_option_cycle(broker, [signal()], {}, SESSION, ledger)
    assert broker.bought == []


def test_legacy_entry_without_flags_still_reconciles():
    ledger = {"open": {}, "closed": [], "options": {SYMBOL: book_entry()}}
    _, closed, _ = daily.run_option_cycle(OptBroker(), [], {}, SESSION,
                                          ledger)
    assert closed[0][3] == "reconciled" and ledger["options"] == {}


# ── 1c. the seven orphans ─────────────────────────────────────────────
STRANDED_2026_11_17 = {
    "CVX261120C00220000", "DAL261120C00080000", "KO270115C00097500",
    "PFE", "PFE261218C00031000", "XOM", "XOM261120C00185000"}


def test_orphan_list_is_exactly_the_seven_from_the_report():
    assert set(ORPHAN_CLOSE) == STRANDED_2026_11_17
    assert SYMBOL not in ORPHAN_CLOSE, \
        "KO 100C is a managed trade (its surplus is sold, not the trade)"


class CloseBroker(OptBroker):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.cancelled, self.closed_syms = [], []

    def cancel_symbol_orders(self, symbol):
        self.cancelled.append(symbol)

    def close_position(self, symbol):
        self.closed_syms.append(symbol)


def stranded_positions():
    return {s: {"qty": "500" if s == "PFE" else "100" if s == "XOM"
                else "2", "unrealized_pl": "-1"}
            for s in STRANDED_2026_11_17}


def test_orphans_close_options_at_mid_and_stock_like_manual_closes():
    ledger = {"open": {}, "closed": [], "options": {}}
    broker = CloseBroker()
    broker._positions = stranded_positions()
    sent, notes = close_orphans(broker, broker._positions, ledger, SESSION)
    assert notes == []
    assert sorted(broker.closed_syms) == ["PFE", "XOM"]
    sold = {s for s, _, _ in broker.sold}
    assert sold == STRANDED_2026_11_17 - {"PFE", "XOM"}
    assert all(lim == pytest.approx(3.1) for _, _, lim in broker.sold), \
        "limit at the mid, never market, on options"
    assert len(sent) == 7


def test_orphan_close_is_not_repeated_in_the_same_session():
    ledger = {"open": {}, "closed": [], "options": {}}
    broker = CloseBroker()
    broker._positions = stranded_positions()
    close_orphans(broker, broker._positions, ledger, SESSION)
    close_orphans(broker, broker._positions, ledger, SESSION)
    assert len(broker.sold) == 5 and len(broker.closed_syms) == 2
    # ...but an unfilled one is re-sent next session.
    close_orphans(broker, broker._positions, ledger, NEXT)
    assert len(broker.sold) == 10


def test_orphan_close_spares_a_symbol_the_ledger_manages():
    ledger = {"open": {"XOM": {"stop": 1.0}}, "closed": [], "options": {}}
    broker = CloseBroker()
    positions = {"XOM": {"qty": "100"}}
    sent, _ = close_orphans(broker, positions, ledger, SESSION)
    assert sent == [] and broker.closed_syms == []


def test_orphan_without_a_quote_waits_rather_than_selling_at_market():
    class NoQuote(CloseBroker):
        def quotes(self, underlying):
            return {}

    ledger = {"open": {}, "closed": [], "options": {}}
    broker = NoQuote()
    positions = {"CVX261120C00220000": {"qty": "1"}}
    sent, notes = close_orphans(broker, positions, ledger, SESSION)
    assert sent == [] and broker.sold == []
    assert any("no tradable quote" in n for n in notes)
    assert ledger["orphan_closing"] == {}


def test_closed_orphan_clears_its_marker():
    ledger = {"open": {}, "closed": [], "options": {},
              "orphan_closing": {"PFE": SESSION}}
    close_orphans(CloseBroker(), {}, ledger, NEXT)
    assert ledger["orphan_closing"] == {}


# ── 2. account limits ─────────────────────────────────────────────────
def hist(*pairs):
    return [{"date": d, "equity": e} for d, e in pairs]


HISTORY_2026_11_17 = hist(("2026-08-24", 100_000.00),
                          ("2026-10-30", 101_858.65),
                          ("2026-11-16", 95_051.77),
                          ("2026-11-17", 93_569.32))


def test_limits_come_from_the_risk_engine():
    assert DRAWDOWN_FREEZE_PCT == 0.10 and DAILY_LOSS_HALT_PCT == 0.03


def test_the_real_account_on_2026_11_17_is_not_yet_frozen():
    gate = account_gate(HISTORY_2026_11_17, 93_569.32, "2026-11-17")
    assert gate["blocked"] is False
    assert gate["drawdown"] == pytest.approx(0.0814, abs=1e-4)
    assert gate["peak"] == 101_858.65 and gate["peak_date"] == "2026-10-30"
    assert gate["daily_loss"] == pytest.approx(0.0156, abs=1e-4)


def test_ten_percent_below_peak_freezes():
    equity = 101_858.65 * 0.90
    gate = account_gate(HISTORY_2026_11_17, equity, SESSION)
    assert gate["frozen"] and gate["blocked"]
    assert "FREEZE" in gate["reason"] and "re-arm" in gate["reason"]


def test_rearm_restarts_the_peak():
    equity = 101_858.65 * 0.90
    gate = account_gate(HISTORY_2026_11_17, equity, SESSION,
                        rearmed_on="2026-11-17")
    assert not gate["frozen"]


def test_three_percent_session_loss_halts_and_uses_the_prior_session():
    history = hist(("2026-11-17", 100_000.0), (SESSION, 97_000.0))
    # today's own snapshot (written by the first run) is not the baseline
    gate = account_gate(history, 97_000.0, SESSION)
    assert gate["halted"] and "HALT" in gate["reason"]
    assert gate["prev"] == 100_000.0
    assert not account_gate(history, 97_100.0, SESSION)["halted"]


def test_malformed_rearm_file_is_an_error_not_a_silent_unfreeze(tmp_path):
    p = tmp_path / "risk_rearm.json"
    p.write_text(json.dumps({"rearmed_on": "last tuesday"}))
    with pytest.raises(ValueError):
        load_rearm_date(str(p))
    p.write_text(json.dumps({"rearmed_on": None}))
    assert load_rearm_date(str(p)) is None
    assert load_rearm_date(str(tmp_path / "absent.json")) is None


def test_shipped_rearm_file_is_unset():
    import pathlib
    shipped = pathlib.Path(daily.__file__).parent / "risk_rearm.json"
    assert load_rearm_date(str(shipped)) is None


# ── 2b. the gate inside a real run ────────────────────────────────────
@pytest.fixture
def files_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(daily, "LEDGER_PATH",
                        str(tmp_path / "paper_ledger.json"))
    monkeypatch.setattr(daily, "REARM_PATH", str(tmp_path / "rearm.json"))
    from paper import growth_tracker
    log = tmp_path / "paper_growth.jsonl"
    monkeypatch.setattr(growth_tracker, "GROWTH_LOG_PATH", str(log))
    return log


def test_frozen_run_places_no_entries_but_still_exits(files_in_tmp):
    from tests.test_paper_daily import FakeBroker, TODAY, breakout_universe
    files_in_tmp.write_text(json.dumps({"date": "2026-08-13",
                                        "equity": 120_000.0}) + "\n")
    save_ledger({"open": {"OLD": dict(
        entry_date="2026-07-01", entry=50.0, entry_estimated=False,
        stop=45.0, target=65.0, qty=10, order_id="x", setup="RS-02")},
        "closed": []}, daily.LEDGER_PATH)
    broker = FakeBroker(positions={"OLD": {"qty": 10, "unrealized_pl": 0}},
                        equity=100_000.0)                 # 16.7% off peak
    report = run(broker, breakout_universe(), TODAY)
    assert broker.brackets == [], "no new entries while frozen"
    assert "OLD" in broker.closed_syms, "time exit still runs"
    assert "ENTRIES BLOCKED" in report and "skipped NVDA: FREEZE" in report


def test_unfrozen_run_still_trades(files_in_tmp):
    from tests.test_paper_daily import FakeBroker, TODAY, breakout_universe
    broker = FakeBroker()
    report = run(broker, breakout_universe(), TODAY)
    assert broker.brackets and "RISK LIMITS: drawdown 0.0%" in report
    assert "ENTRIES BLOCKED" not in report


def test_option_entries_respect_the_gate():
    ledger = {"open": {}, "closed": []}
    broker = OptBroker()
    _, _, notes = daily.run_option_cycle(broker, [signal()], {}, SESSION,
                                         ledger, blocked_reason="FREEZE: x")
    assert broker.bought == []
    assert any("no option entries" in n for n in notes)


# ── report: nothing prints "stop ?" any more ──────────────────────────
def test_report_names_unmanaged_and_orphaned_positions():
    ledger = {"open": {}, "closed": [],
              "options": {SYMBOL: book_entry()}}
    positions = {SYMBOL: {"qty": "2", "unrealized_pl": "-124"},
                 "PFE": {"qty": "500", "unrealized_pl": "-765"},
                 "ZZZ": {"qty": "3", "unrealized_pl": "0"}}
    report = daily.build_report(
        SESSION, {"equity": "93558.50", "cash": "36166.51"}, positions,
        [], [], [], [], [], ledger)
    assert "stop ?" not in report
    assert "stop-if-underlying <= 95.67" in report
    assert "PFE  qty 500" in report and "ORPHAN — being closed" in report
    assert "ZZZ" in report and "UNMANAGED" in report
    assert "1 unmanaged position(s): ZZZ" in report


def test_ledger_round_trips_the_new_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(daily, "LEDGER_PATH", str(tmp_path / "l.json"))
    ledger = {"open": {}, "closed": [], "orphan_closing": {"PFE": SESSION},
              "options": {SYMBOL: book_entry(sell_pending=dict(
                  kind="exit", date=SESSION, qty=2, limit=3.1,
                  order_id="s", reasons=["DTE_FLOOR"]))}}
    save_ledger(ledger)
    assert load_ledger() == ledger


# ── the digest carries the new lines to the operator's phone ──────────
def test_digest_surfaces_freeze_orphans_and_unmanaged(tmp_path, monkeypatch):
    from datetime import datetime, timezone

    import paper.notify as notify
    reports = tmp_path / "docs" / "reports"
    reports.mkdir(parents=True)
    (reports / "paper_trading.txt").write_text(
        "generated: 2026-11-18\n\nPAPER SHADOW TRACK — as of 2026-11-18\n"
        "RISK LIMITS: drawdown 10.2% of the 10% freeze (peak $101,858.65 "
        "on 2026-10-30)\n"
        "  ENTRIES BLOCKED — FREEZE: equity is 10.2% below its peak\n"
        "ORPHANED POSITIONS — CLOSE SENT (7), operator decision\n"
        "  WARNING: 1 unmanaged position(s): ZZZ. Nothing in this system\n")
    (reports / "paper_growth.jsonl").write_text(
        '{"date": "2026-11-17", "equity": 93569.32}\n'
        '{"date": "2026-11-18", "equity": 91400.00}\n')
    monkeypatch.chdir(tmp_path)
    text = notify.digest(datetime(2026, 11, 18, 22, 0, tzinfo=timezone.utc))
    assert "NEW ENTRIES STOPPED: FREEZE" in text
    assert "risk: drawdown 10.2% of the 10% freeze" in text
    assert "close sent for 7" in text
    assert "WARNING: 1 position(s) no rule manages" in text


# ── a far-dated contract missing from the 1,000-contract chain page ───
def test_orphan_quote_falls_back_to_the_contract_by_name():
    class DeepChain(CloseBroker):
        def quotes(self, underlying):
            return {}                      # first page ended before it

        def contract_quote(self, symbol):
            return {symbol: {"bid": 0.40, "ask": 0.50}}

    ledger = {"open": {}, "closed": [], "options": {}}
    broker = DeepChain()
    sent, notes = close_orphans(
        broker, {"KO270115C00097500": {"qty": "2"}}, ledger, SESSION)
    assert broker.sold == [("KO270115C00097500", 2, pytest.approx(0.45))]
    assert notes == []


def test_doctrine_exit_uses_the_same_fallback():
    class DeepChain(OptBroker):
        def quotes(self, underlying):
            return {}

        def contract_quote(self, symbol):
            return {symbol: {"bid": 2.0, "ask": 2.2}}

    ledger = {"open": {}, "closed": [], "options": {SYMBOL: book_entry()}}
    broker = DeepChain(positions=held(2))
    daily.run_option_cycle(broker, [], ko_bars(95.0), SESSION, ledger)
    assert broker.sold == [(SYMBOL, 2, pytest.approx(2.1))]


def test_contract_quote_asks_for_the_symbol(monkeypatch):
    import io

    from paper import options_broker
    monkeypatch.setenv("RS_PAPER_ARMED", "YES")
    monkeypatch.setenv("APCA_API_KEY_ID", "k")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "s")
    seen = {}

    def fake_urlopen(req, timeout=30):
        seen["url"] = req.full_url
        body = {"snapshots": {SYMBOL: {"latestQuote": {"bp": 1.0,
                                                       "ap": 1.2}}}}
        return io.BytesIO(json.dumps(body).encode())

    monkeypatch.setattr(options_broker.urllib.request, "urlopen",
                        fake_urlopen)
    got = options_broker.PaperOptionsBroker().contract_quote(SYMBOL)
    assert seen["url"].endswith(f"/v1beta1/options/snapshots?symbols={SYMBOL}")
    assert got[SYMBOL]["bid"] == 1.0 and got[SYMBOL]["ask"] == 1.2


def test_unreadable_rearm_file_blocks_entries_but_the_run_completes(
        files_in_tmp, tmp_path):
    from tests.test_paper_daily import FakeBroker, TODAY, breakout_universe
    pathlib_rearm = tmp_path / "rearm.json"
    pathlib_rearm.write_text('{"rearmed_on": "not a date"}')
    save_ledger({"open": {"OLD": dict(
        entry_date="2026-07-01", entry=50.0, entry_estimated=False,
        stop=45.0, target=65.0, qty=10, order_id="x", setup="RS-02")},
        "closed": []}, daily.LEDGER_PATH)
    broker = FakeBroker(positions={"OLD": {"qty": 10, "unrealized_pl": 0}})
    report = run(broker, breakout_universe(), TODAY)
    assert broker.brackets == []
    assert "OLD" in broker.closed_syms, "exits still run"
    assert "risk limits unreadable" in report
