"""Vol-surface skew tests. Spec §25."""
import pytest

from rs_options_risk import (SkewState, StrikeIV, classify_skew,
                             rr25_percentile, skew_metrics)


def normal_chain():
    return [
        StrikeIV(delta=0.10, iv=0.32), StrikeIV(delta=0.25, iv=0.30),
        StrikeIV(delta=0.50, iv=0.28),
        StrikeIV(delta=-0.50, iv=0.29), StrikeIV(delta=-0.25, iv=0.33),
        StrikeIV(delta=-0.10, iv=0.38),
    ]


def test_skew_metrics_normal_put_skew_negative_rr25():
    m = skew_metrics(normal_chain())
    assert m.rr25 == pytest.approx(0.30 - 0.33)
    assert m.atm_iv == pytest.approx((0.28 + 0.29) / 2)


def test_skew_metrics_requires_both_wings():
    with pytest.raises(ValueError):
        skew_metrics([StrikeIV(delta=0.25, iv=0.30)])


def test_rr25_percentile_empty_history_returns_50():
    assert rr25_percentile(-0.03, []) == 50.0


def test_classify_extreme_put_skew():
    history = [-0.01 + 0.001 * i for i in range(100)]
    assert classify_skew(-0.05, history) is SkewState.EXTREME_PUT_SKEW


def test_classify_call_skew():
    history = [-0.03 + 0.0005 * i for i in range(100)]
    assert classify_skew(0.05, history) is SkewState.CALL_SKEW


def test_classify_normal_put_skew_mid_history():
    history = [-0.05 + 0.001 * i for i in range(100)]
    assert classify_skew(-0.025, history) is SkewState.NORMAL_PUT_SKEW
