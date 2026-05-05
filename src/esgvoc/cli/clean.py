"""
esgvoc clean  [REMOVED]

The dev-tier config system (named configs, cloned repos) has been eliminated.
Use 'esgvoc remove' to delete installed databases instead:

  esgvoc remove cmip7@v2.0.0        — remove a specific version
  esgvoc remove cmip7 --all         — remove all versions of a project
"""

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def repos():
    """[Removed] The dev-tier config system has been eliminated."""
    console.print(
        "[red]'esgvoc clean repos' has been removed.[/red]\n"
        "The dev-tier config system no longer exists.\n"
        "Use [cyan]esgvoc remove[/cyan] to manage installed databases."
    )
    raise typer.Exit(1)


@app.command()
def dbs():
    """[Removed] Use 'esgvoc remove' to delete installed databases."""
    console.print(
        "[red]'esgvoc clean dbs' has been removed.[/red]\n"
        "Use [cyan]esgvoc remove <project>[@<name>][/cyan] instead.\n"
        "Example: esgvoc remove cmip7@v2.0.0"
    )
    raise typer.Exit(1)


@app.command(name="all")
def clean_all():
    """[Removed] Use 'esgvoc remove' to delete installed databases."""
    console.print(
        "[red]'esgvoc clean all' has been removed.[/red]\nUse [cyan]esgvoc remove <project> --all[/cyan] instead."
    )
    raise typer.Exit(1)


@app.command()
def component():
    """[Removed] The dev-tier config system has been eliminated."""
    console.print("[red]'esgvoc clean component' has been removed.[/red]\nThe dev-tier config system no longer exists.")
    raise typer.Exit(1)
