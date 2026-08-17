"""Round 5 inputs: H9 news attention, H10 fundamentals, H11 volume profile."""
import pandas as pd
import pytest

from mve.fundamentals import (is_profitable, parse_concept,
                              trailing_net_income)
from mve.news import (BASELINE_DAYS, RECENT_DAYS, attention_ratio, parse_news,
                      quiet_attention)
from mve.volume_profile import (MIN_PROFILE_BARS, clear_overhead,
                                overhead_supply, point_of_control,
                                volume_by_price)


# ══════════════════════════════ H11 volume profile ═══════════════════
def bars(rows):
    """rows of (low, high, close, volume) -> bar frame."""
    return pd.DataFrame({
        "trade_date": pd.bdate_range("2025-01-02",
                                     periods=len(rows)).date.astype(str),
        "open": [r[2] for r in rows], "high": [r[1] for r in rows],
        "low": [r[0] for r in rows], "close": [r[2] for r in rows],
        "volume": [r[3] for r in rows]})


def test_volume_by_price_conserves_volume():
    df = bars([(90, 110, 100, 1000)] * 40)
    profile = volume_by_price(df)
    assert profile["volume"].sum() == pytest.approx(40 * 1000)


def test_overhead_supply_high_when_price_sits_at_the_low():
    """40 sessions traded up at 100-110, now price is at the bottom —
    almost all past volume is overhead."""
    rows = [(100, 110, 105, 1000)] * 39 + [(99, 101, 100, 1000)]
    share = overhead_supply(bars(rows))
    assert share is not None and share > 0.8


def test_overhead_supply_low_after_a_breakout():
    """Long base, then a break above it: little volume sits above."""
    rows = [(90, 100, 95, 1000)] * 39 + [(100, 130, 128, 1000)]
    share = overhead_supply(bars(rows))
    assert share is not None and share < 0.10


def test_overhead_supply_fails_closed_on_thin_history():
    assert overhead_supply(bars([(90, 100, 95, 1000)]
                                * (MIN_PROFILE_BARS - 1))) is None
    assert not clear_overhead(bars([(90, 100, 95, 1000)] * 5), 0.10)
    assert overhead_supply(bars([(100, 100, 100, 0)] * 40)) is None


def test_clear_overhead_threshold():
    rows = [(90, 100, 95, 1000)] * 39 + [(100, 130, 128, 1000)]
    df = bars(rows)
    assert clear_overhead(df, 0.10)
    assert not clear_overhead(df, 0.0001)


def test_point_of_control_finds_the_busy_level():
    """Most volume traded around 95; a little around 130."""
    rows = [(94, 96, 95, 10_000)] * 39 + [(129, 131, 130, 100)]
    poc = point_of_control(bars(rows))
    assert poc is not None and 90 < poc < 105


# ══════════════════════════════ H9 news attention ════════════════════
def news_frame(pairs):
    return pd.DataFrame(pairs, columns=["trade_date", "articles"])


def test_parse_news_counts_by_day():
    payload = {"news": [
        {"created_at": "2026-08-10T14:00:00Z"},
        {"created_at": "2026-08-10T18:00:00Z"},
        {"created_at": "2026-08-11T14:00:00Z"},
    ]}
    df = parse_news(payload, "NVDA")
    assert list(df["articles"]) == [2, 1]
    assert parse_news({"news": []}, "NVDA").empty


def test_attention_ratio_spikes_and_calm():
    # baseline: 1 article/day for the older window; recent: 10/day
    older = [(str(pd.Timestamp("2026-08-14") - pd.Timedelta(days=d)).split()[0],
              1) for d in range(RECENT_DAYS + 1, BASELINE_DAYS)]
    recent = [(str(pd.Timestamp("2026-08-14") - pd.Timedelta(days=d)).split()[0],
               10) for d in range(RECENT_DAYS)]
    news = {"T": news_frame(sorted(older + recent))}
    ratio = attention_ratio(news, "T", "2026-08-14")
    assert ratio is not None and ratio > 5           # loud
    assert not quiet_attention(news, "T", "2026-08-14", 2.0)

    calm = {"T": news_frame(sorted(older + [(d, 1) for d, _ in recent]))}
    assert quiet_attention(calm, "T", "2026-08-14", 2.0)


