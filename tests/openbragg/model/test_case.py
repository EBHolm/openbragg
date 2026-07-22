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
