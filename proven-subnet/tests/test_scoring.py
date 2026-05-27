import pytest
from verification.scoring import compute_score


def test_basic_formula():
    assert compute_score(1, 5, 10, 1.0) == pytest.approx(0.5)


def test_p_clean_gate_zero():
    assert compute_score(0, 5, 10, 1.0) == 0.0


def test_bool_p_clean_true():
    assert compute_score(True, 4, 8, 1.0) == pytest.approx(0.5)


def test_no_kills():
    assert compute_score(1, 0, 10, 1.0) == pytest.approx(0.0)


def test_all_killed_full_efficiency():
    assert compute_score(1, 10, 10, 1.0) == pytest.approx(1.0)


def test_efficiency_halves_score():
    assert compute_score(1, 10, 10, 0.5) == pytest.approx(0.5)


def test_n_mut_zero_no_division_error():
    assert compute_score(1, 5, 0, 1.0) == 0.0


def test_alpha_multiplicative():
    assert compute_score(1, 10, 10, 1.0, alpha=2.0) == pytest.approx(2.0)
