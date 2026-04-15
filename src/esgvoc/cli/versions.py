"""
esgvoc list [project]

List installed (and optionally available) versions for User Tier projects.
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


@app.command(name="list")
def list_versions(
    project_id: Optional[str] = typer.Argument(
        None,
        help="Project to list (e.g. 'cmip7'). If omitted, lists all installed projects.",
    ),
    available: bool = typer.Option(
        False, "--available", "-a",
        help="Also show versions available for download (requires network).",
    ),
    prerelease: bool = typer.Option(
        False, "--pre", help="Include pre-release versions when listing available.",
    ),
):
    """List installed (and optionally available) versions."""
    from esgvoc.core.service.user_state import UserState

    state = UserState.load()

    projects = [project_id] if project_id else state.all_project_ids()

    if not projects:
        console.print("[dim]No projects installed. Run: esgvoc install <project>[/dim]")
        raise typer.Exit(0)

    for pid in projects:
        installed = state.get_installed(pid)
        active = state.get_active(pid)

        table = Table(title=f"[cyan]{pid}[/cyan]", show_header=True)
        table.add_column("Version")
        table.add_column("Status")
        table.add_column("DB Path")

        for v in installed:
            db = UserState.db_path(pid, v)
            status = "[bold green]active[/bold green]" if v == active else "installed"
            exists = "✓" if db.exists() else "[red]missing[/red]"
            table.add_row(v, status, f"{exists}  {db}")

        if available:
            try:
                from esgvoc.core.db_fetcher import DBFetcher
                from esgvoc.core.service.configuration.home import EsgvocHome
                fetcher = DBFetcher(cache_dir=EsgvocHome.resolve().user_cache_dir)
                remote_versions = fetcher.list_versions(pid, include_prerelease=prerelease)
                for v in remote_versions:
                    if v not in installed:
                        table.add_row(v, "[dim]available[/dim]", "—")
            except Exception as e:
                console.print(f"[yellow]Could not fetch remote versions: {e}[/yellow]")

        console.print(table)
