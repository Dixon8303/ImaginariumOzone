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
    # Counts must differ the way real feeds do: IEX is one venue, SIP is
    # every venue. Equal counts are the silent-downgrade signature and are
    # covered separately below.
    rs = results(iex_count=50, sip_count=3000)
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


# ── defect 3: a saturated probe cannot tell entitlement from fallback ──
# The 2026-10-12 re-run returned exactly 100 on all eight cells, because
# the probe asked for limit=100. Saturated everywhere, it compared nothing
# — and reported SIP as entitled, which points at spending money.
from mve.data_entitlement import RECORD_LIMIT, feeds_are_distinct


def pair(iex_count, sip_count):
    out = [row("iex", w, e, 200, iex_count) for w in WINDOWS for e in ENDPOINTS]
    out += [row("sip", w, e, 200, sip_count) for w in WINDOWS for e in ENDPOINTS]
    return out


def test_both_feeds_saturated_is_not_evidence():
    """The exact shape of the 2026-10-12 re-run."""
    distinct, why = feeds_are_distinct(pair(RECORD_LIMIT, RECORD_LIMIT))
    assert distinct is False
    assert "ceiling" in why


def test_equal_counts_are_the_downgrade_signature():
    distinct, why = feeds_are_distinct(pair(100, 100))
    assert distinct is False
    assert "cannot be smaller than one venue" in why


def test_sip_smaller_than_iex_is_impossible_for_a_real_tape():
    distinct, _ = feeds_are_distinct(pair(500, 50))
    assert distinct is False


def test_sip_materially_larger_is_the_real_signal():
    """IEX holds a small share of consolidated volume, so a genuine SIP
    tape comes back many times larger on the same window."""
    distinct, why = feeds_are_distinct(pair(80, 3000))
    assert distinct is True
    assert why == ""


def test_sip_may_saturate_alone():
    """Only SIP hitting the ceiling still discriminates — it is the larger
    tape, which is the whole point."""
    distinct, _ = feeds_are_distinct(pair(80, RECORD_LIMIT))
    assert distinct is True


def test_indistinguishable_feeds_render_no_verdict():
    text = format_census({"probed_symbol": "SPY",
                          "results": pair(RECORD_LIMIT, RECORD_LIMIT)})
    assert "NO VERDICT" in text
    assert "NOT ruled out" not in text, \
        "must not read a saturated probe as entitlement"


def test_the_permissive_failure_mode_is_named_in_the_report():
    """The danger here runs toward spending, not toward stopping."""
    text = format_census({"probed_symbol": "SPY", "results": pair(100, 100)})
    assert "buy a tick tape" in text


def test_a_distinct_sip_tape_still_reaches_the_usable_verdict():
    """The fix must not make the affirmative finding unreachable."""
    text = format_census({"probed_symbol": "SPY", "results": pair(80, 3000)})
    assert "NO VERDICT" not in text
    assert "NOT ruled out" in text
    assert "not a silent downgrade" in text


def test_window_is_short_enough_to_avoid_saturation():
    from mve.data_entitlement import WINDOW_MINUTES
    assert WINDOW_MINUTES == 1
    assert RECORD_LIMIT >= 10_000
