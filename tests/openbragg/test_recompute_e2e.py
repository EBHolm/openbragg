"""End-to-end tracer bullet: load -> seam -> Dij·w reproduces plan-dose."""

import numpy as np
from conftest import SyntheticCase

from openbragg.dose.accumulate import total_dose
from openbragg.engine.openkbp_opt import OpenKBPOptEngine
from openbragg.io.openkbp_opt import load_case


def test_recompute_reproduces_plan_dose(synthetic_case: SyntheticCase) -> None:
    sc = synthetic_case
    case = load_case(
        sc.patient_dir, sc.fluence_path, sc.dose_path, grid_shape=sc.grid_shape
    )
    engine = OpenKBPOptEngine(sc.patient_dir, grid_shape=sc.grid_shape)
    dose = total_dose(engine.compute_dij(case), case.plan.weights)
    assert dose.shape == sc.grid_shape
    assert case.reference_dose is not None
    np.testing.assert_allclose(dose, case.reference_dose.array, rtol=1e-9, atol=1e-9)
    assert float(np.max(np.abs(dose - case.reference_dose.array))) < 1e-6
