# Photon Recompute Tracer Bullet — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make photon dose flow end-to-end through OpenBragg — load an openkbp-opt case, source its precomputed `Dij` behind the dose-engine seam, compute `dose = Dij · w`, and verify it reproduces the shipped `plan-dose` — all on a synthetic in-format fixture wired into CI.

**Architecture:** A modality-agnostic `Case` data model is populated by an openkbp-opt loader (reads the verified CSV/`.npz` formats). The `DoseEngine` seam turns a `Case` into a `DijResult`; `OpenKBPOptEngine` implements it by *sourcing* the shipped `Dij` from disk (not computing physics). `total_dose(DijResult, w)` does the sparse matvec and reshapes to the 3D grid. Because openkbp-opt itself computes `plan-dose = Dij·w_opt`, the recompute has an *exact* floating-point known answer.

**Tech Stack:** Python 3.12+, numpy, scipy (`scipy.sparse`), pandas, Typer (CLI), pytest, pyright (strict). Package under `src/openbragg/`, tests under `tests/`.

**Scope note (read first):** This is **Slice 1** of the photon-first Phase-1 milestone — the tracer bullet only. It corresponds to the reframed issues **#4 (ingest + data model)** and **#5 (seam + recompute)**, plus the seed of the CI regression fixture from #13. **Out of this plan** (each its own follow-on slice/plan): full gamma (3%/3mm, 2%/2mm) and DVH suites, dose statistics / clinical-goal checks, RTDOSE export, provenance manifest, visualization, and the real-data download/validation path. Verification here uses a tight numeric-agreement assertion (`assert_allclose`), which is sufficient because the fixture's `plan-dose` equals `Dij·w` by construction; field-standard gamma arrives in the evaluation slice.

## Global Constraints

- **Python 3.12+**; `requires-python >=3.12` (do not lower).
- **All commands run under `uv`** — `uv run pytest`, `uv run pyright`, `uv sync`. Never call bare `python`/`pytest`.
- **pyright mode: strict** (per `pyproject.toml`). scipy.sparse and some pandas members are untyped; relax *per-file* with a top-of-file `# pyright:` comment (shown in tasks), never lower the global bar.
- **Imports at module top** — no function-body imports (CLAUDE.md).
- **Tests live under `tests/`**, mirroring the package layout; never under `src/`.
- **Assert on external behavior** — dose arrays, shapes, agreement metrics — not internal structures.
- **License:** Apache-2.0. openkbp-opt code is MIT, its dataset CC BY 4.0 — usable as fixtures with attribution; **never commit dataset files** (`.gitignore` already blocks `*.npz`, `data/`, `cases/`). The synthetic fixture is generated at test time into `tmp_path`, committing no binary data.
- **All raveled voxel indices are C-order over the grid shape** (numpy default), matching `Dij` row order. Dose units are **Gy** throughout.
- **Commit only files relevant to each task** — never `git add .` (CLAUDE.md). Commits authored as EBHolm (repo-local git config enforces it).
- Branch: `docs/photon-first-pivot` already exists with the spec; implement on a feature branch off it or continue there per the executor's preference.

---

### Task 1: Project setup — tracker labels, PRD addendum, slice-1 photon issues

**Files:**
- Modify: `PRD.md` (append addendum section)

**Interfaces:**
- Consumes: nothing.
- Produces: GitHub labels `phase:photon` / `phase:proton`; existing issues #4–#13 labelled `phase:proton`; two new `phase:photon` issues for this slice; a PRD addendum documenting the pivot.

> **Executor note:** Steps 1–3 are outward-facing GitHub mutations approved by the user during brainstorming. Confirm before running if executing unattended. No test cycle.

- [ ] **Step 1: Create the phase labels**

```bash
gh label create "phase:photon" --repo EBHolm/openbragg --color 1d76db \
  --description "Photon-first Phase-1 (openkbp-opt) work" || true
gh label create "phase:proton" --repo EBHolm/openbragg --color 5319e7 \
  --description "Proton true-north work (sequenced behind photon-first)" || true
```

- [ ] **Step 2: Label the existing proton issues**

```bash
for n in 4 5 6 7 8 9 10 11 12 13; do
  gh issue edit "$n" --repo EBHolm/openbragg --add-label "phase:proton"
done
```

- [ ] **Step 3: Open the two slice-1 photon issues**

