"""Behavioral test for scripts/make_openkbp_sample.py.

Runs the curation script (black box) against a synthetic openkbp-opt dataset and
asserts the produced sample is itself a valid, loadable mini-dataset.
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
from conftest import write_synthetic_openkbp_opt_case

from openbragg.io.openkbp_opt import load_case, resolve_plan_paths, verify_dataset

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "make_openkbp_sample.py"


def test_curated_sample_is_loadable(tmp_path: Path) -> None:
    source = tmp_path / "open-kbp-opt-data"
    sc = write_synthetic_openkbp_opt_case(source)
    dest = tmp_path / "sample_data" / "openkbp_opt"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source",
            str(source),
            "--dest",
            str(dest),
            "--num",
            "3",  # synthetic tree has 1 patient; script takes what exists
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "sample recompute-ready: True" in result.stdout

    # Full reference-plans files carried over, including dij.npz and the CT.
    assert (dest / "reference-plans" / "pt_test" / "dij.npz").is_file()
    assert (dest / "reference-plans" / "pt_test" / "ct.csv").is_file()
    assert (dest / "README.md").is_file()
    assert "CC BY 4.0" in (dest / "README.md").read_text()

    # The sample is a valid dataset in its own right and loads end-to-end.
    assert verify_dataset(dest).recompute_ready is True
    fluence, dose = resolve_plan_paths(dest, "pt_test")
    case = load_case(
        dest / "reference-plans" / "pt_test",
        fluence,
        dose,
        grid_shape=sc.grid_shape,
    )
    assert case.identifier == "pt_test"
    np.testing.assert_allclose(case.plan.weights, sc.weights)


def test_curation_requires_dataset_root(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--source", str(tmp_path / "missing")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "not a dataset root" in result.stderr
