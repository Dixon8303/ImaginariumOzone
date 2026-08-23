"""Alpaca PAPER trading client — §87 shadow track, equities only.

The base URL is a hard-coded constant pointing at Alpaca's paper
endpoint. There is deliberately NO way to aim this client at a live
account: no URL parameter, no environment override. Keys come from
APCA_API_KEY_ID / APCA_API_SECRET_KEY env vars (paper keys), and
RS_PAPER_ARMED=YES is required — the same interlock pattern HoneyDrip
uses. Fake money by construction; still treated with real discipline.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

PAPER_URL = "https://paper-api.alpaca.markets"   # hard-coded, never overridden


class PaperBroker:
    def __init__(self):
        if os.environ.get("RS_PAPER_ARMED") != "YES":
            raise SystemExit("ABORT: RS_PAPER_ARMED must be YES to run the "
                             "paper shadow track.")
        key = os.environ.get("APCA_API_KEY_ID")
        secret = os.environ.get("APCA_API_SECRET_KEY")
        if not key or not secret:
            raise SystemExit("APCA_API_KEY_ID / APCA_API_SECRET_KEY not set.")
        self._headers = {"APCA-API-KEY-ID": key,
                         "APCA-API-SECRET-KEY": secret,
                         "Content-Type": "application/json"}

    def _req(self, method: str, path: str, body: dict | None = None,
             params: dict | None = None):
        url = PAPER_URL + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, headers=self._headers,
                                     method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = resp.read()
        return json.loads(payload) if payload else None

    # ── account state ────────────────────────────────────────────────
    def account(self) -> dict:
        return self._req("GET", "/v2/account")

    def positions(self) -> dict:
        return {p["symbol"]: p for p in self._req("GET", "/v2/positions")}

    def orders(self, status: str = "open", symbols: str | None = None,
               limit: int = 50) -> list:
        params = {"status": status, "limit": limit, "direction": "desc"}
        if symbols:
            params["symbols"] = symbols
        return self._req("GET", "/v2/orders", params=params)

    def order(self, order_id: str) -> dict:
        return self._req("GET", f"/v2/orders/{order_id}")

    # ── actions ──────────────────────────────────────────────────────
    def submit_bracket(self, symbol: str, qty: int, stop_price: float,
                       target_price: float,
                       limit_price: float | None = None) -> dict:
        """Buy queued for the next open (matching the backtester's
        next-open entry) with attached stop and target.

        `limit_price` is how the adopted H15a fill-gap cancellation is
        expressed to a broker: a limit at the doctrine's ceiling fills at
        the open when the open is at or below it, and simply does not
        fill when the open gapped through — which is the cancellation.
        Omitted only by callers that deliberately want an uncapped
        market order; live doctrine always passes it."""
        body = {
            "symbol": symbol, "qty": str(qty), "side": "buy",
            "time_in_force": "day", "order_class": "bracket",
            "take_profit": {"limit_price": f"{target_price:.2f}"},
            "stop_loss": {"stop_price": f"{stop_price:.2f}"},
        }
        if limit_price is None:
            body["type"] = "market"
        else:
            body["type"] = "limit"
            body["limit_price"] = f"{limit_price:.2f}"
        return self._req("POST", "/v2/orders", body=body)

    def cancel_symbol_orders(self, symbol: str) -> int:
        n = 0
        for o in self.orders(status="open", symbols=symbol):
            self._req("DELETE", f"/v2/orders/{o['id']}")
            n += 1
        return n

    def close_position(self, symbol: str) -> dict:
        return self._req("DELETE", f"/v2/positions/{symbol}")
