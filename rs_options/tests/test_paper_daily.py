"""Autonomous paper shadow track — broker guardrails + daily cycle."""
import json

import pandas as pd
import pytest

from paper import daily
from paper.alpaca_paper import PAPER_URL, PaperBroker
from paper.daily import (bdays_between, build_report, load_ledger,
                         position_size, run, save_ledger, scan)


# ── guardrails ───────────────────────────────────────────────────────
def test_paper_url_is_hardcoded_paper():
    assert PAPER_URL == "https://paper-api.alpaca.markets"


def test_broker_aborts_without_interlock(monkeypatch):
    monkeypatch.delenv("RS_PAPER_ARMED", raising=False)
    monkeypatch.setenv("APCA_API_KEY_ID", "k")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "s")
    with pytest.raises(SystemExit, match="RS_PAPER_ARMED"):
        PaperBroker()


def test_broker_aborts_without_keys(monkeypatch):
    monkeypatch.setenv("RS_PAPER_ARMED", "YES")
    monkeypatch.delenv("APCA_API_KEY_ID", raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)
    with pytest.raises(SystemExit, match="APCA"):
        PaperBroker()


# ── sizing ───────────────────────────────────────────────────────────
def test_position_size_risk_and_notional_caps():
    # $100k equity, $2 risk -> 1% = $1000 -> 500 shares, but 5% notional
    # at $100/share caps at 50 shares.
    assert position_size(100_000, 100.0, 98.0) == 50
    # wide stop: risk dominates
    assert position_size(100_000, 100.0, 80.0) == 50   # 1000/20=50 < cap
    assert position_size(100_000, 100.0, 100.0) == 0   # no risk denom
    assert position_size(1_000, 500.0, 490.0) == 0     # can't afford 1 share


def test_bdays_between():
    assert bdays_between("2026-08-03", "2026-08-14") == 9   # two weeks
    assert bdays_between("2026-08-14", "2026-08-14") == 0


# ── scan on synthetic bars ───────────────────────────────────────────
TODAY = "2026-08-14"          # a Friday; fixtures end on this session


