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
def test_variants_cover_every_named_hypothesis():
    """Entry filters and fill-time cancellations together must account
    for every name in VARIANT_NAMES — no hypothesis silently unrun."""
    from mve.hypotheses import GAP_VARIANTS, VARIANT_NAMES, build_variants
    entry = build_variants({}, {}, {})
    assert set(entry) | set(GAP_VARIANTS) == set(VARIANT_NAMES)
    assert not set(entry) & set(GAP_VARIANTS)      # no double-counting
    for name in ("H9a_quiet_news_2x", "H10_profitable", "H11a_overhead_10pct",
                 "H13a_quiet_base_40", "H14a_close_top30",
                 "H16a_max2_signals"):
        assert name in entry
    assert set(GAP_VARIANTS) == {"H15a_gap_2pct", "H15b_gap_1pct"}


def test_round5_filters_fail_closed_with_no_data():
    """No news and no fundamentals on disk -> those filters block every
    signal rather than silently passing them."""
    from mve.hypotheses import build_variants
    v = build_variants({}, {}, {})
    df = bars([(90, 100, 95, 1000)] * 40)
    assert v["H9a_quiet_news_2x"]("T", df, None) is False
    assert v["H10_profitable"]("T", df, None) is False


# ══════════════════════ round 6: H12-H17 ═════════════════════════════
def ohlc(rows):
    """rows of (open, high, low, close) -> path frame for simulate()."""
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"])


# ── H12 partial exits ────────────────────────────────────────────────
PATH_BASE = dict(entry=100.0, stop0=95.0, r_denom=5.0, entry_atr=2.0)


def test_partial_books_half_then_runs_to_target():
    from mve.exit_study import POLICIES, simulate
    # rises through +1.5R (107.5), then reaches +3R (115)
    rows = [(100, 108, 99, 107), (107, 116, 106, 115)] + [(115, 116, 114, 115)] * 5
    out = simulate(ohlc(rows), **PATH_BASE, policy=POLICIES["partial_15"])
    # half booked at 1.5R, half at the 3R target = 2.25R
    assert out["r"] == pytest.approx(0.5 * 1.5 + 0.5 * 3.0)
    assert out["reason"].startswith("partial_")


def test_partial_runner_stops_at_breakeven_not_the_original_stop():
    """After booking half, the runner rides at entry — a full round trip
    keeps the booked gain instead of giving it all back."""
    from mve.exit_study import POLICIES, simulate
    rows = [(100, 108, 99, 107), (107, 107, 94, 95)] + [(95, 96, 94, 95)] * 5
    out = simulate(ohlc(rows), **PATH_BASE, policy=POLICIES["partial_15"])
    assert out["r"] == pytest.approx(0.5 * 1.5 + 0.5 * 0.0)   # +0.75R
    assert out["r"] > 0


def test_partial_loser_is_unchanged_from_all_or_nothing():
    """A trade that never reaches the partial level must behave exactly
    like the wide policy — the scheme cannot help losers."""
    from mve.exit_study import POLICIES, simulate
    rows = [(100, 101, 94, 94)] + [(94, 95, 93, 94)] * 5
    partial = simulate(ohlc(rows), **PATH_BASE, policy=POLICIES["partial_15"])
    wide = simulate(ohlc(rows), **PATH_BASE, policy=POLICIES["wide"])
    assert partial["r"] == wide["r"] == pytest.approx(-1.0)
    assert not partial["reason"].startswith("partial_")


# ── H13 volatility contraction ───────────────────────────────────────
def rising_bars(n, spread):
    rows = []
    for i in range(n):
        c = 100 + 0.1 * i
        rows.append((c - spread, c + spread, c, 1000))
    return bars(rows)


