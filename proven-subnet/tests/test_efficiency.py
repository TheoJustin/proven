import pytest
from verification.efficiency import efficiency


def test_within_budget_returns_1():
    assert efficiency(1.0, 5.0, 10.0) == 1.0


def test_at_soft_budget_boundary_returns_1():
    assert efficiency(5.0, 5.0, 10.0) == 1.0


def test_at_hard_timeout_returns_floor():
    assert efficiency(10.0, 5.0, 10.0) == 0.1


def test_beyond_timeout_returns_floor():
    assert efficiency(15.0, 5.0, 10.0) == 0.1


def test_midpoint_linear_decay():
    # frac = (7.5 - 5.0) / (10.0 - 5.0) = 0.5; base = 1.0 - 0.5 * 0.9 = 0.55
    assert efficiency(7.5, 5.0, 10.0) == pytest.approx(0.55)


def test_probing_within_budget_applies_penalty():
    # within budget base=1.0, probing_penalty=0.1 → 1.0 * 0.1 = 0.1
    assert efficiency(1.0, 5.0, 10.0, probing=True) == pytest.approx(0.1)


def test_custom_floor_at_hard_timeout():
    assert efficiency(10.0, 5.0, 10.0, floor=0.2) == pytest.approx(0.2)


def test_degenerate_band_within_budget_returns_1():
    # hard_timeout == soft_budget: within budget → 1.0
    assert efficiency(3.0, 5.0, 5.0) == 1.0


def test_degenerate_band_beyond_returns_floor():
    # hard_timeout == soft_budget: at/beyond → floor, no ZeroDivisionError
    assert efficiency(6.0, 5.0, 5.0) == pytest.approx(0.1)


def test_result_always_in_unit_interval():
    for t in [0.0, 1.0, 5.0, 7.5, 10.0, 15.0, 100.0]:
        result = efficiency(t, 5.0, 10.0)
        assert 0.0 <= result <= 1.0, f"efficiency({t}) = {result} out of [0,1]"
