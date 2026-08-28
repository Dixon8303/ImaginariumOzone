"""H-24 / H-25 detectors and the setup-study criterion (registered
2026-08-28 in docs/PREREGISTERED.md; implemented after registration)."""
import pandas as pd
import pytest

from mve.setups import (ACTIVE_SETUPS, DETECTORS, INVALIDATION_LOOKBACK,
                        RECLAIM_WINDOW, RS01_STRUCTURE_SMA,
                        RS02_BREAKOUT_LOOKBACK, detect_h24, detect_h25)


def make_bars(closes, lows=None, highs=None):
    closes = list(closes)
    lows = lows or [c - 0.5 for c in closes]
    highs = highs or [c + 0.5 for c in closes]
    return pd.DataFrame({
        "trade_date": [f"d{i:04d}" for i in range(len(closes))],
        "open": closes, "high": highs, "low": lows, "close": closes,
        "volume": [1_000_000] * len(closes),
    })


FEATURES = {"rel_volume": 1.3, "bench_return": 0.01,
            "rs_beta_adjusted": 0.02, "rs_persistence": 0.7,
            "rs_market": 0.02, "rs_sector": None}


def weak_volume():
    return dict(FEATURES, rel_volume=0.6)


def bench_freefall():
    return dict(FEATURES, bench_return=-0.05)


# ── H-24 fixtures ────────────────────────────────────────────────────
def h24_bars(break_close_delta=-1.0, reclaim=True):
    """Uptrend above the 200-SMA, then within the last 3 bars a CLOSE
    below the prior 20-day low, then (optionally) a reclaim close."""
    base = [100 + 0.05 * i for i in range(250)]
    closes = list(base)
    # the prior 20d low sits ~0.5 under the oldest close of that window;
    # drive one of the last 3 pre-signal bars clearly below it
    level = min(c - 0.5 for c in closes[-(RS02_BREAKOUT_LOOKBACK
                                          + RECLAIM_WINDOW):-RECLAIM_WINDOW])
    closes[-3] = level + break_close_delta          # the break (a CLOSE)
    closes[-2] = level - 0.2 if break_close_delta < 0 else closes[-2]
    closes[-1] = (level + 1.5) if reclaim else (level - 0.1)
    return make_bars(closes), level


def test_h24_fires_on_break_and_reclaim():
    bars, level = h24_bars()
    hit = detect_h24(bars, FEATURES)
    assert hit is not None and hit["setup_id"] == "H-24"
    assert hit["invalidation_price"] < level        # stop under the break low


def test_h24_requires_the_reclaim_close():
    bars, _ = h24_bars(reclaim=False)
    assert detect_h24(bars, FEATURES) is None


def test_h24_requires_an_actual_break_close():
    """No bar CLOSED below the level -> no trapped sellers -> no setup,
    even though the latest close is above the level."""
    base = [100 + 0.05 * i for i in range(250)]
    assert detect_h24(make_bars(base), FEATURES) is None


def test_h24_respects_volume_and_market_context():
    bars, _ = h24_bars()
    assert detect_h24(bars, weak_volume()) is None
    assert detect_h24(bars, bench_freefall()) is None


def test_h24_fails_closed_below_200_sma():
    """Same break/reclaim shape but in a broken long-term trend — a
    falling knife, not trapped sellers (H2b, frozen)."""
    base = [200 - 0.3 * i for i in range(250)]      # downtrend
    closes = list(base)
    level = min(c - 0.5 for c in closes[-(RS02_BREAKOUT_LOOKBACK
                                          + RECLAIM_WINDOW):-RECLAIM_WINDOW])
    closes[-2] = level - 1.0
    closes[-1] = level + 1.0
    assert detect_h24(make_bars(closes), FEATURES) is None


def test_h24_fails_closed_on_short_history():
    bars, _ = h24_bars()
    assert detect_h24(bars.iloc[-150:], FEATURES) is None


# ── H-25 fixtures ────────────────────────────────────────────────────
def h25_bars(pullback=True, reclaim=True):
    """253+ bars of strong uptrend (H2b + H4b both pass), then a dip
    under the rolling 20-day SMA inside the last 5 bars, then a
    reclaim close above it."""
    closes = [10 + 0.1 * i for i in range(260)]
    if pullback:
        for i in range(3, 1, -1):                   # bars -3, -2 dip hard
            closes[-i] = closes[-i] - 3.0
    closes[-1] = closes[-4] + 1.0 if reclaim else closes[-2]
    return make_bars(closes)


