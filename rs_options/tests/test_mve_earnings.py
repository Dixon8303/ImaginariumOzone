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
    from mve.universe import UNIVERSE
    stocks = stock_tickers()
    assert not set(stocks) & ETF_TICKERS
    assert "AAPL" in stocks and "NVDA" in stocks
    assert "PFE" in stocks            # H-23 adoption flows through
    # Every non-ETF universe name, exactly — the old "<= 25 fits one
    # free-tier day" bound died with the H-23 adoption (36 stocks now);
    # the fetcher's skip-on-disk resume is what absorbs the API limit.
    assert len(stocks) == len(UNIVERSE) - len(ETF_TICKERS)