```bash
gh issue create --repo EBHolm/openbragg --label "phase:photon" \
  --title "[photon] openkbp-opt ingest + modality-agnostic data model" \
  --body "Photon-phase reframe of #4. Load an openkbp-opt case (CT, structure masks, feasible-dose mask, voxel dims, plan-fluence weights, plan-dose) into a modality-agnostic in-memory Case, reading the verified CSV/.npz formats. Not DICOM. See docs/superpowers/specs/2026-07-22-photon-first-pivot-design.md and docs/superpowers/plans/2026-07-22-photon-recompute-tracer-bullet.md (Tasks 2-4)."

gh issue create --repo EBHolm/openbragg --label "phase:photon" \
  --title "[photon] Dose-engine seam + openkbp-opt loader engine; recompute Dij·w" \
  --body "Photon-phase reframe of #5. Define the DoseEngine seam (Case -> DijResult) and an OpenKBPOptEngine that sources the shipped precomputed Dij from disk. Compute total dose = Dij·w and verify it reproduces plan-dose (exact by construction). See the pivot spec and plan Tasks 5-7."
```

- [ ] **Step 4: Append the PRD addendum**

Add to the end of `PRD.md`:

```markdown
## Addendum (2026-07-22): Photon-first sequencing of Phase 1

Phase 1's dose-recalculation / verification pipeline is being brought up on **photon**
data first, anchored on the open **openkbp-opt** dataset, with **proton remaining the
project's true-north**. This cashes in the modality-agnostic architecture (see
"Implementation Decisions → Modality") earlier than originally sequenced, because the
open-data story for photons is decisively better: openkbp-opt ships a precomputed
`Dij` + reference/plan doses (`dose = Dij·w`, the identical object OpenBragg is built
around), whereas no verified fully-open proton RTION-plan + reference-dose dataset was
found.

The photon-first milestone is **recompute-only** (no optimizer): consume the precomputed
`Dij`, compute `Dij·w` from the shipped beamlet weights (`plan-fluence`), and verify it
reproduces `plan-dose` via gamma + DVH. This exercises the whole Dij-consumer half of the
pipeline on real data now, but — because the `Dij` is precomputed — it does **not** validate
dose physics or the engine seam's produce-a-`Dij` path. Proton-specific modules (HU→RSP,
MCsquare wrapping, Bortfeld/PSTAR analytics) are deferred to the proton phase.

Canonical design: `docs/superpowers/specs/2026-07-22-photon-first-pivot-design.md`.
Issues are split by `phase:photon` / `phase:proton`; the proton issues (#4–#13) are
preserved unchanged.
```

- [ ] **Step 5: Commit the PRD change**

```bash
git add PRD.md
git commit -m "docs: add photon-first Phase-1 addendum to PRD"
```

---

### Task 2: Modality-agnostic data model

**Files:**
- Create: `src/openbragg/model/__init__.py`
- Create: `src/openbragg/model/case.py`
- Test: `tests/openbragg/model/test_case.py`

**Interfaces:**
- Consumes: nothing (numpy only).
- Produces:
  - `GridShape = tuple[int, int, int]`, `FloatArray = npt.NDArray[np.float64]`, `BoolArray = npt.NDArray[np.bool_]`
  - `ImageGrid(array: FloatArray, spacing_mm: tuple[float, float, float])` with property `shape -> GridShape`
  - `StructureSet(masks: dict[str, BoolArray])`
  - `Plan(weights: FloatArray)`
  - `DoseGrid(array: FloatArray, spacing_mm: tuple[float, float, float])`
  - `Case(identifier: str, image: ImageGrid, structures: StructureSet, plan: Plan, reference_dose: DoseGrid | None = None)`

- [ ] **Step 1: Write the failing test**

```python
# tests/openbragg/model/test_case.py
"""Behavioral tests for the modality-agnostic data model."""

import numpy as np

from openbragg.model.case import Case, DoseGrid, ImageGrid, Plan, StructureSet


def test_image_grid_reports_shape_and_spacing() -> None:
    img = ImageGrid(np.zeros((4, 5, 6)), spacing_mm=(3.0, 3.0, 2.5))
    assert img.shape == (4, 5, 6)
    assert img.spacing_mm == (3.0, 3.0, 2.5)


def test_case_holds_parts() -> None:
    img = ImageGrid(np.zeros((2, 2, 2)), spacing_mm=(1.0, 1.0, 1.0))
    structures = StructureSet({"PTV70": np.ones((2, 2, 2), dtype=bool)})
    plan = Plan(np.array([1.0, 2.0]))
    dose = DoseGrid(np.zeros((2, 2, 2)), spacing_mm=(1.0, 1.0, 1.0))
    case = Case("pt_test", img, structures, plan, reference_dose=dose)
    assert case.identifier == "pt_test"
    assert case.plan.weights.shape == (2,)
    assert set(case.structures.masks) == {"PTV70"}
    assert case.reference_dose is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/openbragg/model/test_case.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'openbragg.model'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/openbragg/model/__init__.py
```

