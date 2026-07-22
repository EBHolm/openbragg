"""Verify the synthetic fixture writes the exact openkbp-opt on-disk format,
so loader tests exercise the real format without committing dataset files."""

import numpy as np
import pandas as pd
from scipy import sparse

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingTypeStubs=false
# pyright: reportUnknownParameterType=false, reportMissingParameterType=false


def test_fixture_writes_expected_files(synthetic_case) -> None:
    sc = synthetic_case
    pdir = sc.patient_dir
    assert (pdir / "dij.npz").exists()
    for name in (
        "ct.csv",
        "dose.csv",
        "possible_dose_mask.csv",
        "voxel_dimensions.csv",
    ):
        assert (pdir / name).exists(), name
    assert (pdir / "PTV70.csv").exists()
    assert sc.fluence_path.exists()
    assert sc.dose_path.exists()


def test_fixture_plan_dose_equals_dij_times_w(synthetic_case) -> None:
    sc = synthetic_case
    dij = sparse.load_npz(sc.patient_dir / "dij.npz").tocsr()
    fluence = pd.read_csv(sc.fluence_path, index_col=0)["data"].to_numpy(dtype=float)
    recomputed = np.asarray(dij @ fluence, dtype=float).reshape(sc.grid_shape)
    np.testing.assert_allclose(recomputed, sc.dose, rtol=1e-12, atol=1e-12)


def test_mask_csv_is_index_only(synthetic_case) -> None:
    # openkbp-opt masks: raveled indices in the index column, all-NaN data column
    df = pd.read_csv(synthetic_case.patient_dir / "PTV70.csv", index_col=0)
    assert df.isnull().values.any()
