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

    def submit_bracket(self, symbol, qty, stop_price, target_price):
        self.brackets.append((symbol, qty, stop_price, target_price))
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