(empty file)

```python
# src/openbragg/model/case.py
"""Modality-agnostic in-memory patient/plan data model.

Every downstream module operates on these types, never on engine- or
format-specific structures. Photon (openkbp-opt) and, later, proton (DICOM-RT)
cases both populate the same ``Case``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]
BoolArray = npt.NDArray[np.bool_]
GridShape = tuple[int, int, int]


@dataclass(frozen=True)
class ImageGrid:
    """A CT image on a regular 3D grid. ``spacing_mm`` is (dx, dy, dz)."""

    array: FloatArray
    spacing_mm: tuple[float, float, float]

    @property
    def shape(self) -> GridShape:
        s = self.array.shape
        return (int(s[0]), int(s[1]), int(s[2]))


@dataclass(frozen=True)
class StructureSet:
    """Named binary masks aligned to the image grid (name -> bool array)."""

    masks: dict[str, BoolArray]


@dataclass(frozen=True)
class Plan:
    """A delivered/optimized plan as its beamlet (or spot) weight vector ``w``."""

    weights: FloatArray


@dataclass(frozen=True)
class DoseGrid:
    """A dose distribution on the image grid, in Gy."""

    array: FloatArray
    spacing_mm: tuple[float, float, float]


@dataclass(frozen=True)
class Case:
    """An in-memory patient/plan case.

    ``reference_dose`` is the dose to recompute against (for openkbp-opt, the
    shipped ``plan-dose`` = Dij·w by construction).
    """

    identifier: str
    image: ImageGrid
    structures: StructureSet
    plan: Plan
    reference_dose: DoseGrid | None = None
```

- [ ] **Step 4: Run tests + type check**

Run: `uv run pytest tests/openbragg/model/test_case.py -v && uv run pyright src/openbragg/model tests/openbragg/model`
Expected: tests PASS; pyright 0 errors.

- [ ] **Step 5: Commit**

```bash
git add src/openbragg/model tests/openbragg/model
git commit -m "feat(model): add modality-agnostic Case data model"
```

---

### Task 3: Add scipy/pandas + synthetic openkbp-opt fixture builder

**Files:**
- Modify: `pyproject.toml` (add `scipy`, `pandas` to `[project].dependencies`)
- Create: `tests/conftest.py`
- Test: `tests/openbragg/test_fixture_format.py`

**Interfaces:**
- Consumes: nothing.
- Produces (pytest fixtures + a dataclass, available to all tests):
  - `SyntheticCase` dataclass with fields: `patient_dir: Path`, `fluence_path: Path`, `dose_path: Path`, `grid_shape: tuple[int,int,int]`, `weights: npt.NDArray[np.float64]`, `dij` (`scipy.sparse.csr_matrix`), `dose: npt.NDArray[np.float64]` (dense, == `(dij@w).reshape(grid_shape)`), `ct: npt.NDArray[np.float64]`, `masks: dict[str, npt.NDArray[np.bool_]]`, `spacing_mm: tuple[float,float,float]`
  - fixture `make_synthetic_case` → `Callable[..., SyntheticCase]` (kwargs: `grid_shape`, `n_beamlets`, `seed`), writes into `tmp_path`
  - fixture `synthetic_case` → `SyntheticCase` (defaults: grid `(4,4,4)`, 3 beamlets, seed 0)
- On-disk layout written (verified against real openkbp-opt): `reference-plans/pt_test/{dij.npz, ct.csv, dose.csv, possible_dose_mask.csv, <ROI>.csv, voxel_dimensions.csv}` and `paper-plans/MeanRel/plan-fluence/set_1/pt_test.csv`, `paper-plans/MeanRel/plan-dose/set_1/pt_test.csv`.

- [ ] **Step 1: Add dependencies**

Edit `pyproject.toml` `[project].dependencies` to include `scipy` and `pandas`:

```toml
dependencies = [
    "numpy",
    "scipy",
    "pandas",
    "matplotlib",
    "typer",
    "pydicom>=3.0.2",
]
```

Then: `uv sync`
Expected: lockfile updates; scipy + pandas installed.

- [ ] **Step 2: Write the failing test**

