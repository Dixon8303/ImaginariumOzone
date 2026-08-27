"""mve.fundamentals: point-in-time facts, and the earnings-window proxy
built from a ticker's own filing cadence (no forward earnings-calendar
feed exists in this project — see docs/RESEARCH_LOG.md)."""
from datetime import date

import pandas as pd
import pytest

from mve.fundamentals import (EARNINGS_WINDOW_BUFFER_DAYS,
                              next_expected_filing_window,
                              overlaps_earnings_window)


def facts_with_filings(*filed_dates):
    return {"NVDA": pd.DataFrame({"filed": list(filed_dates),
                                  "period_end": list(filed_dates),
                                  "value": [1.0] * len(filed_dates)})}


def test_needs_at_least_two_filings():
    assert next_expected_filing_window(facts_with_filings("2026-01-01"),
                                       "NVDA", "2026-06-01") is None
    assert next_expected_filing_window({}, "NVDA", "2026-06-01") is None


def test_unknown_ticker_returns_none():
    """An ETF (QQQ, IWM) has no filings at all — must return None, never
    a fabricated window, so the earnings gate never fires on it."""
    facts = facts_with_filings("2026-01-01", "2026-04-01")
    assert next_expected_filing_window(facts, "QQQ", "2026-06-01") is None


def test_projects_forward_from_the_median_cadence():
    # three quarterly filings, ~91 days apart -> next expected ~91 days
    # after the last known one
    facts = facts_with_filings("2025-04-01", "2025-07-01", "2025-10-01")
    window = next_expected_filing_window(facts, "NVDA", "2026-01-01",
                                         buffer_days=5)
    assert window is not None
    start, end = date.fromisoformat(window[0]), date.fromisoformat(window[1])
    expected_center = date(2025, 10, 1) + (date(2025, 10, 1) - date(2025, 7, 1))
    assert start == expected_center - pd.Timedelta(days=5).to_pytimedelta()
    assert end == expected_center + pd.Timedelta(days=5).to_pytimedelta()


def test_only_uses_filings_known_as_of_trade_date():
    """Point-in-time: a filing dated AFTER trade_date must not leak into
    the cadence estimate."""
    facts = facts_with_filings("2025-04-01", "2025-07-01", "2025-10-01")
    # as-of a date before the third filing -> cadence from the first two
    # only: gap = 91 days, projected from 2025-07-01 -> 2025-09-30
    window = next_expected_filing_window(facts, "NVDA", "2025-08-01")
    assert window is not None
    assert window[0] == (date(2025, 9, 30)
                         - pd.Timedelta(days=EARNINGS_WINDOW_BUFFER_DAYS)
                         .to_pytimedelta()).isoformat()


def test_overlaps_earnings_window():
    window = ("2026-05-01", "2026-05-11")
    # holding period spans the window
    assert overlaps_earnings_window(date(2026, 4, 20), date(2026, 5, 20),
                                    window) is True
    # holding period entirely before it
    assert overlaps_earnings_window(date(2026, 3, 1), date(2026, 4, 1),
                                    window) is False
    # holding period entirely after it
    assert overlaps_earnings_window(date(2026, 6, 1), date(2026, 7, 1),
                                    window) is False


def test_unknown_window_never_gates():
    assert overlaps_earnings_window(date(2026, 1, 1), date(2026, 3, 1),
                                    None) is False
