"""Smoke tests for the ``openbragg`` CLI entry point.

These assert on externally observable CLI behavior (exit codes and printed
output) rather than on the Typer app's internals.
"""

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
