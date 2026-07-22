"""Smoke tests for the ``openbragg`` CLI entry point.

These assert on externally observable CLI behavior (exit codes and printed
output) rather than on the Typer app's internals.
"""

from conftest import SyntheticCase
from typer.testing import CliRunner

from openbragg import __version__
from openbragg.cli import app

runner = CliRunner()


def test_help_exits_zero() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "openbragg" in result.output.lower()


def test_version_prints_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_recompute_cli(synthetic_case: SyntheticCase) -> None:
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
    assert "recomputed dose:" in result.output
    assert "max abs diff vs plan-dose" in result.output


def test_recompute_cli_rejects_non_integer_grid(synthetic_case: SyntheticCase) -> None:
    sc = synthetic_case
    result = runner.invoke(
        app,
        [
            "recompute",
            str(sc.patient_dir),
            "--fluence",
            str(sc.fluence_path),
            "--grid",
            "1,2,x",
        ],
    )
    assert result.exit_code != 0
