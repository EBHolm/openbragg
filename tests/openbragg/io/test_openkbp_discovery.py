"""Tests for openkbp-opt dataset discovery helpers.

Discovery is what the curation/fetch tooling relies on to walk a downloaded
``open-kbp-opt-data`` tree, so it is exercised against the synthetic tree in
conftest (nested ``set_*`` layout) and a flat README-shaped tree.
"""

from pathlib import Path

import pytest
from conftest import SyntheticCase

from openbragg.io.openkbp_opt import (
    find_patient_dirs,
    resolve_plan_paths,
    verify_dataset,
)


def test_find_patient_dirs_lists_reference_plans(synthetic_case: SyntheticCase) -> None:
    root = synthetic_case.patient_dir.parents[1]
    dirs = find_patient_dirs(root)
    assert [d.name for d in dirs] == ["pt_test"]


def test_resolve_plan_paths_matches_builder(synthetic_case: SyntheticCase) -> None:
    root = synthetic_case.patient_dir.parents[1]
    fluence, dose = resolve_plan_paths(root, "pt_test")
    assert fluence == synthetic_case.fluence_path
    assert dose == synthetic_case.dose_path


def test_resolve_plan_paths_flat_layout(tmp_path: Path) -> None:
    # Real README layout: paper-plans/<model>/plan-fluence/pt_X.csv (no set_* nesting).
    fluence_dir = tmp_path / "paper-plans" / "MeanAbs" / "plan-fluence"
    dose_dir = tmp_path / "paper-plans" / "MeanAbs" / "plan-dose"
    fluence_dir.mkdir(parents=True)
    dose_dir.mkdir(parents=True)
    (fluence_dir / "pt_9.csv").write_text(",data\n0,1.0\n")
    (dose_dir / "pt_9.csv").write_text(",data\n0,1.0\n")
    fluence, dose = resolve_plan_paths(tmp_path, "pt_9")
    assert fluence == fluence_dir / "pt_9.csv"
    assert dose == dose_dir / "pt_9.csv"


def test_resolve_plan_paths_missing_raises(synthetic_case: SyntheticCase) -> None:
    root = synthetic_case.patient_dir.parents[1]
    with pytest.raises(FileNotFoundError):
        resolve_plan_paths(root, "pt_absent")


def test_verify_dataset_reports_complete_tree(synthetic_case: SyntheticCase) -> None:
    root = synthetic_case.patient_dir.parents[1]
    report = verify_dataset(root)
    assert report.patient_ids == ("pt_test",)
    assert report.has_plan_fluence is True
    assert report.recompute_ready is True


def test_verify_dataset_reports_missing_optional_bundle(tmp_path: Path) -> None:
    # Only the base bundle extracted: patients present, no paper-plans/plan-fluence.
    (tmp_path / "reference-plans" / "pt_1").mkdir(parents=True)
    report = verify_dataset(tmp_path)
    assert report.patient_ids == ("pt_1",)
    assert report.has_plan_fluence is False
    assert report.recompute_ready is False
