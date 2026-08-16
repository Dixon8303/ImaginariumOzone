"""VIX term-structure regime layer (H8) + the total-R adoption guard."""
import pandas as pd
import pytest

from mve.hypotheses import summary, total_r
from mve.vix_regime import (BACKWARDATION_AT, calm_regime, load_term_structure,
                            ratio_on, regime_label, save_term_structure,
                            summary as vix_summary)

VIX = pd.DataFrame({
    "trade_date": ["2026-08-10", "2026-08-11", "2026-08-12"],
    "vix":   [14.0, 20.0, 18.0],
    "vix3m": [20.0, 18.0, 20.0],
    "ratio": [0.70, 1.111, 0.90],
})


# ── regime reading ───────────────────────────────────────────────────
def test_regime_labels():
    assert regime_label(1.05) == "BACKWARDATION"
    assert regime_label(0.85) == "DEEP_CONTANGO"
    assert regime_label(0.95) == "CONTANGO"
    assert regime_label(None) == "UNKNOWN"


def test_ratio_on_is_point_in_time():
    assert ratio_on(VIX, "2026-08-11") == pytest.approx(1.111)
    # a date between readings uses the most recent PRIOR one, never a future
    assert ratio_on(VIX, "2026-08-11T23:59") == pytest.approx(1.111)
    assert ratio_on(VIX, "2026-08-09") is None       # nothing yet
    assert ratio_on(pd.DataFrame(), "2026-08-11") is None


def test_calm_regime_blocks_backwardation():
    assert calm_regime(VIX, "2026-08-10")            # ratio 0.70
    assert not calm_regime(VIX, "2026-08-11")        # ratio 1.111
    assert calm_regime(VIX, "2026-08-12")            # ratio 0.90
    assert not calm_regime(VIX, "2026-08-12", 0.85)  # stricter threshold


def test_calm_regime_fails_closed_on_unknown():
    """Missing data must block, never read as calm."""
    assert not calm_regime(VIX, "2026-01-01")
    assert not calm_regime(pd.DataFrame(), "2026-08-12")


def test_save_and_load_roundtrip(tmp_path):
    path = str(tmp_path / "vix.csv")
    save_term_structure(VIX, path)
    back = load_term_structure(path)
    assert list(back["trade_date"]) == list(VIX["trade_date"])
    assert load_term_structure(str(tmp_path / "missing.csv")).empty


def test_vix_summary_reports_state():
    text = vix_summary(VIX)
    assert "DEEP_CONTANGO" in text and "0.900" in text
    assert "backwardation on" in text or "LAW 12/20" in text
    assert "No VIX data" in vix_summary(pd.DataFrame())


# ── the H5 lesson, made automatic ────────────────────────────────────
def _stats(trades, exp, wr=0.6):
    return {"trades": trades, "expectancy_r": exp, "win_rate": wr}


def test_total_r_math():
    assert total_r(_stats(61, 0.348)) == pytest.approx(21.228)
    assert total_r(None) == 0.0


def test_caution_fires_on_the_actual_h5_numbers():
    """Replay of round 3: expectancy rose, total return fell. The report
    must say so — that is the guard H5 earned."""
    results = {
        "CONTROL": {"train": _stats(136, 0.281), "test": _stats(76, 0.252),
                    "filtered": 0},
        "BASELINE_DOCTRINE": {"train": _stats(61, 0.348),
                              "test": _stats(47, 0.280), "filtered": 193},
        "H5a_replay": {"train": _stats(58, 0.359), "test": _stats(44, 0.288),
                       "filtered": 204},
    }
    text = summary(results)
    assert "ADOPT-CANDIDATE" in text
    assert "CAUTION" in text
    assert "the average rose while the total fell" in text
    assert "6 trades differ" in text        # 3 per window — too few


def test_no_caution_when_a_filter_genuinely_helps():
    """A filter that raises expectancy AND keeps total return gets a
    clean ADOPT-CANDIDATE with no caution."""
    results = {
        "BASELINE_DOCTRINE": {"train": _stats(100, 0.30),
                              "test": _stats(60, 0.25), "filtered": 0},
        "GOOD": {"train": _stats(90, 0.50), "test": _stats(55, 0.45),
                 "filtered": 15},
    }
    text = summary(results)
    assert "ADOPT-CANDIDATE" in text
    # the per-variant caution lines are indented; the footer mentions the
    # word too, so match the line form rather than the bare word
    assert "CAUTION:" not in text
