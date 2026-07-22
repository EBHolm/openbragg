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

# pyright: reportOptionalSubscript=false


class OpenKBPOptEngine:
    def __init__(
        self, patient_dir: str | Path, grid_shape: GridShape = DEFAULT_GRID_SHAPE
    ) -> None:
        self._patient_dir = Path(patient_dir)
        self._grid_shape = grid_shape

    def compute_dij(self, case: Case) -> DijResult:
        if case.image.shape != self._grid_shape:
            raise ValueError(
                f"case grid {case.image.shape} != engine grid {self._grid_shape}"
            )
        dij = load_dij(self._patient_dir, self._grid_shape)
        if dij.shape[1] != case.plan.weights.shape[0]:
            raise ValueError(
                f"Dij has {dij.shape[1]} beamlet columns but plan has {case.plan.weights.shape[0]} weights"
            )
        return DijResult(dij=dij, grid_shape=self._grid_shape, units="Gy")