def test_atr_percentile_low_for_a_quiet_tape():
    from mve.hypotheses import atr_percentile, quiet_base
    wide = rising_bars(200, 5.0)
    quiet = rising_bars(120, 0.2)
    df = pd.concat([wide, quiet], ignore_index=True)
    df["trade_date"] = pd.bdate_range("2024-01-02",
                                      periods=len(df)).date.astype(str)
    pct = atr_percentile(df)
    assert pct is not None and pct < 0.4       # currently calm vs its year
    assert quiet_base(df, 0.40)


def test_atr_percentile_fails_closed_on_short_history():
    from mve.hypotheses import atr_percentile, quiet_base
    assert atr_percentile(rising_bars(100, 1.0)) is None
    assert not quiet_base(rising_bars(100, 1.0), 0.40)


# ── H14 close strength ───────────────────────────────────────────────
def test_close_strength_reads_the_bar():
    from mve.hypotheses import close_strength, strong_close
    top = bars([(90, 100, 99.5, 1000)])           # closed near the high
    mid = bars([(90, 100, 95, 1000)])
    assert close_strength(top) == pytest.approx(0.95)
    assert close_strength(mid) == pytest.approx(0.5)
    assert strong_close(top, 0.70) and not strong_close(mid, 0.70)
    flat = bars([(100, 100, 100, 1000)])          # zero range -> undefined
    assert close_strength(flat) is None
    assert not strong_close(flat, 0.70)


# ── H16 clustering ───────────────────────────────────────────────────
def test_uncrowded_day_counts_signals():
    from mve.hypotheses import daily_signal_counts, uncrowded_day
    class R:
        signal_dates = ["2026-08-10"] * 5 + ["2026-08-11"]
    counts = daily_signal_counts(R())
    assert counts == {"2026-08-10": 5, "2026-08-11": 1}
    assert not uncrowded_day(counts, "2026-08-10", 2)     # crowded
    assert uncrowded_day(counts, "2026-08-11", 2)
    assert uncrowded_day(counts, "2026-08-12", 2)         # no signals at all


# ── H15 gap guard + H17 sizing diagnostic ────────────────────────────
def test_gap_guard_cancels_the_fill_and_counts_it():
    from datetime import date as _d
    from mve.backtest import run_backtest
    from mve.store import DataStore
    from mve.vendors import SyntheticVendor
    import tempfile
    store = DataStore(tempfile.mkdtemp())
    v = SyntheticVendor(start=_d(2023, 1, 2), days=400)
    store.ingest_bars(v.bars("SPY", base=500.0, drift=0.0002, amp=0.02))
    store.ingest_bars(v.bars("RUNR", base=80.0, drift=0.003, amp=0.012,
                             phase=1.0))
    loose = run_backtest(store, universe=["RUNR"], benchmark="SPY",
                         sector_map={})
    tight = run_backtest(store, universe=["RUNR"], benchmark="SPY",
                         sector_map={}, max_gap_pct=0.0)
    assert tight.gapped_signals > 0            # some opens gapped up
    assert len(tight.trades) < len(loose.trades)
    assert loose.gapped_signals == 0           # off by default


def test_per_score_buckets_expectancy():
    from mve.backtest import BacktestResult, Trade
    res = BacktestResult(trades=[
        Trade("A", "RS-02", "d", "d", 1, 1, 2.0, "target", 5, score=10),
        Trade("B", "RS-02", "d", "d", 1, 1, 1.0, "target", 5, score=10),
        Trade("C", "RS-02", "d", "d", 1, 1, -1.0, "stop", 5, score=8),
        Trade("D", "RS-02", "d", "d", 1, 1, 0.5, "time", 5, score=6),
    ])
    by = res.per_score()
    assert by["10"] == {"trades": 2, "expectancy_r": 1.5}
    assert by["8"] == {"trades": 1, "expectancy_r": -1.0}
    assert by["<=7"] == {"trades": 1, "expectancy_r": 0.5}
    assert by["9"] == {"trades": 0, "expectancy_r": 0.0}


