"""
esgvoc config  [REMOVED]

The named dev-environment config system (TOML config files, active_config,
per-config state) has been eliminated. There is no longer a multi-tier
configuration concept in esgvoc.

Database management is now done directly:
  esgvoc use cmip7@latest          — activate/download a version
  esgvoc status                     — show installed versions
  esgvoc remove cmip7@v2.0.0       — remove a version
  esgvoc list [project]             — list versions
"""

import typer
from rich.console import Console

app = typer.Typer()
console = Console()

_REMOVED_MSG = (
    "[red]'esgvoc config' has been removed.[/red]\n"
    "The named config system no longer exists.\n\n"
    "Manage databases with:\n"
    "  [cyan]esgvoc use <project>@<version>[/cyan]   — activate/download\n"
    "  [cyan]esgvoc status[/cyan]                     — show installed versions\n"
    "  [cyan]esgvoc remove <project>[@<name>][/cyan]  — remove a version"
)


@app.command()
def list():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)


@app.command()
def show():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)


@app.command()
def switch():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)


@app.command()
def create():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)


@app.command()
def remove():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)


@app.command()
def edit():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)


@app.command(name="set")
def set_config():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)


@app.command()
def add():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)


@app.command()
def rm():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)


@app.command()
def init():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)
