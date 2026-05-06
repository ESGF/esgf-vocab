"""
esgvoc offline  [REMOVED]

The per-component offline mode management (tied to the named config system)
has been eliminated. The system now works offline by default when no network
is available — no explicit offline mode toggle is needed.

To work offline, simply ensure you have activated a database:
  esgvoc use cmip7@v2.1.0    — activates a downloaded database (no network needed)
  esgvoc status               — shows active databases

Set ESGVOC_OFFLINE=true to prevent any network calls entirely.
"""

import typer
from rich.console import Console

app = typer.Typer()
console = Console()

_REMOVED_MSG = (
    "[red]'esgvoc offline' has been removed.[/red]\n"
    "Per-component offline mode no longer exists.\n\n"
    "Set [cyan]ESGVOC_OFFLINE=true[/cyan] to prevent all network calls, or\n"
    "activate a local database and network access is not needed:\n"
    "  [cyan]esgvoc use cmip7@v2.1.0[/cyan]"
)


@app.command()
def show():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)


@app.command()
def enable():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)


@app.command()
def disable():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)


@app.command()
def enable_all():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)


@app.command()
def disable_all():
    console.print(_REMOVED_MSG)
    raise typer.Exit(1)
