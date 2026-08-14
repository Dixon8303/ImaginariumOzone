"""RS features, setup detectors, chain selection (spec §13-§19, §27)."""
from datetime import date

import pandas as pd
import pytest

from mve.chain_select import DELTA_RANGE, select_call
from mve.rs_features import compute_features, rs_persistence, window_return
from mve.setups import detect_all, detect_rs01, detect_rs02
from mve.vendors import SyntheticVendor


def bars_from_closes(closes, ticker="TCKR", volume=1_000_000, last_volume=None):
    n = len(closes)
    dates = pd.bdate_range("2026-03-02", periods=n).date.astype(str)
    vols = [volume] * n
    if last_volume is not None:
        vols[-1] = last_volume
    return pd.DataFrame({
        "ticker": ticker, "trade_date": dates,
        "open": closes, "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes], "close": closes, "volume": vols,
    })


# ------------------------------------------------------------- features
def test_window_return_and_persistence():
    up = bars_from_closes([100 + i for i in range(40)])
    flat = bars_from_closes([100.0] * 40)
    assert window_return(up["close"]) > 0
    assert rs_persistence(up["close"], flat["close"]) == 1.0
    assert rs_persistence(flat["close"], up["close"]) == 0.0


def test_compute_features_shape():
    stock = bars_from_closes([100 * 1.004 ** i for i in range(80)])
    bench = bars_from_closes([500 * 1.001 ** i for i in range(80)])
    f = compute_features(stock, bench)
    assert f["rs_market"] > 0
    assert f["rs_beta_adjusted"] == pytest.approx(
        f["stock_return"] - f["beta"] * f["bench_return"])
    assert f["rs_sector"] is None


# -------------------------------------------------------------- RS-01
def test_rs01_fires_on_weak_market_strong_stock():
    stock = bars_from_closes([100 * 1.002 ** i for i in range(40)])
    bench = bars_from_closes([500.0] * 29 + [500 * (1 - 0.002 * i) for i in range(1, 12)])
    f = compute_features(stock, bench)
    hit = detect_rs01(stock, f)
    assert hit is not None and hit["setup_id"] == "RS-01"
    assert hit["invalidation_price"] < hit["close"]


def test_rs01_silent_when_market_strong():
    stock = bars_from_closes([100 * 1.002 ** i for i in range(40)])
    bench = bars_from_closes([500 * 1.002 ** i for i in range(40)])
    assert detect_rs01(stock, compute_features(stock, bench)) is None


# -------------------------------------------------------------- RS-02
def test_rs02_fires_on_breakout_with_volume():
    closes = [100.0 + 0.3 * i for i in range(39)] + [100.0 + 0.3 * 38 + 5.0]
    stock = bars_from_closes(closes, last_volume=2_000_000)
    bench = bars_from_closes([500.0 + 0.05 * i for i in range(40)])
    f = compute_features(stock, bench)
    hit = detect_rs02(stock, f)
    assert hit is not None and hit["setup_id"] == "RS-02"
    assert 0 <= hit["opportunity_score"] <= 10


def test_rs02_silent_without_volume_expansion():
    closes = [100.0 + 0.3 * i for i in range(39)] + [100.0 + 0.3 * 38 + 5.0]
    stock = bars_from_closes(closes)                     # flat volume
    bench = bars_from_closes([500.0 + 0.05 * i for i in range(40)])
    assert detect_rs02(stock, compute_features(stock, bench)) is None


def test_detect_all_returns_list():
    stock = bars_from_closes([100.0] * 40)
    bench = bars_from_closes([500.0] * 40)
    assert detect_all(stock, compute_features(stock, bench)) == []


# ------------------------------------------------------ chain selection
def test_select_call_within_research_band():
    chain = SyntheticVendor(start=date(2026, 3, 2)).chain(
        "TCKR", "2026-08-12", spot=100.0)
    q = select_call(chain, "2026-08-12")
    assert q is not None
    assert DELTA_RANGE[0] <= _chain_delta(chain, q) <= DELTA_RANGE[1]
    assert 7 <= q.dte_days <= 45
    assert q.spread_pct <= 0.10


def test_select_call_none_on_empty_or_illiquid():
    assert select_call(pd.DataFrame(), "2026-08-12") is None
    chain = SyntheticVendor(start=date(2026, 3, 2)).chain(
        "TCKR", "2026-08-12", spot=100.0)
    chain["open_interest"] = 0
    assert select_call(chain, "2026-08-12") is None


def _chain_delta(chain, q):
    row = chain[(chain["strike"] == q.strike) & (chain["right"] == "call")
                & (chain["iv"].round(4) == round(q.iv, 4))].iloc[0]
    return float(row["delta"])