```python
# tests/openbragg/test_fixture_format.py
"""Verify the synthetic fixture writes the exact openkbp-opt on-disk format,
so loader tests exercise the real format without committing dataset files."""

import numpy as np
import pandas as pd
from scipy import sparse


def test_fixture_writes_expected_files(synthetic_case) -> None:
    sc = synthetic_case
    pdir = sc.patient_dir
    assert (pdir / "dij.npz").exists()
    for name in ("ct.csv", "dose.csv", "possible_dose_mask.csv", "voxel_dimensions.csv"):
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/openbragg/test_fixture_format.py -v`
Expected: FAIL — fixtures `synthetic_case` not found.

- [ ] **Step 4: Write the fixture builder**

```python
# tests/conftest.py
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
```

- [ ] **Step 5: Run tests + type check**

Run: `uv run pytest tests/openbragg/test_fixture_format.py -v && uv run pyright tests/conftest.py`
Expected: 3 tests PASS; pyright 0 errors (the per-file `# pyright:` comment suppresses scipy/pandas unknown-type noise). If pyright reports *other* real errors, fix them.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock tests/conftest.py tests/openbragg/test_fixture_format.py
git commit -m "test: add scipy/pandas deps and synthetic openkbp-opt fixture builder"
```

---

### Task 4: openkbp-opt loader

**Files:**
- Create: `src/openbragg/io/__init__.py`
- Create: `src/openbragg/io/openkbp_opt.py`
- Test: `tests/openbragg/io/test_openkbp_opt.py`

**Interfaces:**
- Consumes: `Case, DoseGrid, ImageGrid, Plan, StructureSet, GridShape` from `openbragg.model.case`; the `synthetic_case` fixture.
- Produces:
  - `DEFAULT_GRID_SHAPE: GridShape = (128, 128, 128)`
  - `OKBP_ROI_NAMES: tuple[str, ...]`
  - `load_dij(patient_dir: str | Path, grid_shape: GridShape = DEFAULT_GRID_SHAPE) -> scipy.sparse.csr_matrix`
  - `load_weights(fluence_path: str | Path) -> npt.NDArray[np.float64]`
  - `load_case(patient_dir, fluence_path, dose_path=None, grid_shape=DEFAULT_GRID_SHAPE, identifier=None) -> Case`

- [ ] **Step 1: Write the failing test**

```python
# tests/openbragg/io/test_openkbp_opt.py
"""Behavioral tests for the openkbp-opt loader against the synthetic fixture."""

import numpy as np

from openbragg.io.openkbp_opt import load_case, load_dij, load_weights


def test_load_case_populates_model(synthetic_case) -> None:
    sc = synthetic_case
    case = load_case(sc.patient_dir, sc.fluence_path, sc.dose_path, grid_shape=sc.grid_shape)
    assert case.identifier == "pt_test"
    assert case.image.shape == sc.grid_shape
    assert case.image.spacing_mm == sc.spacing_mm
    assert set(case.structures.masks) == {"PTV70", "SpinalCord"}
    np.testing.assert_array_equal(case.structures.masks["PTV70"], sc.masks["PTV70"])
    np.testing.assert_allclose(case.plan.weights, sc.weights)
    assert case.reference_dose is not None
    np.testing.assert_allclose(case.reference_dose.array, sc.dose)


def test_load_case_without_dose_has_none(synthetic_case) -> None:
    sc = synthetic_case
    case = load_case(sc.patient_dir, sc.fluence_path, grid_shape=sc.grid_shape)
    assert case.reference_dose is None


def test_load_dij_shape_and_weights(synthetic_case) -> None:
    sc = synthetic_case
    dij = load_dij(sc.patient_dir, grid_shape=sc.grid_shape)
    assert dij.shape == (int(np.prod(sc.grid_shape)), sc.weights.shape[0])
    w = load_weights(sc.fluence_path)
    np.testing.assert_allclose(w, sc.weights)


def test_load_dij_rejects_wrong_grid(synthetic_case) -> None:
    sc = synthetic_case
    try:
        load_dij(sc.patient_dir, grid_shape=(7, 7, 7))
    except ValueError:
        return
    raise AssertionError("expected ValueError for mismatched grid")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/openbragg/io/test_openkbp_opt.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'openbragg.io'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/openbragg/io/__init__.py