# ── multiple-comparisons footer ──────────────────────────────────────
def test_summary_reports_expected_false_positives():
    from mve.hypotheses import summary
    def st(n, e):
        return {"trades": n, "expectancy_r": e, "win_rate": 0.6}
    results = {"CONTROL": {"train": st(100, 0.2), "test": st(60, 0.2),
                           "filtered": 0, "by_ticker": {}},
               "BASELINE_DOCTRINE": {"train": st(100, 0.3), "test": st(60, 0.25),
                                     "filtered": 0, "by_ticker": {}}}
    for i in range(12):
        results[f"H{i}_x"] = {"train": st(90, 0.31), "test": st(55, 0.26),
                              "filtered": 5, "by_ticker": {}}
    text = summary(results)
    assert "MULTIPLE COMPARISONS: 12 variants tested" in text
    assert "~0.6 ADOPT-CANDIDATEs expected from chance" in text


# ══════════════════ partial-data guard (real incident) ═══════════════
def test_data_coverage_finds_missing_tickers():
    from mve.hypotheses import data_coverage
    news = {"AAPL": pd.DataFrame({"articles": [1]}),
            "NVDA": pd.DataFrame(),           # fetched but empty
            }
    covered, required, missing = data_coverage(news, {"AAPL", "NVDA", "TSLA"})
    assert (covered, required) == (1, 3)
    assert missing == ["NVDA", "TSLA"]


def test_partial_fetch_invalidates_the_verdict():
    """The 2026-08-17 incident: a dropped connection left news for 7 of
    22 tickers. H9 must be INVALID, not scored — a fail-closed filter on
    partial data reports a verdict about the covered names only."""
    from mve.hypotheses import summary
    def st(n, e):
        return {"trades": n, "expectancy_r": e, "win_rate": 0.6}
    results = {
        "CONTROL": {"train": st(100, 0.2), "test": st(60, 0.2),
                    "filtered": 0, "by_ticker": {}},
        "BASELINE_DOCTRINE": {"train": st(100, 0.3), "test": st(60, 0.25),
                              "filtered": 0, "by_ticker": {}},
        "H9a_quiet_news_2x": {
            "train": st(40, 0.9), "test": st(25, 0.8),   # looks fantastic
            "filtered": 300, "by_ticker": {},
            "invalid": "data covers only 7/21 tickers — this would be a "
                       "verdict about those names, not about the filter."},
    }
    text = summary(results)
    assert "H9a_quiet_news_2x: INVALID" in text
    assert "7/21 tickers" in text
    # never scored despite showing +0.9R — check the variant's own line,
    # since the footer legitimately mentions the term
    verdict_lines = [ln for ln in text.splitlines()
                     if "H9a_quiet_news_2x" in ln]
    assert verdict_lines and not any("ADOPT-CANDIDATE" in ln
                                     for ln in verdict_lines)


# ══════════════ fetch resilience (2026-08-17 incidents) ══════════════
def test_sec_requires_a_contact_email(monkeypatch):
    """The SEC returns 403 without a contact address in the User-Agent.
    It is read from the environment, never hard-coded — an email is the
    operator's to give and does not belong in a public repo."""
    from mve import fundamentals
    monkeypatch.delenv("SEC_CONTACT_EMAIL", raising=False)
    with pytest.raises(SystemExit, match="SEC_CONTACT_EMAIL"):
        fundamentals._ua()
    monkeypatch.setenv("SEC_CONTACT_EMAIL", "not-an-email")
    with pytest.raises(SystemExit):
        fundamentals._ua()
    monkeypatch.setenv("SEC_CONTACT_EMAIL", "someone@example.com")
    ua = fundamentals._ua()
    assert "someone@example.com" in ua["User-Agent"]


def test_news_backoff_is_seconds_not_milliseconds():
    """DNS resolvers need seconds to recover; the first backoff was too
    fast and let the same dropout repeat."""
    from mve.news import BACKOFF_S
    assert BACKOFF_S >= 1.0
