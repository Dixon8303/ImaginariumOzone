"""Earnings-date layer (Alpha Vantage EARNINGS endpoint) — H5 data."""
from datetime import date

import pytest

from mve.earnings import (ETF_TICKERS, load_earnings, parse_earnings,
                          save_dates, stock_tickers)


def test_parse_earnings_payload():
    payload = {"symbol": "AAPL", "quarterlyEarnings": [
        {"fiscalDateEnding": "2026-03-31", "reportedDate": "2026-05-01"},
        {"fiscalDateEnding": "2025-12-31", "reportedDate": "2026-01-30"},
        {"fiscalDateEnding": "2025-09-30", "reportedDate": ""},   # dropped
    ]}
    assert parse_earnings(payload) == ["2026-01-30", "2026-05-01"]


def test_parse_earnings_rate_limit_note():
    with pytest.raises(ValueError, match="rate limit"):
        parse_earnings({"Note": "API rate limit reached"})


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    root = str(tmp_path / "earnings")
    save_dates("NVDA", ["2026-02-25", "2025-11-19"], root=root)
    out = load_earnings(root)
    assert out == {"NVDA": [date(2025, 11, 19), date(2026, 2, 25)]}
    assert load_earnings(str(tmp_path / "missing")) == {}


def test_stock_tickers_excludes_etfs():
    stocks = stock_tickers()
    assert not set(stocks) & ETF_TICKERS
    assert "AAPL" in stocks and "NVDA" in stocks
    assert len(stocks) <= 25          # fits the free daily request limit
