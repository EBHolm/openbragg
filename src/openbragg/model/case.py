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
