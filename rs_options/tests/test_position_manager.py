"""Exit-rule tests — the regression net for the -$918 of expirations."""
from datetime import date

from mve.position_manager import (ExitAction, MIN_DTE_HOLD, OpenPosition,
                                  entry_dte_is_coherent, evaluate_exit,
                                  format_exit_report)


def _position(expiry: str, invalidation: float = 100.0) -> OpenPosition:
    return OpenPosition(ticker="NVDA", contract=f"NVDA {expiry} 220C",
                        quantity=1, entry_price=5.0,
                        expiry=date.fromisoformat(expiry),
                        invalidation_price=invalidation)


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
    # Documents the live coupling: today's 7-DTE floor leaves exactly 2 days.
    assert entry_dte_is_coherent(DTE_RANGE[0])


def test_report_renders_empty_and_populated():
    assert format_exit_report([]) == "No open positions."
    p = _position("2026-08-19")
    text = format_exit_report([(p, evaluate_exit(p, 120.0, date(2026, 8, 14)))])
    assert "EXIT" in text and "DTE_FLOOR" in text