def make_bars(closes, volume=1_000_000, last_volume=None, end=TODAY):
    n = len(closes)
    vols = [volume] * n
    if last_volume:
        vols[-1] = last_volume
    return pd.DataFrame({
        "trade_date": pd.bdate_range(end=end, periods=n).date.astype(str),
        "open": closes, "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes], "close": closes, "volume": vols})


def breakout_universe(end=TODAY):
    rising = [100.0 + 0.3 * i for i in range(299)] + [100.0 + 0.3 * 298 + 9.0]
    bars = {t: make_bars([500.0 + 0.05 * i for i in range(300)], end=end)
            for t in daily.required_tickers()}
    bars["NVDA"] = make_bars(rising, last_volume=2_000_000, end=end)
    return bars


def test_scan_finds_doctrine_signal():
    signals = scan(breakout_universe())
    tickers = [s["ticker"] for s in signals]
    assert "NVDA" in tickers
    s = next(x for x in signals if x["ticker"] == "NVDA")
    assert s["stop"] < s["close"] < s["target"]
    assert s["target"] == pytest.approx(s["close"] + 3 * s["r_denom"], abs=0.02)


# ── daily cycle with a fake broker ───────────────────────────────────
class FakeBroker:
    def __init__(self, positions=None, equity=100_000.0):
        self._positions = positions or {}
        self._equity = equity
        self.brackets, self.closed_syms, self.cancelled = [], [], []
        self.limits = []

    def account(self):
        return {"equity": str(self._equity), "cash": str(self._equity)}

    def positions(self):
        return self._positions

    def orders(self, status="open", symbols=None, limit=50):
        if status == "closed" and symbols == "GONE":
            return [{"side": "sell", "filled_avg_price": "118.00"}]
        return []

    def order(self, order_id):
        return {"id": order_id, "filled_avg_price": "101.00"}

    def submit_bracket(self, symbol, qty, stop_price, target_price,
                       limit_price=None):
        self.brackets.append((symbol, qty, stop_price, target_price))
        self.limits.append(limit_price)
        return {"id": f"ord-{symbol}"}

    def cancel_symbol_orders(self, symbol):
        self.cancelled.append(symbol)
        return 1

    def close_position(self, symbol):
        self.closed_syms.append(symbol)
        return {}


@pytest.fixture(autouse=True)
def ledger_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(daily, "LEDGER_PATH",
                        str(tmp_path / "paper_ledger.json"))


def test_run_places_bracket_and_records_ledger():
    broker = FakeBroker()
    report = run(broker, breakout_universe(), TODAY)
    assert broker.brackets and broker.brackets[0][0] == "NVDA"
    ledger = load_ledger(daily.LEDGER_PATH)
    assert "NVDA" in ledger["open"]
    assert ledger["open"]["NVDA"]["setup"] == "RS-02"
    assert "PAPER ORDERS PLACED (1)" in report
    assert "option guidance" in report and "CALL" in report


def test_run_reconciles_closed_position():
    save_ledger({"open": {"GONE": dict(
        entry_date="2026-08-01", entry=100.0, entry_estimated=False,
        stop=95.0, target=115.0, qty=10, order_id="x", setup="RS-02")},
        "closed": []}, daily.LEDGER_PATH)
    broker = FakeBroker()                       # GONE not in positions
    report = run(broker, {}, TODAY, require_fresh=False)
    ledger = load_ledger(daily.LEDGER_PATH)
    assert ledger["open"] == {}
    assert ledger["closed"][0]["ticker"] == "GONE"
    assert ledger["closed"][0]["r"] == pytest.approx(3.6)   # 118 exit / 5 risk
    assert "CLOSED SINCE LAST RUN" in report


def test_run_time_exits_stale_position():
    save_ledger({"open": {"OLD": dict(
        entry_date="2026-07-01", entry=100.0, entry_estimated=False,
        stop=95.0, target=115.0, qty=10, order_id="x", setup="RS-02")},
        "closed": []}, daily.LEDGER_PATH)
    broker = FakeBroker(positions={"OLD": {"qty": "10", "unrealized_pl": "5"}})
    run(broker, {}, TODAY, require_fresh=False)  # 32 business days later
    assert broker.cancelled == ["OLD"] and broker.closed_syms == ["OLD"]


def test_run_skips_already_held_and_caps():
    broker = FakeBroker(positions={"NVDA": {"qty": "5", "unrealized_pl": "0"}})
    save_ledger({"open": {"NVDA": dict(
        entry_date="2026-08-13", entry=100.0, entry_estimated=False,
        stop=95.0, target=115.0, qty=5, order_id="x", setup="RS-02")},
        "closed": []}, daily.LEDGER_PATH)
    report = run(broker, breakout_universe(), TODAY)
    assert broker.brackets == []                # not re-entered
    assert "already held" in report


# ── freshness guard ──────────────────────────────────────────────────
def test_stale_bars_block_the_whole_cycle():
    """A holiday run must not re-signal yesterday's bars."""
    broker = FakeBroker()
    report = run(broker, breakout_universe(), TODAY)
    assert "PAPER ORDERS PLACED" in report                    # sanity: fresh
    stale = run(broker, breakout_universe(), "2099-01-01")
    assert "No session today" in stale
    assert len(broker.brackets) == 1                          # nothing new


def test_data_is_fresh_detects_missing_benchmark():
    from paper.daily import data_is_fresh
    assert not data_is_fresh({}, TODAY)
    assert not data_is_fresh({"SPY": pd.DataFrame()}, TODAY)
    assert data_is_fresh(breakout_universe(), TODAY)


# ── dependency isolation (regression: CI ModuleNotFoundError) ────────
def test_paper_track_imports_without_duckdb(monkeypatch):
    """The paper trader fetches bars directly and never queries a
    DataStore, so its import chain must not require duckdb — the
    scheduled run has only pandas installed."""
    import builtins
    import importlib
    import sys

    real_import = builtins.__import__

    def no_duckdb(name, *args, **kwargs):
        if name == "duckdb":
            raise ModuleNotFoundError("No module named 'duckdb'")
        return real_import(name, *args, **kwargs)

    for mod in [m for m in sys.modules
                if m.startswith(("mve.", "paper.")) or m in ("mve", "paper")]:
        monkeypatch.delitem(sys.modules, mod, raising=False)
    monkeypatch.delitem(sys.modules, "duckdb", raising=False)
    monkeypatch.setattr(builtins, "__import__", no_duckdb)

    importlib.import_module("paper.daily")          # must not raise


# ── option-position review (co-pilot side) ───────────────────────────
import json as _json
from datetime import date as _d

from paper.daily import load_open_options, review_open_options

ROW = dict(ticker="NVDA", contract="NVDA 2026-09-18 220C", quantity=1,
           entry_price=5.0, expiry="2026-09-18", invalidation_price=100.0,
           entry_date="2026-08-10", entry_underlying=110.0)


def _options_file(tmp_path, rows):
    p = tmp_path / "open_options.json"
    p.write_text(_json.dumps({"positions": rows}))
    return str(p)


def test_load_open_options_parses_rows(tmp_path):
    pos = load_open_options(_options_file(tmp_path, [ROW]))
    assert len(pos) == 1
    assert pos[0].ticker == "NVDA" and pos[0].expiry == _d(2026, 9, 18)
    assert pos[0].target_price == 140.0            # 110 + 3 x 10


def test_load_open_options_missing_file_is_empty():
    assert load_open_options("/nonexistent/open_options.json") == []


def test_load_open_options_surfaces_bad_rows(tmp_path):
    """A silently dropped position is a position nobody is watching."""
    bad = dict(ROW, expiry="not-a-date")
    with pytest.raises(ValueError, match="Unreadable entries"):
        load_open_options(_options_file(tmp_path, [bad]))


def test_review_flags_exit_and_holds():
    bars = breakout_universe()
    nvda_close = float(bars["NVDA"]["close"].iloc[-1])
    from mve.position_manager import OpenPosition
    holding = OpenPosition("NVDA", "NVDA 2026-09-18 220C", 1, 5.0,
                           _d(2026, 9, 18), nvda_close - 50,
                           entry_date=_d(2026, 8, 10),
                           entry_underlying=nvda_close - 20)
    expiring = OpenPosition("NVDA", "NVDA 2026-08-17 220C", 1, 5.0,
                            _d(2026, 8, 17), 1.0)
    text = review_open_options([holding, expiring], bars, TODAY)
    assert "POSITION REVIEW — 2 open" in text
    assert "DTE_FLOOR" in text                     # the expiring one
    assert "NOT CHECKED" in text                   # expiring lacks entry data


def test_review_reports_unpriced_positions():
    from mve.position_manager import OpenPosition
    orphan = OpenPosition("ZZZZ", "ZZZZ 2026-09-18 10C", 1, 1.0,
                          _d(2026, 9, 18), 5.0)
    text = review_open_options([orphan], breakout_universe(), TODAY)
    assert "NOT PRICED" in text and "ZZZZ" in text


def test_review_empty_gives_instructions():
    assert "none on file" in review_open_options([], {}, TODAY)


def test_holiday_run_still_reviews_options(monkeypatch, tmp_path):
    """DTE ticks over a weekend — held options must still be reviewed."""
    monkeypatch.setattr(daily, "OPTIONS_PATH", _options_file(tmp_path, [ROW]))
    broker = FakeBroker()
    text = run(broker, breakout_universe(), "2099-01-01")
    assert "No session today" in text
    assert "last available" in text
    assert "POSITION REVIEW" in text               # review still ran
    assert broker.brackets == []                   # but no orders


def test_daily_report_includes_option_section():
    broker = FakeBroker()
    text = run(broker, breakout_universe(), TODAY)
    assert "OPTION POSITIONS" in text or "POSITION REVIEW" in text


# ── pre-open briefing (read-only by construction) ────────────────────
from paper.daily import bars_are_current, preopen_report

MONDAY = "2026-08-17"          # the session after the TODAY fixture (Friday)


def test_bars_are_current_accepts_yesterday_rejects_stale():
    bars = breakout_universe()                 # newest bar = Friday
    assert bars_are_current(bars, MONDAY)      # Friday -> Monday = 3 days
    assert bars_are_current(bars, TODAY)       # same day is fine too
    assert not bars_are_current(bars, "2026-09-01")   # weeks stale
    assert not bars_are_current({}, MONDAY)


def test_preopen_places_no_orders_and_writes_no_ledger():
    """The whole point: it cannot double-trade against the evening run."""
    broker = FakeBroker()
    before = load_ledger(daily.LEDGER_PATH)
    text = preopen_report(broker, breakout_universe(), MONDAY)
    assert broker.brackets == []               # nothing bought
    assert broker.closed_syms == []            # nothing sold
    assert load_ledger(daily.LEDGER_PATH) == before
    assert "no orders placed by this run" in text


def test_preopen_lists_candidates_with_option_guidance():
    text = preopen_report(FakeBroker(), breakout_universe(), MONDAY)
    assert "PRE-OPEN SCAN" in text
    assert "signals from the 2026-08-14 close" in text
    assert "CANDIDATES FOR TODAY (1)" in text
    assert "NVDA" in text and "option guidance" in text
    assert "ORDERS QUEUED FOR THE OPEN" in text


def test_preopen_marks_already_held_names():
    broker = FakeBroker(positions={"NVDA": {"qty": "5", "unrealized_pl": "12"}})
    text = preopen_report(broker, breakout_universe(), MONDAY)
    assert "[already held]" in text


def test_preopen_refuses_stale_bars():
    text = preopen_report(FakeBroker(), breakout_universe(), "2026-12-25")
    assert "stale or missing" in text
    assert "CANDIDATES" not in text


# ----------------------------------- H15a fill-gap cancellation (ADOPTED)

def test_entry_orders_carry_the_doctrine_cap():
    """Live orders must go in as limits at the H15a ceiling. A market
    order would fill at any gap, which is the behaviour the rule was
    adopted to stop."""
    from mve.setups import MAX_ENTRY_GAP
    broker = FakeBroker()
    daily.run(broker, breakout_universe(), TODAY)
    assert broker.limits and all(lp is not None for lp in broker.limits)
    for (sym, _q, _s, _t), lp in zip(broker.brackets, broker.limits):
        rec = daily.load_ledger()["open"][sym]
        assert lp == pytest.approx(rec["signal_close"] * (1 + MAX_ENTRY_GAP))
        assert rec["entry_cap"] == pytest.approx(lp)


def test_unfilled_entry_is_cancelled_not_booked_as_a_trade():
    """The cancellation actually happening. An unfilled order has no
    position, so without dedicated handling it would fall through to the
    closure branch and be recorded as a trade that exited at an unknown
    price — inventing a round trip that never occurred."""
    class Unfilled(FakeBroker):
        def order(self, order_id):
            return {"id": order_id, "status": "canceled"}

    broker = Unfilled()
    daily.save_ledger({"open": {"GAPD": dict(
        entry_date="2026-08-10", entry=100.0, entry_estimated=True,
        entry_cap=102.0, signal_close=100.0, stop=95.0, target=115.0,
        qty=10, order_id="ord-GAPD", setup="RS-02")}, "closed": []})
    report = daily.run(broker, breakout_universe(), TODAY)

    ledger = daily.load_ledger()
    assert "GAPD" not in ledger["open"]                 # order is gone
    assert not any(c["ticker"] == "GAPD" for c in ledger["closed"])
    assert "GAPD" in broker.cancelled                   # broker told too
    assert "H15a GAP CANCELLATIONS" in report           # never silent
    assert "cancelled GAPD" in report


def test_working_order_is_left_alone():
    """An order still live at the broker must not be cancelled just
    because it has not filled yet."""
    class Working(FakeBroker):
        def order(self, order_id):
            return {"id": order_id, "status": "new"}

    broker = Working()
    daily.save_ledger({"open": {"WORK": dict(
        entry_date="2026-08-10", entry=100.0, entry_estimated=True,
        entry_cap=102.0, signal_close=100.0, stop=95.0, target=115.0,
        qty=10, order_id="ord-WORK", setup="RS-02")}, "closed": []})
    daily.run(broker, breakout_universe(), TODAY)
    assert "WORK" in daily.load_ledger()["open"]
    assert "WORK" not in broker.cancelled


def test_tonights_order_is_not_cancelled_before_the_open():
    """An order queued by this same run has not seen an open yet."""
    class NoFill(FakeBroker):
        def order(self, order_id):
            return {"id": order_id, "status": "canceled"}

    broker = NoFill()
    daily.run(broker, breakout_universe(), TODAY)
    ledger = daily.load_ledger()
    assert ledger["open"], "tonight's entries must survive the same run"


# ----------------------------------- micro-account override integration

def cheap_breakout_universe(end=TODAY):
    """Same shape as breakout_universe but priced under $29, so a
    micro-account test can actually afford the signal it finds."""
    rising = [10.0 + 0.03 * i for i in range(299)] + [10.0 + 0.03 * 298 + 0.9]
    bars = {t: make_bars([50.0 + 0.005 * i for i in range(300)], end=end)
            for t in daily.required_tickers()}
    bars["NVDA"] = make_bars(rising, last_volume=2_000_000, end=end)
    return bars


def test_run_ignores_micro_override_when_not_armed(monkeypatch):
    """Default behaviour, tiny equity, override unset: doctrine sizing
    applies (0 shares) and no micro trade is placed."""
    monkeypatch.delenv("RS_MICRO_ACCOUNT_OVERRIDE", raising=False)
    broker = FakeBroker(equity=29.0)
    report = daily.run(broker, breakout_universe(), TODAY)
    assert broker.brackets == []
    assert "MICRO OVERRIDE" not in report


def test_run_places_one_share_when_micro_override_armed(monkeypatch):
    monkeypatch.setenv("RS_MICRO_ACCOUNT_OVERRIDE", "YES")
    broker = FakeBroker(equity=29.0)
    report = daily.run(broker, cheap_breakout_universe(), TODAY)
    assert broker.brackets and broker.brackets[0][1] == 1   # qty == 1
    ledger = daily.load_ledger()
    assert ledger["open"]["NVDA"]["micro_override"] is True
    assert "MICRO OVERRIDE ACTIVE" in report
    assert "MICRO OVERRIDE: NVDA" in report


def test_micro_override_caps_at_one_concurrent_position(monkeypatch):
    monkeypatch.setenv("RS_MICRO_ACCOUNT_OVERRIDE", "YES")
    daily.save_ledger({"open": {"OLD": dict(
        entry_date="2026-08-10", entry=10.0, entry_estimated=False,
        stop=9.0, target=13.0, qty=1, order_id="x", setup="RS-02",
        micro_override=True)}, "closed": []})
    broker = FakeBroker(equity=29.0,
                        positions={"OLD": {"qty": "1", "unrealized_pl": "0"}})
    daily.run(broker, cheap_breakout_universe(), TODAY)
    assert broker.brackets == []                # second micro trade blocked


def test_micro_override_steps_aside_once_equity_recovers(monkeypatch):
    """Crossing the threshold restores doctrine sizing automatically,
    with no separate flag to unset."""
    monkeypatch.setenv("RS_MICRO_ACCOUNT_OVERRIDE", "YES")
    broker = FakeBroker(equity=100_000.0)
    report = daily.run(broker, breakout_universe(), TODAY)
    assert "MICRO OVERRIDE" not in report
    assert broker.brackets and broker.brackets[0][1] > 1    # doctrine sizing
