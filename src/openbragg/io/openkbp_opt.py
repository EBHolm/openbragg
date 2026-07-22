"""Loader for openkbp-opt cases into the modality-agnostic data model.

Reads the on-disk formats verified against ababier/open-kbp-opt provided_code
(see the pivot spec's format table): Dij as a scipy.sparse .npz; CT and dose as
sparse index+value CSVs; structure/feasible masks as index-only CSVs; voxel
dimensions via np.loadtxt; the beamlet weight vector w as the 'data' column of
the plan-fluence CSV. All raveled indices are C-order over the grid shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pandas as pd
from scipy import sparse

from openbragg.model.case import (
    Case,
    DoseGrid,
    GridShape,
    ImageGrid,
    Plan,
    StructureSet,
)

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingTypeStubs=false

DEFAULT_GRID_SHAPE: GridShape = (128, 128, 128)
OKBP_ROI_NAMES: tuple[str, ...] = (
    "Brainstem",
    "SpinalCord",
    "RightParotid",
    "LeftParotid",
    "Esophagus",
    "Larynx",
    "Mandible",
    "PTV56",
    "PTV63",
    "PTV70",
)


def _read_sparse_vector(path: Path, grid_shape: GridShape) -> npt.NDArray[np.float64]:
    df = pd.read_csv(path, index_col=0)
    indices = df.index.to_numpy(dtype=np.int64)
    data = df["data"].to_numpy(dtype=np.float64)
    flat = np.zeros(int(np.prod(grid_shape)), dtype=np.float64)
    flat[indices] = data
    return flat.reshape(grid_shape)


def _read_mask(path: Path, grid_shape: GridShape) -> npt.NDArray[np.bool_]:
    df = pd.read_csv(path, index_col=0)
    indices = df.index.to_numpy(dtype=np.int64)
    flat = np.zeros(int(np.prod(grid_shape)), dtype=bool)
    flat[indices] = True
    return flat.reshape(grid_shape)


def _read_voxel_dims(path: Path) -> tuple[float, float, float]:
    v = np.asarray(np.loadtxt(path), dtype=np.float64).ravel()
    return (float(v[0]), float(v[1]), float(v[2]))


@dataclass(frozen=True)
class DatasetReport:
    """Summary of what an ``open-kbp-opt-data`` tree contains, for tooling."""

    root: Path
    patient_ids: tuple[str, ...]
    has_plan_fluence: bool

    @property
    def recompute_ready(self) -> bool:
        """True when both the base (patients) and optional (fluence) bundles are present."""
        return bool(self.patient_ids) and self.has_plan_fluence


def verify_dataset(root: str | Path) -> DatasetReport:
    """Inspect an ``open-kbp-opt-data`` tree and report what is present.

    Checks for ``reference-plans/pt_*`` patients (base bundle) and any
    ``paper-plans/*/plan-fluence`` directory (optional bundle — the source of
    the beamlet weight vector ``w``).
    """
    root = Path(root)
    patient_ids = tuple(d.name for d in find_patient_dirs(root))
    has_plan_fluence = (
        next((root / "paper-plans").glob("*/plan-fluence"), None) is not None
    )
    return DatasetReport(root, patient_ids, has_plan_fluence)


def find_patient_dirs(root: str | Path) -> list[Path]:
    """Return the sorted ``reference-plans/pt_*`` patient directories under *root*.

    *root* is an ``open-kbp-opt-data`` tree (see the dataset README). Used by the
    fetch/curation tooling to enumerate patients without hard-coding IDs.
    """
    reference_plans = Path(root) / "reference-plans"
    return sorted(p for p in reference_plans.glob("pt_*") if p.is_dir())


def resolve_plan_paths(
    root: str | Path, patient_id: str, model: str | None = None
) -> tuple[Path, Path]:
    """Locate the ``(plan-fluence, plan-dose)`` CSVs for *patient_id* under *root*.

    Globs ``paper-plans/<model>/plan-fluence/**/<patient_id>.csv`` — the ``**``
    tolerates both the flat README layout (``plan-fluence/pt_*.csv``) and any
    prediction-set nesting — then derives the matching ``plan-dose`` path by
    swapping the ``plan-fluence`` path component. When *model* is ``None`` any
    model matches; the first path in sorted order is chosen for determinism.

    Raises ``FileNotFoundError`` if no ``plan-fluence`` CSV exists for the
    patient. The returned ``plan-dose`` path is not guaranteed to exist — callers
    that need the reference dose should check.
    """
    paper_plans = Path(root) / "paper-plans"
    pattern = f"{model or '*'}/plan-fluence/**/{patient_id}.csv"
    matches = sorted(paper_plans.glob(pattern))
    if not matches:
        raise FileNotFoundError(
            f"no plan-fluence CSV for {patient_id!r} under {paper_plans}"
        )
    fluence = matches[0]
    parts = list(fluence.parts)
    parts[parts.index("plan-fluence")] = "plan-dose"
    return fluence, Path(*parts)


def load_dij(
    patient_dir: str | Path, grid_shape: GridShape = DEFAULT_GRID_SHAPE
) -> sparse.csr_matrix:
    dij = sparse.load_npz(Path(patient_dir) / "dij.npz").tocsr()
    n_vox = int(np.prod(grid_shape))
    if dij.shape[0] != n_vox:
        raise ValueError(
            f"Dij has {dij.shape[0]} rows but grid {grid_shape} has {n_vox} voxels"
        )
    return dij


def load_weights(fluence_path: str | Path) -> npt.NDArray[np.float64]:
    df = pd.read_csv(fluence_path, index_col=0)
    return df["data"].to_numpy(dtype=np.float64)


def load_case(
    patient_dir: str | Path,
    fluence_path: str | Path,
    dose_path: str | Path | None = None,
    grid_shape: GridShape = DEFAULT_GRID_SHAPE,
    identifier: str | None = None,
) -> Case:
    patient_dir = Path(patient_dir)
    spacing = _read_voxel_dims(patient_dir / "voxel_dimensions.csv")
    ct = _read_sparse_vector(patient_dir / "ct.csv", grid_shape)
    masks: dict[str, npt.NDArray[np.bool_]] = {}
    for name in OKBP_ROI_NAMES:
        mask_path = patient_dir / f"{name}.csv"
        if mask_path.exists():
            masks[name] = _read_mask(mask_path, grid_shape)
    weights = load_weights(fluence_path)
    reference_dose: DoseGrid | None = None
    if dose_path is not None:
        reference_dose = DoseGrid(
            _read_sparse_vector(Path(dose_path), grid_shape), spacing
        )
    return Case(
        identifier=identifier if identifier is not None else patient_dir.name,
        image=ImageGrid(ct, spacing),
        structures=StructureSet(masks),
        plan=Plan(weights),
        reference_dose=reference_dose,
    )
