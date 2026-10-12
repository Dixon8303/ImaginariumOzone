"""The 2026-10-12 census reported a verdict it had no evidence for.

It probed 30 and 400 calendar days before a Monday — a Saturday and a
Sunday. Every feed correctly returned zero records for a closed market,
and the report read those zeros as proof SIP was unentitled and
recommended closing H-27 on that basis.

Two defects, pinned here:
  1. Window selection ignored the market calendar.
  2. The verdict consulted only SIP, never the IEX control, so it spoke
     confidently while its own control was failing.
"""
from datetime import date, timezone

import pytest

from mve.data_entitlement import (control_ok, format_census, sip_is_usable,
                                  trading_day_back, windows)

WINDOWS = ["recent (30d)", "deep (400d)"]
ENDPOINTS = ["trades", "quotes"]


def row(feed, window, endpoint, status=200, count=50, error=""):
    return {"feed": feed, "window": window, "endpoint": endpoint,
            "status": status, "endpoint_error": None, "count": count,
            "error": error}


def results(iex_count=50, sip_count=50, sip_status=200, sip_error=""):
    out = [row("iex", w, e, 200, iex_count) for w in WINDOWS for e in ENDPOINTS]
    out += [row("sip", w, e, sip_status, sip_count, sip_error)
            for w in WINDOWS for e in ENDPOINTS]
    return out


# ── defect 1: the window landed on a closed market ────────────────────
def test_the_exact_dates_that_invalidated_the_first_census():
    """2026-10-12 was a Monday. 30 and 400 days back are a Saturday and a
    Sunday — the naive subtraction the first census shipped."""
    monday = date(2026, 10, 12)
    assert (monday - __import__('datetime').timedelta(days=30)).weekday() == 5
    assert (monday - __import__('datetime').timedelta(days=400)).weekday() == 6
    # ...and the fix walks both back onto weekdays.
    assert trading_day_back(monday, 30).weekday() <= 4
    assert trading_day_back(monday, 400).weekday() <= 4


@pytest.mark.parametrize("anchor", [
    date(2026, 10, 12), date(2026, 10, 13), date(2026, 10, 14),
    date(2026, 10, 15), date(2026, 10, 16), date(2026, 10, 17),
    date(2026, 10, 18),
])
@pytest.mark.parametrize("back", [30, 400])
def test_no_anchor_day_ever_probes_a_weekend(anchor, back):
    """Whatever day the operator clicks Run, both reaches land on a
    weekday. A weekend probe is unanswerable, not informative."""
    assert trading_day_back(anchor, back).weekday() <= 4


def test_windows_are_inside_regular_hours_and_ordered():
    for label, start, end in windows(date(2026, 10, 12)):
        assert start.tzinfo == timezone.utc
        assert start.hour == 15, "15:00 UTC is 11:00 ET, inside RTH either DST regime"
        assert end > start
        assert start.weekday() <= 4


# ── defect 2: a verdict rendered while the control was failing ────────
def test_control_fails_when_iex_is_empty():
    """The precise shape of the bad census: everything 200, everything
    zero. The control must catch it."""
    assert control_ok(results(iex_count=0, sip_count=0)) is False


def test_the_bad_census_renders_no_verdict_now():
    text = format_census({"probed_symbol": "SPY",
                          "results": results(iex_count=0, sip_count=0)})
    assert "NO VERDICT" in text
    assert "NOT usable on this account" not in text, \
        "must not claim an entitlement finding when the control failed"
    assert "INCONCLUSIVE" not in text, \
        "must not recommend a disposition for H-27 from a dead probe"


def test_control_passing_allows_a_real_denial_verdict():
    """IEX flowing, SIP refused — that IS the finding the census exists
    for, and it must still be reachable."""
    rs = results(iex_count=50, sip_count=0, sip_status=403,
                 sip_error='{"message":"subscription does not permit sip"}')
    assert control_ok(rs) is True
    assert sip_is_usable(rs) is False
    text = format_census({"probed_symbol": "SPY", "results": rs})
    assert "NO VERDICT" not in text
    assert "NOT usable on this account" in text
    assert "INCONCLUSIVE" in text


def test_control_passing_allows_a_usable_verdict():
    rs = results(iex_count=50, sip_count=50)
    assert control_ok(rs) is True
    assert sip_is_usable(rs) is True
    text = format_census({"probed_symbol": "SPY", "results": rs})
    assert "NO VERDICT" not in text
    assert "NOT ruled out" in text
    assert "UNMEASURED" in text, "the latency half must stay explicitly unmeasured"


# ── the original traps, still held ────────────────────────────────────
def test_sip_200_with_zero_records_is_not_entitlement():
    assert sip_is_usable(results(sip_count=0)) is False


def test_sip_reaching_recent_but_not_deep_is_not_enough():
    """A tape that stops short of the study period cannot supply it."""
    rs = [row("iex", w, e) for w in WINDOWS for e in ENDPOINTS]
    rs += [row("sip", "recent (30d)", e, 200, 50) for e in ENDPOINTS]
    rs += [row("sip", "deep (400d)", e, 200, 0) for e in ENDPOINTS]
    assert control_ok(rs) is True
    assert sip_is_usable(rs) is False


def test_a_missing_probe_row_is_not_treated_as_a_pass():
    """An absent row must fail closed, not be skipped."""
    rs = [r for r in results() if not (r["feed"] == "sip"
                                       and r["window"] == "deep (400d)"
                                       and r["endpoint"] == "quotes")]
    assert sip_is_usable(rs) is False