```

(empty file)

```python
# src/openbragg/io/openkbp_opt.py
"""Loader for openkbp-opt cases into the modality-agnostic data model.

Reads the on-disk formats verified against ababier/open-kbp-opt provided_code
(see the pivot spec's format table): Dij as a scipy.sparse .npz; CT and dose as
sparse index+value CSVs; structure/feasible masks as index-only CSVs; voxel
dimensions via np.loadtxt; the beamlet weight vector w as the 'data' column of
the plan-fluence CSV. All raveled indices are C-order over the grid shape.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import numpy.typing as npt
import pandas as pd
from scipy import sparse

from openbragg.model.case import Case, DoseGrid, GridShape, ImageGrid, Plan, StructureSet

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


def load_dij(patient_dir: str | Path, grid_shape: GridShape = DEFAULT_GRID_SHAPE) -> sparse.csr_matrix:
    dij = sparse.load_npz(Path(patient_dir) / "dij.npz").tocsr()
    n_vox = int(np.prod(grid_shape))
    if dij.shape[0] != n_vox:
        raise ValueError(f"Dij has {dij.shape[0]} rows but grid {grid_shape} has {n_vox} voxels")
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
        reference_dose = DoseGrid(_read_sparse_vector(Path(dose_path), grid_shape), spacing)
    return Case(
        identifier=identifier if identifier is not None else patient_dir.name,
        image=ImageGrid(ct, spacing),
        structures=StructureSet(masks),
        plan=Plan(weights),
        reference_dose=reference_dose,
    )
```

- [ ] **Step 4: Run tests + type check**

Run: `uv run pytest tests/openbragg/io/test_openkbp_opt.py -v && uv run pyright src/openbragg/io tests/openbragg/io`
Expected: 4 tests PASS; pyright 0 errors.

- [ ] **Step 5: Commit**

```bash
git add src/openbragg/io tests/openbragg/io
git commit -m "feat(io): add openkbp-opt loader into the Case data model"
```

---

### Task 5: Dose-engine seam + openkbp-opt loader engine

**Files:**
- Create: `src/openbragg/engine/__init__.py`
- Create: `src/openbragg/engine/base.py`
- Create: `src/openbragg/engine/openkbp_opt.py`
- Test: `tests/openbragg/engine/test_openkbp_opt_engine.py`

**Interfaces:**
- Consumes: `Case, GridShape` from `openbragg.model.case`; `DEFAULT_GRID_SHAPE, load_dij` from `openbragg.io.openkbp_opt`.
- Produces:
  - `DijResult(dij: scipy.sparse.csr_matrix, grid_shape: GridShape, units: str = "Gy")` — validates `dij.shape[0] == prod(grid_shape)` in `__post_init__`.
  - `DoseEngine` (typing `Protocol`) with `compute_dij(self, case: Case) -> DijResult`.
  - `OpenKBPOptEngine(patient_dir: str | Path, grid_shape: GridShape = DEFAULT_GRID_SHAPE)` implementing `DoseEngine`; `compute_dij` loads the shipped Dij and validates it against the case's grid and weight count.

- [ ] **Step 1: Write the failing test**

```python
# tests/openbragg/engine/test_openkbp_opt_engine.py
"""Behavioral tests for the dose-engine seam and the openkbp-opt loader engine."""

import numpy as np
import pytest

from openbragg.engine.base import DijResult, DoseEngine
from openbragg.engine.openkbp_opt import OpenKBPOptEngine
from openbragg.io.openkbp_opt import load_case


def test_engine_sources_dij_matching_case(synthetic_case) -> None:
    sc = synthetic_case
    case = load_case(sc.patient_dir, sc.fluence_path, sc.dose_path, grid_shape=sc.grid_shape)
    engine: DoseEngine = OpenKBPOptEngine(sc.patient_dir, grid_shape=sc.grid_shape)
    result = engine.compute_dij(case)
    assert isinstance(result, DijResult)
    assert result.grid_shape == sc.grid_shape
    assert result.units == "Gy"
    assert result.dij.shape == (int(np.prod(sc.grid_shape)), sc.weights.shape[0])


def test_dij_result_rejects_row_mismatch(synthetic_case) -> None:
    sc = synthetic_case
    dij = sc.dij
    with pytest.raises(ValueError):
        DijResult(dij=dij, grid_shape=(7, 7, 7))


def test_engine_rejects_weight_count_mismatch(make_synthetic_case) -> None:
    sc = make_synthetic_case(grid_shape=(4, 4, 4), n_beamlets=3)
    # Build a case whose plan has the wrong number of weights.
    case = load_case(sc.patient_dir, sc.fluence_path, sc.dose_path, grid_shape=sc.grid_shape)
    bad = OpenKBPOptEngine(sc.patient_dir, grid_shape=sc.grid_shape)
    from dataclasses import replace

    from openbragg.model.case import Plan

    mangled = replace(case, plan=Plan(np.array([1.0, 2.0])))  # 2 != 3 beamlets
    with pytest.raises(ValueError):
        bad.compute_dij(mangled)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/openbragg/engine/test_openkbp_opt_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'openbragg.engine'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/openbragg/engine/__init__.py
```

(empty file)

```python
# src/openbragg/engine/base.py
"""The dose-engine seam — OpenBragg's primary interface.

