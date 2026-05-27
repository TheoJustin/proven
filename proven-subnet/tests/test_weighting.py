import numpy as np
import pytest
from verification.weighting import to_weights


def test_all_zeros_returns_zeros_no_nan():
    result = to_weights([0.0, 0.0, 0.0])
    assert result.sum() == pytest.approx(0.0)
    assert not np.isnan(result).any()


def test_single_nonzero_winner():
    result = to_weights([0.0, 5.0, 0.0])
    assert result == pytest.approx([0.0, 1.0, 0.0])


def test_multi_score_sums_to_one_and_is_monotonic():
    result = to_weights([1.0, 2.0, 3.0, 4.0])
    assert result.sum() == pytest.approx(1.0)
    # higher score → higher weight
    assert result[0] < result[1] < result[2] < result[3]


def test_top_weight_exceeds_proportional_share():
    # proportional share of score=4 in [1,2,3,4] is 4/10 = 0.4
    # p=4 should give ~0.72, well above proportional
    result = to_weights([1.0, 2.0, 3.0, 4.0])
    assert result[-1] > 0.4


def test_higher_p_concentrates_more():
    scores = [1.0, 2.0, 3.0, 4.0]
    top_p4 = to_weights(scores, p=4.0)[-1]
    top_p8 = to_weights(scores, p=8.0)[-1]
    assert top_p8 > top_p4


def test_negative_scores_clamped_to_zero():
    result = to_weights([-1.0, 2.0])
    assert result == pytest.approx([0.0, 1.0])


def test_sum_to_one_for_mixed_input():
    result = to_weights([-5.0, 0.0, 3.0, 1.5])
    assert result.sum() == pytest.approx(1.0)
