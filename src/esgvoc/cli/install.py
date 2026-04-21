"""
esgvoc install  [REMOVED]

This command has been removed. Use 'esgvoc use' instead:

  esgvoc use cmip7@latest       — download and activate latest version
  esgvoc use cmip7@v2.1.0       — download and activate a specific version

To install a locally built database use:
  esgvoc admin install cmip7 ./cmip7.db [--name my-experiment]
"""

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def install():
    """[Removed] Use 'esgvoc use <project>@<version>' instead."""
    console.print(
        "[red]'esgvoc install' has been removed.[/red]\n\n"
        "Use [cyan]esgvoc use <project>@<version>[/cyan] to download and activate a database.\n"
        "Examples:\n"
        "  esgvoc use cmip7@latest\n"
        "  esgvoc use cmip7@v2.1.0\n\n"
        "To install a locally built DB:\n"
        "  esgvoc admin install cmip7 ./cmip7.db --name my-experiment"
    )
    raise typer.Exit(1)