An engine turns a Case into a Dij influence matrix (sparse voxels×beamlets) plus
grid/units metadata. Nothing downstream talks to an engine directly — only to
``DijResult``. A precomputed-Dij loader and a future computing engine both
implement this same Protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from scipy import sparse

from openbragg.model.case import Case, GridShape

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingTypeStubs=false


@dataclass(frozen=True)
class DijResult:
    """The output of the dose-engine seam.

    ``dij`` is voxels×beamlets; total dose is ``dij @ w`` in ``units`` (Gy).
    """

    dij: sparse.csr_matrix
    grid_shape: GridShape
    units: str = "Gy"

    def __post_init__(self) -> None:
        n_vox = int(np.prod(self.grid_shape))
        if self.dij.shape[0] != n_vox:
            raise ValueError(
                f"Dij has {self.dij.shape[0]} rows but grid {self.grid_shape} has {n_vox} voxels"
            )


class DoseEngine(Protocol):
    """Any dose engine (wrapped, in-house, or a precomputed-Dij loader)."""

    def compute_dij(self, case: Case) -> DijResult: ...
```

```python
# src/openbragg/engine/openkbp_opt.py
"""A dose 'engine' that sources a precomputed openkbp-opt Dij from disk.

This implements the DoseEngine seam without computing physics: it loads the
shipped Dij (CERR IMRTP output) and validates it against the case's grid and
beamlet count, so the seam contract is exercised end-to-end. A future computing
engine drops in behind the identical interface.
"""

from __future__ import annotations

from pathlib import Path

from openbragg.engine.base import DijResult
from openbragg.io.openkbp_opt import DEFAULT_GRID_SHAPE, load_dij
from openbragg.model.case import Case, GridShape


class OpenKBPOptEngine:
    def __init__(self, patient_dir: str | Path, grid_shape: GridShape = DEFAULT_GRID_SHAPE) -> None:
        self._patient_dir = Path(patient_dir)
        self._grid_shape = grid_shape

    def compute_dij(self, case: Case) -> DijResult:
        if case.image.shape != self._grid_shape:
            raise ValueError(f"case grid {case.image.shape} != engine grid {self._grid_shape}")
        dij = load_dij(self._patient_dir, self._grid_shape)
        if dij.shape[1] != case.plan.weights.shape[0]:
            raise ValueError(
                f"Dij has {dij.shape[1]} beamlet columns but plan has {case.plan.weights.shape[0]} weights"
            )
        return DijResult(dij=dij, grid_shape=self._grid_shape, units="Gy")
```

- [ ] **Step 4: Run tests + type check**

Run: `uv run pytest tests/openbragg/engine/test_openkbp_opt_engine.py -v && uv run pyright src/openbragg/engine tests/openbragg/engine`
Expected: 3 tests PASS; pyright 0 errors (including that `OpenKBPOptEngine` satisfies the `DoseEngine` Protocol — the `engine: DoseEngine = OpenKBPOptEngine(...)` line in the test is a structural type check).

- [ ] **Step 5: Commit**

```bash
git add src/openbragg/engine tests/openbragg/engine
git commit -m "feat(engine): add dose-engine seam and openkbp-opt loader engine"
```

---

### Task 6: Dose accumulation (Dij · w)

**Files:**
- Create: `src/openbragg/dose/__init__.py`
- Create: `src/openbragg/dose/accumulate.py`
- Test: `tests/openbragg/dose/test_accumulate.py`

**Interfaces:**
- Consumes: `DijResult` from `openbragg.engine.base`.
- Produces: `total_dose(dij_result: DijResult, weights: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]` — returns the 3D dose grid (Gy); raises `ValueError` on beamlet-count mismatch.

- [ ] **Step 1: Write the failing test**

```python
# tests/openbragg/dose/test_accumulate.py
"""Behavioral tests for total-dose accumulation."""

import numpy as np
import pytest

from openbragg.dose.accumulate import total_dose
from openbragg.engine.base import DijResult


def test_total_dose_matches_known_answer(synthetic_case) -> None:
    sc = synthetic_case
    result = DijResult(dij=sc.dij, grid_shape=sc.grid_shape)
    dose = total_dose(result, sc.weights)
    assert dose.shape == sc.grid_shape
    np.testing.assert_allclose(dose, sc.dose, rtol=1e-12, atol=1e-12)


