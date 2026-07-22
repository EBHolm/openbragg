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

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingTypeStubs=false, reportOptionalSubscript=false


@dataclass(frozen=True, eq=False)
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
