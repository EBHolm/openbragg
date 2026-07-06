"""Command-line entry point for OpenBragg.

Exposes a Typer ``app`` wired to the ``openbragg`` console script. Phase-1
slices (ingest, recompute, export) register their subcommands onto this ``app``;
for now it carries only ``--version`` and the built-in ``--help``.
"""

import typer

from openbragg import __version__

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
