"""Command-line interface for FamilyDB."""

from __future__ import annotations

import typer

from familydb import __version__
from familydb.config import load_settings

app = typer.Typer(
    name="familydb",
    help="FamilyDB: a private family planning assistant.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"familydb {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show the version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """FamilyDB command-line interface."""


@app.command()
def config() -> None:
    """Print the resolved settings with secrets masked."""
    settings = load_settings()
    for key, value in settings.masked().items():
        typer.echo(f"{key}={value}")