def test_attention_is_point_in_time():
    """Articles published AFTER the signal date must not count."""
    rows = [("2026-08-10", 1), ("2026-08-20", 500)]
    news = {"T": news_frame(rows)}
    # the future spike is excluded, and the remaining baseline is too thin
    assert attention_ratio(news, "T", "2026-08-14") is None


def test_attention_fails_closed_without_baseline():
    assert attention_ratio({}, "T", "2026-08-14") is None
    thin = {"T": news_frame([("2026-08-13", 1)])}
    assert attention_ratio(thin, "T", "2026-08-14") is None
    assert not quiet_attention(thin, "T", "2026-08-14", 2.0)


# ══════════════════════════ H10 fundamentals ═════════════════════════
def test_parse_concept_keeps_quarters_and_earliest_filing():
    payload = {"units": {"USD": [
        {"start": "2026-01-01", "end": "2026-03-31", "filed": "2026-05-01",
         "val": 100},
        # same period re-reported later — keep the first publication
        {"start": "2026-01-01", "end": "2026-03-31", "filed": "2026-08-01",
         "val": 105},
        # annual figure — excluded, it would double-count
        {"start": "2025-01-01", "end": "2025-12-31", "filed": "2026-02-01",
         "val": 900},
        {"start": "2026-04-01", "end": "2026-06-30", "filed": "2026-08-01",
         "val": 120},
    ]}}
    df = parse_concept(payload)
    assert len(df) == 2
    assert df[df["period_end"] == "2026-03-31"]["filed"].iloc[0] == "2026-05-01"
    assert df[df["period_end"] == "2026-03-31"]["value"].iloc[0] == 100


def facts_frame(rows):
    return pd.DataFrame(rows, columns=["filed", "period_end", "value"])


FOUR_Q = facts_frame([
    ("2025-05-01", "2025-03-31", 100.0),
    ("2025-08-01", "2025-06-30", 110.0),
    ("2025-11-01", "2025-09-30", 120.0),
    ("2026-02-01", "2025-12-31", 130.0),
])


def test_trailing_net_income_uses_filing_dates():
    facts = {"T": FOUR_Q}
    assert trailing_net_income(facts, "T", "2026-03-01") == pytest.approx(460.0)
    # one day before the fourth filing, only three quarters are public
    assert trailing_net_income(facts, "T", "2026-01-31") is None


def test_is_profitable_and_fail_closed():
    assert is_profitable({"T": FOUR_Q}, "T", "2026-03-01")
    losses = facts_frame([(f, p, -50.0) for f, p, _ in
                          FOUR_Q.itertuples(index=False)])
    assert not is_profitable({"T": losses}, "T", "2026-03-01")
    assert not is_profitable({}, "T", "2026-03-01")          # unknown blocks
    assert not is_profitable({"T": FOUR_Q}, "T", "2025-06-01")  # too early


# ══════════════════════════ study wiring ═════════════════════════════
def test_round5_variants_are_all_present():
    from mve.hypotheses import VARIANT_NAMES, build_variants
    variants = build_variants({}, {})
    assert set(variants) == set(VARIANT_NAMES)
    assert "H9a_quiet_news_2x" in variants
    assert "H10_profitable" in variants
    assert "H11a_overhead_10pct" in variants


def test_round5_filters_fail_closed_with_no_data():
    """No news and no fundamentals on disk -> those filters block every
    signal rather than silently passing them."""
    from mve.hypotheses import build_variants
    v = build_variants({}, {})
    df = bars([(90, 100, 95, 1000)] * 40)
    assert v["H9a_quiet_news_2x"]("T", df, None) is False
    assert v["H10_profitable"]("T", df, None) is False
