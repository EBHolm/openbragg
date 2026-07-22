"""Behavioral tests for the openkbp-opt loader against the synthetic fixture."""

import numpy as np
from conftest import SyntheticCase

from openbragg.io.openkbp_opt import load_case, load_dij, load_weights


def test_load_case_populates_model(synthetic_case: SyntheticCase) -> None:
    sc = synthetic_case
    case = load_case(
        sc.patient_dir, sc.fluence_path, sc.dose_path, grid_shape=sc.grid_shape
    )
    assert case.identifier == "pt_test"
    assert case.image.shape == sc.grid_shape
    assert case.image.spacing_mm == sc.spacing_mm
    assert set(case.structures.masks) == {"PTV70", "SpinalCord"}
    np.testing.assert_array_equal(case.structures.masks["PTV70"], sc.masks["PTV70"])
    np.testing.assert_allclose(case.plan.weights, sc.weights)
    assert case.reference_dose is not None
    np.testing.assert_allclose(case.reference_dose.array, sc.dose)


def test_load_case_without_dose_has_none(synthetic_case: SyntheticCase) -> None:
    sc = synthetic_case
    case = load_case(sc.patient_dir, sc.fluence_path, grid_shape=sc.grid_shape)
    assert case.reference_dose is None


def test_load_dij_shape_and_weights(synthetic_case: SyntheticCase) -> None:
    sc = synthetic_case
    dij = load_dij(sc.patient_dir, grid_shape=sc.grid_shape)
    assert dij.shape == (int(np.prod(sc.grid_shape)), sc.weights.shape[0])
    w = load_weights(sc.fluence_path)
    np.testing.assert_allclose(w, sc.weights)


def test_load_dij_rejects_wrong_grid(synthetic_case: SyntheticCase) -> None:
    sc = synthetic_case
    try:
        load_dij(sc.patient_dir, grid_shape=(7, 7, 7))
    except ValueError:
        return
    raise AssertionError("expected ValueError for mismatched grid")
