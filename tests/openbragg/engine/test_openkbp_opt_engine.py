"""Behavioral tests for the dose-engine seam and the openkbp-opt loader engine."""

from dataclasses import replace
from typing import Callable

import numpy as np
import pytest
from conftest import SyntheticCase

from openbragg.engine.base import DijResult, DoseEngine
from openbragg.engine.openkbp_opt import OpenKBPOptEngine
from openbragg.io.openkbp_opt import load_case
from openbragg.model.case import Plan


def test_engine_sources_dij_matching_case(synthetic_case: SyntheticCase) -> None:
    sc = synthetic_case
    case = load_case(
        sc.patient_dir, sc.fluence_path, sc.dose_path, grid_shape=sc.grid_shape
    )
    engine: DoseEngine = OpenKBPOptEngine(sc.patient_dir, grid_shape=sc.grid_shape)
    result = engine.compute_dij(case)
    assert isinstance(result, DijResult)
    assert result.grid_shape == sc.grid_shape
    assert result.units == "Gy"
    assert result.dij.shape == (int(np.prod(sc.grid_shape)), sc.weights.shape[0])


def test_dij_result_rejects_row_mismatch(synthetic_case: SyntheticCase) -> None:
    sc = synthetic_case
    dij = sc.dij
    with pytest.raises(ValueError):
        DijResult(dij=dij, grid_shape=(7, 7, 7))


def test_engine_rejects_weight_count_mismatch(
    make_synthetic_case: Callable[..., SyntheticCase],
) -> None:
    sc = make_synthetic_case(grid_shape=(4, 4, 4), n_beamlets=3)
    # Build a case whose plan has the wrong number of weights.
    case = load_case(
        sc.patient_dir, sc.fluence_path, sc.dose_path, grid_shape=sc.grid_shape
    )
    bad = OpenKBPOptEngine(sc.patient_dir, grid_shape=sc.grid_shape)
    mangled = replace(case, plan=Plan(np.array([1.0, 2.0])))  # 2 != 3 beamlets
    with pytest.raises(ValueError):
        bad.compute_dij(mangled)
