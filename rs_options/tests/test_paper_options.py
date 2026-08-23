"""Autonomous PAPER options: contract selection, sizing, the daily cycle."""
from datetime import date

import pytest

from mve.chain_select import DELTA_RANGE, DTE_RANGE, MAX_SPREAD_PCT
from paper import daily
from paper.options_broker import (MONEYNESS_TARGET, PaperOptionsBroker,
                                  contracts_to_buy, dte_of, parse_occ_symbol,
                                  select_contract, spread_pct)

AS_OF = date(2026, 8, 14)
SPOT = 200.0


def contract(strike, days_out=35, right="call", symbol=None):
    expiry = date.fromordinal(AS_OF.toordinal() + days_out)
    sym = symbol or (f"NVDA{expiry.strftime('%y%m%d')}"
                     f"{'C' if right == 'call' else 'P'}"
                     f"{int(strike * 1000):08d}")
    return {"symbol": sym, "type": right, "strike_price": str(strike),
            "expiration_date": str(expiry)}


def quote(bid, ask, delta=None):
    q = {"bid": bid, "ask": ask}
    if delta is not None:
        q["delta"] = delta
    return q


# ── OCC symbols ──────────────────────────────────────────────────────
def test_parse_occ_symbol():
    got = parse_occ_symbol("NVDA260918C00220000")
    assert got == {"ticker": "NVDA", "expiry": date(2026, 9, 18),
                   "right": "call", "strike": 220.0}
    assert parse_occ_symbol("SPY261218P00450500")["strike"] == 450.5
    assert parse_occ_symbol("not-a-symbol") is None
    assert parse_occ_symbol("NVDA269918C00220000") is None   # bad month


def test_dte_and_spread():
    assert dte_of(contract(200, days_out=30), AS_OF) == 30
    assert spread_pct(quote(9.5, 10.5)) == pytest.approx(0.10)
    assert spread_pct(quote(None, 10.5)) is None
    assert spread_pct(quote(10.5, 9.5)) is None      # crossed
    assert spread_pct(quote(0, 0)) is None


# ── selection ────────────────────────────────────────────────────────
def test_selects_nearest_target_delta_when_greeks_present():
    contracts = [contract(190), contract(200), contract(210)]
    quotes = {
        contracts[0]["symbol"]: quote(14.0, 14.4, delta=0.72),
        contracts[1]["symbol"]: quote(9.0, 9.3, delta=0.58),   # closest 0.60
        contracts[2]["symbol"]: quote(5.0, 5.2, delta=0.41),
    }
    pick = select_contract(contracts, SPOT, AS_OF, quotes)
    assert pick["symbol"] == contracts[1]["symbol"]
    assert pick["basis"] == "delta"
    assert pick["mid"] == pytest.approx(9.15)


def test_falls_back_to_moneyness_and_says_so():
    """No greeks in the data plan -> proxy, reported, never silent."""
    contracts = [contract(180), contract(194), contract(210)]
    quotes = {c["symbol"]: quote(9.0, 9.2) for c in contracts}
    pick = select_contract(contracts, SPOT, AS_OF, quotes)
    assert pick["basis"] == "moneyness"
    assert pick["delta"] is None
    # 200 * 0.97 = 194 -> the 194 strike is the target
    assert float(pick["strike_price"]) == 194.0
    assert MONEYNESS_TARGET == 0.97


def test_rejects_wide_spreads():
    c = contract(200)
    wide = {c["symbol"]: quote(9.0, 11.0, delta=0.60)}     # 20% spread
    assert select_contract([c], SPOT, AS_OF, wide) is None
    ok = {c["symbol"]: quote(9.5, 10.0, delta=0.60)}
    assert select_contract([c], SPOT, AS_OF, ok) is not None
    assert MAX_SPREAD_PCT == 0.10


def test_rejects_out_of_range_dte_and_delta():
    near = contract(200, days_out=DTE_RANGE[0] - 5)
    far = contract(200, days_out=DTE_RANGE[1] + 5)
    quotes = {c["symbol"]: quote(9.0, 9.2, delta=0.60) for c in (near, far)}
    assert select_contract([near, far], SPOT, AS_OF, quotes) is None

    deep = contract(120)
    q = {deep["symbol"]: quote(80.0, 80.5, delta=0.95)}    # above DELTA_RANGE
    assert select_contract([deep], SPOT, AS_OF, q) is None
    assert DELTA_RANGE == (0.40, 0.80)


def test_ignores_puts_and_unquoted_contracts():
    put = contract(200, right="put")
    call = contract(200)
    quotes = {put["symbol"]: quote(9.0, 9.2, delta=0.60)}   # call unquoted
    assert select_contract([put, call], SPOT, AS_OF, quotes) is None