def test_total_dose_is_linear_in_weights(synthetic_case) -> None:
    sc = synthetic_case
    result = DijResult(dij=sc.dij, grid_shape=sc.grid_shape)
    d1 = total_dose(result, sc.weights)
    d2 = total_dose(result, 2.0 * sc.weights)
    np.testing.assert_allclose(d2, 2.0 * d1, rtol=1e-12, atol=1e-12)


def test_total_dose_rejects_weight_mismatch(synthetic_case) -> None:
    sc = synthetic_case
    result = DijResult(dij=sc.dij, grid_shape=sc.grid_shape)
    with pytest.raises(ValueError):
        total_dose(result, np.ones(sc.weights.shape[0] + 1))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/openbragg/dose/test_accumulate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'openbragg.dose'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/openbragg/dose/__init__.py
```

(empty file)

```python
# src/openbragg/dose/accumulate.py
"""Total dose accumulation: dose = Dij · w on the calculation grid (Gy)."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from openbragg.engine.base import DijResult

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingTypeStubs=false


def total_dose(dij_result: DijResult, weights: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    dij = dij_result.dij
    if dij.shape[1] != weights.shape[0]:
        raise ValueError(
            f"Dij has {dij.shape[1]} beamlet columns but w has {weights.shape[0]} entries"
        )
    flat = dij @ weights
    return np.asarray(flat, dtype=np.float64).reshape(dij_result.grid_shape)
```

- [ ] **Step 4: Run tests + type check**

Run: `uv run pytest tests/openbragg/dose/test_accumulate.py -v && uv run pyright src/openbragg/dose tests/openbragg/dose`
Expected: 3 tests PASS; pyright 0 errors.

- [ ] **Step 5: Commit**

```bash
git add src/openbragg/dose tests/openbragg/dose
git commit -m "feat(dose): add Dij·w total-dose accumulation"
```

---

### Task 7: End-to-end recompute + `recompute` CLI subcommand

**Files:**
- Modify: `src/openbragg/cli.py` (register a `recompute` command)
- Test: `tests/openbragg/test_recompute_e2e.py`
- Test: `tests/openbragg/test_cli.py` (add a CLI test)

**Interfaces:**
- Consumes: `load_case` (`openbragg.io.openkbp_opt`), `OpenKBPOptEngine` (`openbragg.engine.openkbp_opt`), `total_dose` (`openbragg.dose.accumulate`).
- Produces: `openbragg recompute PATIENT_DIR --fluence FLUENCE [--plan-dose DOSE] [--grid nx,ny,nz]` — prints the recomputed dose shape/max and, when `--plan-dose` is given, the max absolute difference vs `plan-dose`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/openbragg/test_recompute_e2e.py
"""End-to-end tracer bullet: load -> seam -> Dij·w reproduces plan-dose."""

import numpy as np

from openbragg.dose.accumulate import total_dose
from openbragg.engine.openkbp_opt import OpenKBPOptEngine
from openbragg.io.openkbp_opt import load_case


def test_recompute_reproduces_plan_dose(synthetic_case) -> None:
    sc = synthetic_case
    case = load_case(sc.patient_dir, sc.fluence_path, sc.dose_path, grid_shape=sc.grid_shape)
    engine = OpenKBPOptEngine(sc.patient_dir, grid_shape=sc.grid_shape)
    dose = total_dose(engine.compute_dij(case), case.plan.weights)
    assert dose.shape == sc.grid_shape
    assert case.reference_dose is not None
    np.testing.assert_allclose(dose, case.reference_dose.array, rtol=1e-9, atol=1e-9)
    assert float(np.max(np.abs(dose - case.reference_dose.array))) < 1e-6
```

Add to `tests/openbragg/test_cli.py`:

```python
def test_recompute_cli(synthetic_case) -> None:
    sc = synthetic_case
    result = runner.invoke(
        app,
        [
            "recompute",
            str(sc.patient_dir),
            "--fluence",
            str(sc.fluence_path),
            "--plan-dose",
            str(sc.dose_path),
            "--grid",
            "4,4,4",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "max abs diff vs plan-dose" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/openbragg/test_recompute_e2e.py tests/openbragg/test_cli.py::test_recompute_cli -v`
Expected: E2E test PASSES (its modules already exist); the CLI test FAILS — no `recompute` command (nonzero exit / usage error).

- [ ] **Step 3: Add the `recompute` command to the CLI**

Replace the imports block and append the command in `src/openbragg/cli.py`. New top-of-file imports:

```python
"""Command-line entry point for OpenBragg.

