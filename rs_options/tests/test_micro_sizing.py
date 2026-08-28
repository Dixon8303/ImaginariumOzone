"""Micro-account override — fails closed, tags trades, never touches options."""
import pytest

from paper.micro_sizing import (ENV_VAR, MICRO_EQUITY_THRESHOLD,
                                count_open_micro_positions,
                                micro_mode_banner, micro_override_active,
                                micro_override_armed, micro_position_size,
                                micro_trade_warning)


# ------------------------------------------------------- fails closed
def test_unset_env_var_means_off(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert not micro_override_armed()
    assert not micro_override_active(29.0)


def test_only_the_literal_string_yes_arms_it(monkeypatch):
    for bad in ("yes", "true", "1", "YES ", " YES", "Yes"):
        monkeypatch.setenv(ENV_VAR, bad)
        assert not micro_override_armed(), f"{bad!r} should not arm it"
    monkeypatch.setenv(ENV_VAR, "YES")
    assert micro_override_armed()


def test_armed_but_equity_above_threshold_is_inactive(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "YES")
    assert not micro_override_active(MICRO_EQUITY_THRESHOLD)
    assert not micro_override_active(MICRO_EQUITY_THRESHOLD + 0.01)
    assert micro_override_active(MICRO_EQUITY_THRESHOLD - 0.01)


def test_growing_past_threshold_disables_without_a_separate_switch(monkeypatch):
    """No second flag to remember to flip off — crossing the equity line
    alone turns it off, even with the env var still set."""
    monkeypatch.setenv(ENV_VAR, "YES")
    assert micro_override_active(29.0)
    assert not micro_override_active(5000.0)


# ------------------------------------------------------------- sizing
def test_sizes_exactly_one_share_when_affordable():
    assert micro_position_size(29.0, 25.0) == 1
    assert micro_position_size(29.0, 29.0) == 1        # exact equity


def test_returns_zero_rather_than_a_fraction():
    assert micro_position_size(29.0, 29.01) == 0
    assert micro_position_size(29.0, 1000.0) == 0
    assert micro_position_size(0.0, 10.0) == 0
    assert micro_position_size(29.0, 0.0) == 0
    assert micro_position_size(29.0, -5.0) == 0


def test_never_returns_more_than_one_share():
    # even a cheap stock and a large equity cap at 1 share — this mode
    # is "afford one share", not "afford as many as possible"
    assert micro_position_size(10_000.0, 5.0) == 1


# ---------------------------------------------------- ledger bookkeeping
def test_counts_only_tagged_open_positions():
    ledger = {"open": {
        "AAA": {"micro_override": True},
        "BBB": {"micro_override": False},
        "CCC": {},                       # doctrine trades predate the flag
    }}
    assert count_open_micro_positions(ledger) == 1


def test_counts_zero_on_an_empty_ledger():
    assert count_open_micro_positions({"open": {}}) == 0
    assert count_open_micro_positions({}) == 0


# --------------------------------------------------------------- report
def test_trade_warning_names_the_equity_fraction():
    lines = micro_trade_warning("AAL", 29.0, 15.0)
    text = "\n".join(lines)
    assert "AAL" in text and "MICRO OVERRIDE" in text
    assert "52%" in text                 # 15/29 rounded


def test_banner_states_threshold_and_module():
    text = micro_mode_banner(29.0)
    assert "MICRO OVERRIDE ACTIVE" in text
    assert str(int(MICRO_EQUITY_THRESHOLD)) in text
    assert "micro_sizing.py" in text


# ── fixed-capital fractional sizing (docs/FIXED_CAPITAL_PHILOSOPHY.md,
#    integrated 2026-08-27) ────────────────────────────────────────────
from paper.micro_sizing import (MICRO_COOLOFF_SESSIONS,          # noqa: E402
                                MICRO_MIN_NOTIONAL,
                                MICRO_RESERVE_PCT,
                                MICRO_RISK_CEILING_PCT,
                                micro_cooloff_active,
                                micro_drawdown_paused,
                                micro_fractional_size,
                                micro_fractional_warning)


def test_fractional_size_respects_risk_ceiling():
    """$29 equity, wide stop: risk binds before notional."""
    qty = micro_fractional_size(29.0, 20.0, 16.0)   # $4 risk/share
    assert qty > 0
    assert qty * 4.0 <= 29.0 * MICRO_RISK_CEILING_PCT + 1e-9
    # far below the notional cap when risk binds
    assert qty * 20.0 < 29.0 * (1 - MICRO_RESERVE_PCT)


def test_fractional_size_respects_reserve_floor():
    """Tight stop: notional cap binds, reserve stays in cash."""
    qty = micro_fractional_size(29.0, 20.0, 19.8)   # $0.20 risk/share
    assert qty > 0
    assert qty * 20.0 <= 29.0 * (1 - MICRO_RESERVE_PCT) + 1e-9


def test_fractional_size_zero_below_broker_minimum():
    assert micro_fractional_size(2.0, 100.0, 60.0) == 0.0
    assert MICRO_MIN_NOTIONAL == 1.00


def test_fractional_size_fails_closed_on_degenerate_inputs():
    assert micro_fractional_size(29.0, 20.0, 20.0) == 0.0    # stop == close
    assert micro_fractional_size(29.0, 20.0, 21.0) == 0.0    # stop above
    assert micro_fractional_size(29.0, 0.0, -1.0) == 0.0
    assert micro_fractional_size(0.0, 20.0, 19.0) == 0.0


def test_fractional_size_floors_never_rounds_up():
    qty = micro_fractional_size(29.0, 20.0, 16.0)
    assert qty == int(qty * 1000) / 1000.0


def test_drawdown_pause_triggers_at_ten_percent():
    flat = [{"date": f"2026-08-2{i}", "equity": 30.0} for i in range(5)]
    assert micro_drawdown_paused(flat) is False
    dd = flat + [{"date": "2026-08-25", "equity": 26.9}]     # -10.3%
    assert micro_drawdown_paused(dd) is True
    small = flat + [{"date": "2026-08-25", "equity": 27.5}]  # -8.3%
    assert micro_drawdown_paused(small) is False
    assert micro_drawdown_paused([]) is False                # no history


def test_cooloff_needs_two_recent_consecutive_losses():
    def closed(r, exit_date, micro=True):
        return dict(ticker="X", exit_date=exit_date, r=r,
                    micro_override=micro)

    two_losses = {"closed": [closed(-1.0, "2026-08-24"),
                             closed(-0.8, "2026-08-25")]}
    assert micro_cooloff_active(two_losses, "2026-08-26") is True
    # a win between resets the count
    mixed = {"closed": [closed(-1.0, "2026-08-24"),
                        closed(+1.5, "2026-08-25")]}
    assert micro_cooloff_active(mixed, "2026-08-26") is False
    # losses long past the cool-off window do not gate
    stale = {"closed": [closed(-1.0, "2026-07-01"),
                        closed(-0.8, "2026-07-02")]}
    assert micro_cooloff_active(stale, "2026-08-26") is False
    # non-micro losses are the validated track's business, not ours
    doctrine = {"closed": [closed(-1.0, "2026-08-24", micro=False),
                           closed(-0.8, "2026-08-25", micro=False)]}
    assert micro_cooloff_active(doctrine, "2026-08-26") is False
    assert MICRO_COOLOFF_SESSIONS == 5


def test_fractional_warning_reports_commitment_and_gap_risk():
    lines = micro_fractional_warning("NVDA", 29.0, 0.8, 20.0, 18.5)
    text = "\n".join(lines)
    assert "NVDA" in text and "0.8 sh" in text
    assert "reserve kept" in text
    assert "planned loss $1.20" in text
    assert "overnight gap" in text        # the honest caveat travels