# ── sizing ───────────────────────────────────────────────────────────
def test_sizes_by_max_loss():
    # $100k equity, 1% = $1,000 budget; a $2.50 contract costs $250 -> 4
    assert contracts_to_buy(2.50, 100_000, 0.01) == 4
    # a $12 contract costs $1,200 -> cannot afford one within budget
    assert contracts_to_buy(12.0, 100_000, 0.01) == 0
    assert contracts_to_buy(0.0, 100_000, 0.01) == 0
    assert contracts_to_buy(0.10, 100_000, 0.01) == 5        # hard cap


# ── broker guardrails ────────────────────────────────────────────────
def test_options_broker_inherits_paper_interlock(monkeypatch):
    from paper.options_broker import PAPER_URL
    assert PAPER_URL == "https://paper-api.alpaca.markets"
    monkeypatch.delenv("RS_PAPER_ARMED", raising=False)
    monkeypatch.setenv("APCA_API_KEY_ID", "k")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "s")
    with pytest.raises(SystemExit, match="RS_PAPER_ARMED"):
        PaperOptionsBroker()


# ── the daily option cycle ───────────────────────────────────────────
class FakeOptionsBroker:
    def __init__(self, positions=None, equity=100_000.0):
        self._positions = positions or {}
        self._equity = equity
        self.bought, self.sold = [], []

    def account(self):
        return {"equity": str(self._equity), "cash": str(self._equity)}

    def positions(self):
        return {}

    def option_positions(self):
        return self._positions

    def contracts(self, underlying, as_of, limit=200):
        return [contract(190), contract(194), contract(210)]

    def quotes(self, underlying):
        return {c["symbol"]: quote(2.4, 2.6, delta=0.60)
                for c in self.contracts(underlying, AS_OF)}

    def buy_to_open(self, symbol, qty, limit_price):
        self.bought.append((symbol, qty, limit_price))
        return {"id": "o1"}

    def sell_to_close(self, symbol, qty):
        self.sold.append((symbol, qty))
        return {"id": "o2"}


SIGNAL = dict(ticker="NVDA", close=SPOT, stop=190.0, target=230.0,
              r_denom=10.0, score=9, rationale="test")


def test_cycle_buys_a_contract_and_records_it():
    broker = FakeOptionsBroker()
    ledger = {"open": {}, "closed": []}
    opened, closed, notes = daily.run_option_cycle(
        broker, [SIGNAL], {}, str(AS_OF), ledger)
    assert len(opened) == 1 and broker.bought
    symbol, qty, limit = broker.bought[0]
    assert qty == 4                       # $250/contract vs $1,000 budget
    assert limit == pytest.approx(2.5)    # limit at the mid, not market
    rec = ledger["options"][symbol]
    assert rec["ticker"] == "NVDA"
    assert rec["invalidation_price"] == 190.0
    assert rec["entry_underlying"] == SPOT


def test_cycle_exits_on_doctrine_and_frees_the_name():
    """A held contract whose underlying broke invalidation must be sold."""
    import pandas as pd
    symbol = contract(194)["symbol"]
    ledger = {"open": {}, "closed": [], "options": {symbol: dict(
        ticker="NVDA", qty=2, entry_price=2.5, expiry="2026-09-18",
        strike=194.0, entry_date="2026-08-10", invalidation_price=190.0,
        entry_underlying=200.0, basis="delta", delta=0.6, spread_pct=0.02)}}
    broker = FakeOptionsBroker(positions={symbol: {"unrealized_pl": "-120"}})
    bars = {"NVDA": pd.DataFrame({"trade_date": ["2026-08-14"],
                                  "close": [185.0]})}   # below invalidation
    opened, closed, notes = daily.run_option_cycle(
        broker, [], bars, str(AS_OF), ledger)
    assert broker.sold == [(symbol, 2)]
    assert symbol not in ledger["options"]
    assert any("INVALIDATION" in r for r in closed[0][3])


def test_cycle_reconciles_a_position_that_vanished():
    symbol = contract(194)["symbol"]
    ledger = {"open": {}, "closed": [], "options": {symbol: dict(
        ticker="NVDA", qty=1, entry_price=2.5, expiry="2026-09-18",
        strike=194.0, entry_date="2026-08-10", invalidation_price=190.0,
        entry_underlying=200.0, basis="delta", delta=0.6, spread_pct=0.02)}}
    broker = FakeOptionsBroker()          # holds nothing
    opened, closed, notes = daily.run_option_cycle(
        broker, [], {}, str(AS_OF), ledger)
    assert ledger["options"] == {}
    assert closed[0][3] == "reconciled"
    assert broker.sold == []              # nothing to sell


def test_cycle_holds_one_contract_per_name():
    symbol = contract(194)["symbol"]
    ledger = {"open": {}, "closed": [], "options": {symbol: dict(
        ticker="NVDA", qty=1, entry_price=2.5, expiry="2026-09-18",
        strike=194.0, entry_date="2026-08-14", invalidation_price=190.0,
        entry_underlying=200.0, basis="delta", delta=0.6, spread_pct=0.02)}}
    import pandas as pd
    bars = {"NVDA": pd.DataFrame({"trade_date": ["2026-08-14"],
                                  "close": [205.0]})}
    broker = FakeOptionsBroker(positions={symbol: {"unrealized_pl": "20"}})
    opened, _, _ = daily.run_option_cycle(broker, [SIGNAL], bars,
                                          str(AS_OF), ledger)
    assert opened == [] and broker.bought == []


