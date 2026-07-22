"""Command-line entry point for OpenBragg.

Exposes a Typer ``app`` wired to the ``openbragg`` console script. Phase-1
slices register their subcommands onto this ``app``.
"""

from pathlib import Path

import numpy as np
import typer

from openbragg import __version__
from openbragg.dose.accumulate import total_dose
from openbragg.engine.openkbp_opt import OpenKBPOptEngine
from openbragg.io.openkbp_opt import load_case

app = typer.Typer(
    name="openbragg",
    help="OpenBragg — a proton-focused, open-source treatment planning system.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"openbragg {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the OpenBragg version and exit.",
    ),
) -> None:
    """OpenBragg command-line interface."""


@app.command()
def recompute(
    patient_dir: Path = typer.Argument(
        ..., help="openkbp-opt reference-plans/pt_* directory (contains dij.npz)."
    ),
    fluence: Path = typer.Option(
        ..., "--fluence", help="plan-fluence CSV: the beamlet weight vector w."
    ),
    plan_dose: Path | None = typer.Option(
        None, "--plan-dose", help="plan-dose CSV to compare the recompute against."
    ),
    grid: str = typer.Option(
        "128,128,128",
        "--grid",
        help="Grid shape as 'nx,ny,nz' (openkbp-opt is 128,128,128).",
    ),
) -> None:
    """Recompute dose = Dij·w for an openkbp-opt case and report agreement."""
    parts = tuple(int(x) for x in grid.split(","))
    if len(parts) != 3:
        raise typer.BadParameter("grid must be 'nx,ny,nz'")
    grid_shape = (parts[0], parts[1], parts[2])
    case = load_case(patient_dir, fluence, plan_dose, grid_shape=grid_shape)
    engine = OpenKBPOptEngine(patient_dir, grid_shape=grid_shape)
    dose = total_dose(engine.compute_dij(case), case.plan.weights)
    typer.echo(f"recomputed dose: shape={dose.shape} max={float(dose.max()):.4g} Gy")
    if case.reference_dose is not None:
        max_abs = float(np.max(np.abs(dose - case.reference_dose.array)))
        typer.echo(f"max abs diff vs plan-dose: {max_abs:.3e} Gy")
