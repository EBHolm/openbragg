"""Shared test fixtures: synthetic openkbp-opt-format cases.

The layout and CSV/.npz forms match the real ababier/open-kbp-opt dataset
(verified against provided_code), so loader/engine tests run against the true
format while committing no binary data — everything is written into tmp_path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import numpy.typing as npt
import pandas as pd
import pytest
from scipy import sparse

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingTypeStubs=false


@dataclass(frozen=True)
class SyntheticCase:
    patient_dir: Path
    fluence_path: Path
    dose_path: Path
    grid_shape: tuple[int, int, int]
    weights: npt.NDArray[np.float64]
    dij: sparse.csr_matrix
    dose: npt.NDArray[np.float64]
    ct: npt.NDArray[np.float64]
    masks: dict[str, npt.NDArray[np.bool_]]
    spacing_mm: tuple[float, float, float]


def _write_sparse_vector(path: Path, dense: npt.NDArray[np.float64]) -> None:
    """Write a dense array as an openkbp-opt sparse vector CSV: index=raveled
    voxel index, column 'data'=value (nonzero entries only)."""
    flat = dense.reshape(-1)
    idx = np.nonzero(flat)[0]
    pd.DataFrame({"data": flat[idx]}, index=idx).to_csv(path)


def _write_mask(path: Path, mask: npt.NDArray[np.bool_]) -> None:
    """Write a boolean mask as an openkbp-opt index-only CSV: raveled indices in
    the index column, an all-NaN 'data' column (matches load_file's mask branch)."""
    idx = np.nonzero(mask.reshape(-1))[0]
    pd.DataFrame({"data": [np.nan] * len(idx)}, index=idx).to_csv(path)


def write_synthetic_openkbp_opt_case(
    root: Path,
    *,
    grid_shape: tuple[int, int, int] = (4, 4, 4),
    n_beamlets: int = 3,
    seed: int = 0,
) -> SyntheticCase:
    root = Path(root)
    rng = np.random.default_rng(seed)
    n_vox = int(np.prod(grid_shape))

    # Deterministic sparse Dij (~25% nonzero), beamlet weights, and dose = Dij·w.
    dense_dij = rng.uniform(0.0, 1.0, size=(n_vox, n_beamlets))
    dense_dij[dense_dij < 0.75] = 0.0
    dij = sparse.csr_matrix(dense_dij)
    weights = rng.uniform(0.5, 2.0, size=n_beamlets).astype(np.float64)
    dose = np.asarray(dij @ weights, dtype=np.float64).reshape(grid_shape)

    ct = np.zeros(grid_shape, dtype=np.float64)
    ct.reshape(-1)[: n_vox // 2] = 1000.0
    spacing = (3.0, 3.0, 2.5)

    ptv = np.zeros(grid_shape, dtype=bool)
    ptv.reshape(-1)[: max(1, n_vox // 8)] = True
    cord = np.zeros(grid_shape, dtype=bool)
    cord.reshape(-1)[max(1, n_vox // 8) : max(2, n_vox // 4)] = True
    masks = {"PTV70": ptv, "SpinalCord": cord}

    patient_dir = root / "reference-plans" / "pt_test"
    patient_dir.mkdir(parents=True, exist_ok=True)
    sparse.save_npz(patient_dir / "dij.npz", dij)
    _write_sparse_vector(patient_dir / "ct.csv", ct)
    _write_sparse_vector(patient_dir / "dose.csv", dose)
    _write_mask(patient_dir / "possible_dose_mask.csv", np.ones(grid_shape, dtype=bool))
    for name, m in masks.items():
        _write_mask(patient_dir / f"{name}.csv", m)
    np.savetxt(patient_dir / "voxel_dimensions.csv", np.array(spacing))

    fluence_dir = root / "paper-plans" / "MeanRel" / "plan-fluence" / "set_1"
    dose_dir = root / "paper-plans" / "MeanRel" / "plan-dose" / "set_1"
    fluence_dir.mkdir(parents=True, exist_ok=True)
    dose_dir.mkdir(parents=True, exist_ok=True)
    fluence_path = fluence_dir / "pt_test.csv"
    pd.DataFrame(weights, columns=["data"]).to_csv(fluence_path)
    dose_path = dose_dir / "pt_test.csv"
    _write_sparse_vector(dose_path, dose)

    return SyntheticCase(
        patient_dir=patient_dir,
        fluence_path=fluence_path,
        dose_path=dose_path,
        grid_shape=grid_shape,
        weights=weights,
        dij=dij,
        dose=dose,
        ct=ct,
        masks=masks,
        spacing_mm=spacing,
    )


@pytest.fixture
def make_synthetic_case(tmp_path: Path) -> Callable[..., SyntheticCase]:
    def _make(**kwargs: object) -> SyntheticCase:
        return write_synthetic_openkbp_opt_case(tmp_path, **kwargs)  # type: ignore[arg-type]

    return _make


@pytest.fixture
def synthetic_case(make_synthetic_case: Callable[..., SyntheticCase]) -> SyntheticCase:
    return make_synthetic_case()
