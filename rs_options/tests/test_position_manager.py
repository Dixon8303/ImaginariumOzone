"""Exit-rule tests — the regression net for the -$918 of expirations."""
from datetime import date

from mve.backtest import MAX_HOLD_BARS, TARGET_R
from mve.position_manager import (ExitAction, MIN_DTE_HOLD, OpenPosition,
                                  entry_dte_is_coherent, evaluate_exit,
                                  format_exit_report, trading_days_between)


def _position(expiry: str, invalidation: float = 100.0,
              entry_date: str | None = None,
              entry_underlying: float | None = None) -> OpenPosition:
    return OpenPosition(ticker="NVDA", contract=f"NVDA {expiry} 220C",
                        quantity=1, entry_price=5.0,
                        expiry=date.fromisoformat(expiry),
                        invalidation_price=invalidation,
                        entry_date=date.fromisoformat(entry_date)
                        if entry_date else None,
                        entry_underlying=entry_underlying)


def test_healthy_position_holds():
    v = evaluate_exit(_position("2026-09-18"), 120.0, date(2026, 8, 14))
    assert v.action is ExitAction.HOLD
    assert not v.must_exit
    assert v.dte == 35


def test_dte_floor_forces_exit():
    """The rule the 8 expired positions violated."""
    v = evaluate_exit(_position("2026-08-19"), 120.0, date(2026, 8, 14))
    assert v.must_exit
    assert any("DTE_FLOOR" in r for r in v.reasons)


def test_expiration_day_forces_exit():
    v = evaluate_exit(_position("2026-08-14"), 120.0, date(2026, 8, 14))
    assert v.must_exit and v.dte == 0


def test_past_expiry_still_exits():
    """A stale record must never read as HOLD."""
    v = evaluate_exit(_position("2026-08-10"), 120.0, date(2026, 8, 14))
    assert v.must_exit and v.dte < 0


def test_invalidation_breach_forces_exit():
    v = evaluate_exit(_position("2026-09-18", invalidation=100.0), 99.5,
                      date(2026, 8, 14))
    assert v.must_exit
    assert any("INVALIDATION" in r for r in v.reasons)


def test_invalidation_is_inclusive_at_the_level():
    v = evaluate_exit(_position("2026-09-18", invalidation=100.0), 100.0,
                      date(2026, 8, 14))
    assert v.must_exit


def test_both_triggers_are_reported():
    v = evaluate_exit(_position("2026-08-17", invalidation=100.0), 95.0,
                      date(2026, 8, 14))
    assert v.must_exit and len(v.reasons) == 2


def test_advisory_does_not_force_exit():
    """Advisory text must not be mistaken for an exit trigger."""
    v = evaluate_exit(_position("2026-08-22"), 120.0, date(2026, 8, 14))
    assert v.action is ExitAction.HOLD
    assert v.reasons and "ADVISORY" in v.reasons[0]


def test_entry_dte_coherence_against_chain_selector():
    """chain_select's floor must leave room above the exit floor."""
    from mve.chain_select import DTE_RANGE
    assert not entry_dte_is_coherent(MIN_DTE_HOLD + 1)
    assert entry_dte_is_coherent(MIN_DTE_HOLD + 2)
    # Documents the live coupling: the 21-DTE floor adopted with the wide
    # exit leaves ample room above the 5-day exit floor.
    assert entry_dte_is_coherent(DTE_RANGE[0])


def test_report_renders_empty_and_populated():
    assert format_exit_report([]) == "No open positions."
    p = _position("2026-08-19")
    text = format_exit_report([(p, evaluate_exit(p, 120.0, date(2026, 8, 14)))])
    assert "EXIT" in text and "DTE_FLOOR" in text


# ── doctrine rules added 2026-08-16 (playbook rules 3 and 4) ─────────
def test_target_forces_exit_at_plus_3r():
    """+3R on the underlying: entry 110, invalidation 100 -> 1R = 10."""
    p = _position("2026-09-18", invalidation=100.0, entry_underlying=110.0)
    assert p.target_price == 140.0
    assert evaluate_exit(p, 139.9, date(2026, 8, 14)).action is ExitAction.HOLD
    v = evaluate_exit(p, 140.0, date(2026, 8, 14))
    assert v.must_exit and any("TARGET" in r for r in v.reasons)


def test_target_uses_doctrine_constant():
    p = _position("2026-09-18", invalidation=100.0, entry_underlying=110.0)
    assert p.target_price == 110.0 + TARGET_R * 10.0


def test_time_exit_at_max_hold_bars():
    p = _position("2026-10-16", invalidation=100.0, entry_date="2026-07-20")
    held = trading_days_between(date(2026, 7, 20), date(2026, 8, 14))
    assert held >= MAX_HOLD_BARS
    v = evaluate_exit(p, 120.0, date(2026, 8, 14))
    assert v.must_exit and any("TIME_EXIT" in r for r in v.reasons)


def test_time_exit_holds_before_the_horizon():
    p = _position("2026-10-16", invalidation=100.0, entry_date="2026-08-10")
    v = evaluate_exit(p, 120.0, date(2026, 8, 14))
    assert v.action is ExitAction.HOLD


def test_missing_data_is_reported_not_skipped():
    """A rule that cannot run must say so — silence would read as a pass."""
    v = evaluate_exit(_position("2026-09-18"), 120.0, date(2026, 8, 14))
    assert v.action is ExitAction.HOLD
    assert any("TARGET" in g for g in v.not_evaluated)
    assert any("TIME_EXIT" in g for g in v.not_evaluated)
    text = format_exit_report([(_position("2026-09-18"), v)])
    assert "NOT CHECKED" in text


def test_trading_days_ignores_weekends():
    assert trading_days_between(date(2026, 8, 3), date(2026, 8, 14)) == 9
    assert trading_days_between(date(2026, 8, 14), date(2026, 8, 3)) == 0


# ---------------------------------- FWD-1 plumbing (docs/PREREGISTERED.md)

def test_open_position_carries_score_without_acting_on_it():
    """The §32 score FAILED its holdout test and is not doctrine. It is
    recorded so forward paper results accumulate the score->outcome
    pairing — the only clean test left. Nothing may read it to decide."""
    from datetime import date as _d
    from mve.position_manager import OpenPosition
    p = OpenPosition(ticker="T", contract="T260101C00100000", quantity=1,
                     entry_price=2.0, expiry=_d(2026, 1, 1),
                     invalidation_price=95.0, score=8)
    assert p.score == 8
    # optional, like the other late-added fields — older records load
    bare = OpenPosition(ticker="T", contract="C", quantity=1,
                        entry_price=2.0, expiry=_d(2026, 1, 1),
                        invalidation_price=95.0)
    assert bare.score is None


def test_score_never_reaches_the_exit_decision():
    """Guard against the score quietly becoming doctrine: no exit rule
    may consult it while FWD-1 is OPEN."""
    import inspect
    from mve import position_manager
    src = inspect.getsource(position_manager.evaluate_exit)
    assert ".score" not in src