Exposes a Typer ``app`` wired to the ``openbragg`` console script. Phase-1
slices register their subcommands onto this ``app``.
"""

from pathlib import Path

import numpy as np
import typer

from openbragg import __version__
from openbragg.dose.accumulate import total_dose
from openbragg.engine.openkbp_opt import OpenKBPOptEngine
from openbragg.io.openkbp_opt import load_case
```

Keep the existing `app`, `_version_callback`, and `main` callback unchanged. Append:

```python
@app.command()
def recompute(
    patient_dir: Path = typer.Argument(
        ..., help="openkbp-opt reference-plans/pt_* directory (contains dij.npz)."
    ),
    fluence: Path = typer.Option(
        ..., "--fluence", help="plan-fluence CSV: the beamlet weight vector w."
    ),
    plan_dose: Path | None = typer.Option(
        None, "--plan-dose", help="plan-dose CSV to compare the recompute against."
    ),
    grid: str = typer.Option(
        "128,128,128", "--grid", help="Grid shape as 'nx,ny,nz' (openkbp-opt is 128,128,128)."
    ),
) -> None:
    """Recompute dose = Dij·w for an openkbp-opt case and report agreement."""
    parts = tuple(int(x) for x in grid.split(","))
    if len(parts) != 3:
        raise typer.BadParameter("grid must be 'nx,ny,nz'")
    grid_shape = (parts[0], parts[1], parts[2])
    case = load_case(patient_dir, fluence, plan_dose, grid_shape=grid_shape)
    engine = OpenKBPOptEngine(patient_dir, grid_shape=grid_shape)
    dose = total_dose(engine.compute_dij(case), case.plan.weights)
    typer.echo(f"recomputed dose: shape={dose.shape} max={float(dose.max()):.4g} Gy")
    if case.reference_dose is not None:
        max_abs = float(np.max(np.abs(dose - case.reference_dose.array)))
        typer.echo(f"max abs diff vs plan-dose: {max_abs:.3e} Gy")
```

- [ ] **Step 4: Run the full suite + type check**

Run: `uv run pytest -q && uv run pyright`
Expected: all tests PASS (including the existing CLI smoke tests); pyright 0 errors across `src` and `tests`.

- [ ] **Step 5: Commit**

```bash
git add src/openbragg/cli.py tests/openbragg/test_recompute_e2e.py tests/openbragg/test_cli.py
git commit -m "feat(cli): add recompute command and end-to-end recompute tracer bullet"
```

---

## Self-Review

**Spec coverage (against `2026-07-22-photon-first-pivot-design.md`):**
- Modality-agnostic data model → Task 2. ✓
- openkbp-opt array ingest (verified formats; not DICOM) → Tasks 3–4. ✓
- Dose-engine seam + loader engine (contract exercised; Dij sourced) → Task 5. ✓
- `dose = Dij·w`, Gy, C-order reshape → Task 6. ✓
- Recompute reproduces `plan-dose` (exact known answer) → Task 7. ✓
- `w` = `plan-fluence` (not `plan-weights`) → encoded in the fixture (Task 3) and loader (Task 4). ✓
- Fixture strategy: generated in `tmp_path`, no committed data, respects `.gitignore` → Task 3. ✓
- Tracker labels + PRD addendum + photon issues → Task 1. ✓
- **Deferred, by design (own slices):** gamma (3%/3mm, 2%/2mm), DVH, dose stats/clinical goals, RTDOSE export, provenance manifest, visualization, real-data download/validation. Called out in the scope note — not gaps.

**Placeholder scan:** No TBD/TODO; every code step shows complete code; every command shows expected output. The `# pyright:` per-file relaxation is a concrete, bounded instruction (matches the dev-scaffold ADR), not a placeholder.

**Type consistency:** `GridShape` defined in `model/case.py`, imported everywhere. `DijResult` (fields `dij`, `grid_shape`, `units`) consistent across engine/base (Task 5), dose/accumulate (Task 6), and E2E (Task 7). `load_case`/`load_dij`/`load_weights` signatures match between Task 4 (produces) and Tasks 5/7 (consume). `SyntheticCase` field names used by Tasks 3–7 match the Task 3 definition. `total_dose(dij_result, weights)` signature consistent (Task 6 defines, Task 7 consumes). CLI `--grid`/`--fluence`/`--plan-dose` consistent between the command (Task 7 Step 3) and its test (Task 7 Step 1).

**Residual implementation-time risk (honest):** the loader's CSV readers are validated against the synthetic fixture, which mirrors the real format per the verified `provided_code` reading. When real openkbp-opt data is first fetched, run `openbragg recompute` on one real patient (`--grid 128,128,128`) and confirm `max abs diff` is ~0; adjust a reader only if a real-file header quirk differs. This is a follow-on validation step, not a slice-1 blocker.
