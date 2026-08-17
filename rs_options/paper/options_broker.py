"""Alpaca PAPER options trading — contract discovery, selection, orders.

Closes the measurement gap this project has carried from the start:
every rule was validated on the UNDERLYING, never on the contract that
actually gets bought. Historical chains are paid data, but FORWARD paper
option fills cost nothing — so the shadow track can start recording real
option P&L today, with fake money.

Selection reuses the research constants (chain_select) rather than
re-typing them, so paper and doctrine cannot drift.

Greeks: Alpaca's snapshot feed carries delta when the account's data
subscription includes it. When it does not, selection falls back to a
MONEYNESS proxy, and the choice is reported — never silently swapped.

No live path exists here: every request goes through PaperBroker, whose
base URL is a hard-coded paper endpoint.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import date

from mve.chain_select import DELTA_RANGE, DELTA_TARGET, DTE_RANGE, MAX_SPREAD_PCT

from .alpaca_paper import PAPER_URL, PaperBroker

DATA_URL = "https://data.alpaca.markets"
# Delta ~0.60 on a 3-8 week call sits a few percent in the money. Used
# ONLY when greeks are unavailable (CALIBRATE, and reported as a proxy).
MONEYNESS_TARGET = 0.97
OCC_RE = re.compile(r"^(?P<root>[A-Z]+)(?P<ymd>\d{6})(?P<right>[CP])"
                    r"(?P<strike>\d{8})$")


def parse_occ_symbol(symbol: str) -> dict | None:
    """'NVDA260918C00220000' -> ticker/expiry/right/strike."""
    m = OCC_RE.match(symbol.strip().upper())
    if not m:
        return None
    ymd = m.group("ymd")
    try:
        expiry = date(2000 + int(ymd[:2]), int(ymd[2:4]), int(ymd[4:6]))
    except ValueError:
        return None
    return {"ticker": m.group("root"), "expiry": expiry,
            "right": "call" if m.group("right") == "C" else "put",
            "strike": int(m.group("strike")) / 1000.0}


def dte_of(contract: dict, as_of: date) -> int:
    return (date.fromisoformat(contract["expiration_date"]) - as_of).days


def spread_pct(quote: dict) -> float | None:
    """Bid-ask spread as a fraction of the mid. None when unquotable —
    an unquotable contract is not tradable and must not be guessed at."""
    bid, ask = quote.get("bid"), quote.get("ask")
    if bid is None or ask is None:
        return None
    bid, ask = float(bid), float(ask)
    mid = (bid + ask) / 2.0
    if mid <= 0 or ask < bid:
        return None
    return (ask - bid) / mid


def select_contract(contracts: list, spot: float, as_of: date,
                    quotes: dict | None = None) -> dict | None:
    """Pick one long call from a contract list.

    Filters: call, DTE in range, quotable, spread within cap, and delta
    in range when greeks are available. Ranks by closeness to the delta
    target, or to the moneyness proxy when delta is absent.

    Returns the contract dict with `basis` ('delta' or 'moneyness'),
    `mid`, and `delta` (when known) attached — the caller reports which
    basis was used.
    """
    quotes = quotes or {}
    scored = []
    for c in contracts:
        if c.get("type") != "call":
            continue
        dte = dte_of(c, as_of)
        if not DTE_RANGE[0] <= dte <= DTE_RANGE[1]:
            continue
        q = quotes.get(c["symbol"])
        if not q:
            continue
        sp = spread_pct(q)
        if sp is None or sp > MAX_SPREAD_PCT:
            continue
        mid = (float(q["bid"]) + float(q["ask"])) / 2.0
        delta = q.get("delta")
        if delta is not None:
            delta = float(delta)
            if not DELTA_RANGE[0] <= delta <= DELTA_RANGE[1]:
                continue
            basis, rank = "delta", abs(delta - DELTA_TARGET)
        else:
            strike = float(c["strike_price"])
            basis, rank = "moneyness", abs(strike - spot * MONEYNESS_TARGET)
        scored.append((rank, dict(c, basis=basis, mid=mid, delta=delta,
                                  dte=dte, spread_pct=sp)))
    if not scored:
        return None
    return min(scored, key=lambda x: x[0])[1]


def contracts_to_buy(premium_mid: float, equity: float, risk_pct: float,
                     max_contracts: int = 5) -> int:
    """Size by MAX LOSS: a long call can go to zero, so the premium is
    the risk. Conservative on purpose — it sizes smaller than a
    delta-based estimate would."""
    cost = premium_mid * 100.0
    if cost <= 0:
        return 0
    return max(0, min(int(equity * risk_pct / cost), max_contracts))


class PaperOptionsBroker(PaperBroker):
    """PaperBroker plus the options endpoints. Inherits the hard-coded
    paper URL and the RS_PAPER_ARMED interlock."""

    def contracts(self, underlying: str, as_of: date,
                  limit: int = 200) -> list:
        params = {
            "underlying_symbols": underlying,
            "expiration_date_gte": str(as_of.fromordinal(
                as_of.toordinal() + DTE_RANGE[0])),
            "expiration_date_lte": str(as_of.fromordinal(
                as_of.toordinal() + DTE_RANGE[1])),
            "type": "call", "status": "active", "limit": limit,
        }
        payload = self._req("GET", "/v2/options/contracts", params=params)
        return (payload or {}).get("option_contracts", []) or []

    def quotes(self, underlying: str) -> dict:
        """{occ_symbol: {bid, ask, delta?}} from the snapshot feed.
        Greeks appear only when the data subscription includes them."""
        url = (f"{DATA_URL}/v1beta1/options/snapshots/"
               f"{urllib.parse.quote(underlying)}?limit=1000")
        req = urllib.request.Request(url, headers=self._headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())
        out = {}
        for symbol, snap in (payload.get("snapshots") or {}).items():
            quote = snap.get("latestQuote") or {}
            greeks = snap.get("greeks") or {}
            if quote.get("bp") is None or quote.get("ap") is None:
                continue
            out[symbol] = {"bid": quote["bp"], "ap": quote["ap"],
                           "ask": quote["ap"], "delta": greeks.get("delta")}
        return out

    def option_positions(self) -> dict:
        """Held option contracts only, keyed by OCC symbol."""
        rows = self._req("GET", "/v2/positions") or []
        return {p["symbol"]: p for p in rows
                if p.get("asset_class") == "us_option"}

    def buy_to_open(self, symbol: str, qty: int, limit_price: float) -> dict:
        """Limit at the mid, day only (§38) — never a market order on an
        instrument whose spread is the main cost."""
        return self._req("POST", "/v2/orders", body={
            "symbol": symbol, "qty": str(qty), "side": "buy",
            "type": "limit", "limit_price": f"{limit_price:.2f}",
            "time_in_force": "day",
        })

    def sell_to_close(self, symbol: str, qty: int) -> dict:
        return self._req("POST", "/v2/orders", body={
            "symbol": symbol, "qty": str(qty), "side": "sell",
            "type": "market", "time_in_force": "day",
        })
