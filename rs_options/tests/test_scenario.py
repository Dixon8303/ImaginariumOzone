"""Scenario grid & Black-Scholes tests. Spec §6."""
import math

from rs_options_risk import Right, bs_delta, bs_price, scenario_grid, worst_case
from rs_options_risk.config import ScenarioConfig

from tests.test_engine import make_candidate


def test_bs_price_atm_call_positive():
    price = bs_price(Right.CALL, s=100.0, k=100.0, t_years=14 / 365, sigma=0.35)
    assert 0.0 < price < 10.0


def test_bs_put_call_parity():
    s, k, t, sigma, r = 100.0, 100.0, 30 / 365, 0.30, 0.04
    call = bs_price(Right.CALL, s, k, t, sigma, r)
    put = bs_price(Right.PUT, s, k, t, sigma, r)
    parity = call - put - (s - k * math.exp(-r * t))
    assert abs(parity) < 1e-9


def test_bs_price_expiry_returns_intrinsic():
    assert bs_price(Right.CALL, 105.0, 100.0, 0.0, 0.35) == 5.0
    assert bs_price(Right.PUT, 95.0, 100.0, 0.0, 0.35) == 5.0
    assert bs_price(Right.CALL, 95.0, 100.0, 0.0, 0.35) == 0.0


def test_bs_delta_bounds():
    assert 0.0 < bs_delta(Right.CALL, 100.0, 100.0, 14 / 365, 0.35) < 1.0
    assert -1.0 < bs_delta(Right.PUT, 100.0, 100.0, 14 / 365, 0.35) < 0.0


def test_scenario_grid_has_five_scenarios():
    scenarios = scenario_grid(make_candidate(), ScenarioConfig())
    names = {s.name for s in scenarios}
    assert names == {"BASE", "STRESS_A_SLIPPAGE", "STRESS_B_IV_ADVERSE",
                     "STRESS_C_TIME_DECAY", "STRESS_D_LIQUIDITY"}


def test_all_scenarios_lose_at_invalidation_for_long_call():
    scenarios = scenario_grid(make_candidate(), ScenarioConfig())
    for s in scenarios:
        assert s.pnl_per_contract < 0, f"{s.name} should lose at invalidation"


def test_worst_case_is_minimum():
    scenarios = scenario_grid(make_candidate(), ScenarioConfig())
    worst = worst_case(scenarios)
    assert worst.pnl_per_contract == min(s.pnl_per_contract for s in scenarios)
