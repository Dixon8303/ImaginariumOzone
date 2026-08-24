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
