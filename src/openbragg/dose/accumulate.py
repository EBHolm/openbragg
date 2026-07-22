"""Total dose accumulation: dose = Dij · w on the calculation grid (Gy)."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from openbragg.engine.base import DijResult

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportMissingTypeStubs=false, reportOptionalSubscript=false


def total_dose(
    dij_result: DijResult, weights: npt.NDArray[np.float64]
) -> npt.NDArray[np.float64]:
    dij = dij_result.dij
    if dij.shape[1] != weights.shape[0]:
        raise ValueError(
            f"Dij has {dij.shape[1]} beamlet columns but w has {weights.shape[0]} entries"
        )
    flat = dij @ weights
    return np.asarray(flat, dtype=np.float64).reshape(dij_result.grid_shape)