def test_h25_fires_on_pullback_and_reclaim():
    hit = detect_h25(h25_bars(), FEATURES)
    assert hit is not None and hit["setup_id"] == "H-25"


def test_h25_requires_a_pullback():
    """A clean uptrend with no close under the 20-SMA is RS-02
    territory, not H-25's."""
    assert detect_h25(h25_bars(pullback=False), FEATURES) is None


def test_h25_requires_the_reclaim():
    assert detect_h25(h25_bars(reclaim=False), FEATURES) is None


def test_h25_fails_closed_without_momentum_history():
    bars = h25_bars().iloc[-200:]                   # under the H4b horizon
    assert detect_h25(bars, FEATURES) is None


def test_h25_respects_volume_and_market_context():
    bars = h25_bars()
    assert detect_h25(bars, weak_volume()) is None
    assert detect_h25(bars, bench_freefall()) is None


# ── registry and live-path guarantees ────────────────────────────────
def test_new_setups_are_registered_for_research_but_not_live():
    """The backtester can study them; the live scanner must not trade
    them before the registered verdict AND a separate operator
    activation (one live setup at a time)."""
    assert "H-24" in DETECTORS and "H-25" in DETECTORS
    assert ACTIVE_SETUPS == ("RS-02",)


def test_h24_and_h25_cannot_fire_on_the_same_bar_as_rs02():
    """Frozen registration claim: a close above the prior 20-day high
    cannot also be a reclaim of the prior 20-day low. Verify on H-24's
    own trigger fixture: the reclaim bar is nowhere near a breakout."""
    from mve.setups import detect_rs02
    bars, _ = h24_bars()
    strong = dict(FEATURES, rs_persistence=0.9, rel_volume=1.5)
    assert detect_rs02(bars, strong) is None


# ── the frozen criterion, as implemented ─────────────────────────────
class T:
    def __init__(self, r):
        self.r_multiple = r
        self.ticker, self.signal_date, self.setup = "X", "d", "H-24"


def test_judge_confirms_on_the_registered_bar():
    from mve.setup_study import judge
    windows = [(str(y), [T(0.2)] * 12) for y in range(2010, 2015)]  # n=60
    v = judge(windows)
    assert v["verdict"] == "CONFIRMED" and v["n"] == 60


def test_judge_inconclusive_below_fifty():
    from mve.setup_study import judge
    v = judge([("2010", [T(1.0)] * 49)])
    assert v["verdict"] == "INCONCLUSIVE"


def test_judge_fails_on_negative_aggregate():
    from mve.setup_study import judge
    windows = [(str(y), [T(-0.1)] * 12) for y in range(2010, 2015)]
    assert judge(windows)["verdict"] == "FAILED"


def test_judge_fails_when_one_lucky_year_carries_it():
    """Aggregate positive but only 1 of 4 judged windows positive —
    the breadth clause exists exactly for this."""
    from mve.setup_study import judge
    windows = [("2010", [T(3.0)] * 15),
               ("2011", [T(-0.1)] * 15),
               ("2012", [T(-0.1)] * 15),
               ("2013", [T(-0.1)] * 15)]
    v = judge(windows)
    assert v["expectancy_r"] > 0
    assert v["verdict"] == "FAILED"


def test_judge_inconclusive_when_no_window_is_judgeable():
    from mve.setup_study import judge
    windows = [(str(y), [T(0.5)] * 9) for y in range(2010, 2017)]  # n=63
    v = judge(windows)
    assert v["verdict"] == "INCONCLUSIVE"
    assert "unjudgeable" in v["reason"]


def test_overlap_counts_shared_ticker_signal_dates():
    from mve.setup_study import overlap_with

    def trade(ticker, sig):
        t = T(0.1)
        t.ticker, t.signal_date = ticker, sig
        return t

    base = [("2010", [trade("NVDA", "d1"), trade("KO", "d2")])]
    mine = [("2010", [trade("NVDA", "d1"), trade("F", "d3")])]
    ov = overlap_with(base, mine)
    assert ov == {"trades": 2, "overlapping": 1, "share": 0.5}


def test_break_even_estimate_sane():
    from mve.setup_study import linear_break_even
    assert linear_break_even(0.10, 0.08, 10.0) == pytest.approx(50.0)
    assert linear_break_even(None, 0.08, 10.0) is None
    assert linear_break_even(0.10, 0.12, 10.0) is None   # costs helped?? no
