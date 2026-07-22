"""Behavioral tests for total-dose accumulation."""

import numpy as np
import pytest
from conftest import SyntheticCase

from openbragg.dose.accumulate import total_dose
from openbragg.engine.base import DijResult


def test_total_dose_matches_known_answer(synthetic_case: SyntheticCase) -> None:
    sc = synthetic_case
    result = DijResult(dij=sc.dij, grid_shape=sc.grid_shape)
    dose = total_dose(result, sc.weights)
    assert dose.shape == sc.grid_shape
    np.testing.assert_allclose(dose, sc.dose, rtol=1e-12, atol=1e-12)


def test_total_dose_is_linear_in_weights(synthetic_case: SyntheticCase) -> None:
    sc = synthetic_case
    result = DijResult(dij=sc.dij, grid_shape=sc.grid_shape)
    d1 = total_dose(result, sc.weights)
    d2 = total_dose(result, 2.0 * sc.weights)
    np.testing.assert_allclose(d2, 2.0 * d1, rtol=1e-12, atol=1e-12)


def test_total_dose_rejects_weight_mismatch(synthetic_case: SyntheticCase) -> None:
    sc = synthetic_case
    result = DijResult(dij=sc.dij, grid_shape=sc.grid_shape)
    with pytest.raises(ValueError):
        total_dose(result, np.ones(sc.weights.shape[0] + 1))