def test_cycle_notes_unaffordable_premium():
    class Pricey(FakeOptionsBroker):
        def quotes(self, underlying):
            return {c["symbol"]: quote(40.0, 40.5, delta=0.60)
                    for c in self.contracts(underlying, AS_OF)}

    broker = Pricey()
    ledger = {"open": {}, "closed": []}
    opened, _, notes = daily.run_option_cycle(broker, [SIGNAL], {},
                                              str(AS_OF), ledger)
    assert opened == [] and broker.bought == []
    assert any("risk budget" in n for n in notes)


def test_cycle_notes_when_no_contract_qualifies():
    class NoChain(FakeOptionsBroker):
        def contracts(self, underlying, as_of, limit=200):
            return []

        def quotes(self, underlying):
            return {}

    opened, _, notes = daily.run_option_cycle(
        NoChain(), [SIGNAL], {}, str(AS_OF), {"open": {}, "closed": []})
    assert opened == []
    assert any("no contract met" in n for n in notes)


def test_option_failure_never_kills_the_equity_run():
    """The equity track is the validated one — an options outage must
    degrade to a note, not an exception."""
    class Broken(FakeOptionsBroker):
        def contracts(self, underlying, as_of, limit=200):
            raise RuntimeError("chain endpoint down")

    opened, _, notes = daily.run_option_cycle(
        Broken(), [SIGNAL], {}, str(AS_OF), {"open": {}, "closed": []})
    assert opened == []
    assert any("chain unavailable" in n for n in notes)


# ------------------------------- option cost recorder (no capital needed)

def test_min_equity_shows_the_notional_cap_binds_first():
    """A small account places no orders because the 5% cap binds long
    before the 1% risk rule does. Stating which limit binds is the
    difference between 'broken' and 'working as designed'."""
    from paper.option_costs import min_equity_for_share
    # $200 stock, $8 stop: risk rule needs $800, cap needs $4,000.
    assert min_equity_for_share(200.0, 8.0) == pytest.approx(4000.0)
    # a wide stop can flip which limit binds
    assert min_equity_for_share(20.0, 5.0) == pytest.approx(500.0)


def test_min_equity_for_contract_uses_the_position_cap():
    from paper.option_costs import min_equity_for_contract
    # $2.50 mid -> $250 a contract -> $5,000 to hold it inside 5%
    assert min_equity_for_contract(2.50) == pytest.approx(5000.0)


class _QuoteBroker:
    """Market data only — no orders, no buying power, no permissions."""
    def __init__(self, bid=2.40, ask=2.60):
        self._bid, self._ask = bid, ask

    def contracts(self, underlying, as_of, limit=200):
        return [{"symbol": "AAA260918C00100000", "strike_price": "100",
                 "expiration_date": "2026-09-18", "type": "call"}]

    def quotes(self, underlying):
        return {"AAA260918C00100000": {"bid": self._bid, "ask": self._ask,
                                       "ap": self._ask, "delta": 0.60}}


def test_quote_doctrine_contract_prices_the_real_trade():
    from paper.option_costs import quote_doctrine_contract
    row = quote_doctrine_contract(_QuoteBroker(), "AAA", 100.0, "2026-08-23")
    assert row is not None
    assert row["cost_per_contract"] == pytest.approx(250.0)   # $2.50 mid
    assert row["min_equity_for_contract"] == pytest.approx(5000.0)
    assert row["spread_pct"] == pytest.approx(0.08, abs=0.001)


def test_missing_quotes_record_nothing_rather_than_zero():
    """A missing quote is not a zero cost — the row must be absent, not
    cheap, or the affordability report would lie downward."""
    from paper.option_costs import collect, quote_doctrine_contract

    class Dead:
        def contracts(self, *a, **k):
            raise RuntimeError("no options subscription")

        def quotes(self, *a, **k):
            raise RuntimeError("no options subscription")

    assert quote_doctrine_contract(Dead(), "AAA", 100.0, "2026-08-23") is None
    assert collect(Dead(), [{"ticker": "AAA", "close": 100.0}],
                   "2026-08-23") == []


def test_format_costs_states_the_account_size_needed():
    from paper.option_costs import collect, format_costs
    rows = collect(_QuoteBroker(), [{"ticker": "AAA", "close": 100.0,
                                     "stop": 96.0, "r_denom": 4.0}],
                   "2026-08-23")
    text = format_costs(rows, equity=29.0)
    assert "$250.00 per contract" in text
    assert "you can buy 0 of 1" in text
    assert "$5,000" in text                  # the honest requirement
    assert "risk rules working, not a bug" in text


def test_format_costs_with_no_rows_does_not_imply_free():
    from paper.option_costs import format_costs
    assert "not a zero cost" in format_costs([], equity=29.0)
