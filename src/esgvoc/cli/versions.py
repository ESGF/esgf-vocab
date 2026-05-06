"""
esgvoc list / list-remote commands.

- list          : installed versions (optionally with remote)
- list-remote   : full registry metadata for available versions
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()

_KNOWN_PROJECTS = [
    "universe", "cmip7", "cmip6", "cmip6plus",
    "input4mips", "obs4ref", "cordex-cmip6", "cordex-cmip5", "emd",
]


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
        console.print("[dim]No projects installed. Run: esgvoc use <project>@latest[/dim]")
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
                fetcher = DBFetcher()
                remote_versions = fetcher.list_versions(pid, include_prerelease=prerelease)
                for v in remote_versions:
                    if v not in installed:
                        table.add_row(v, "[dim]available[/dim]", "—")
            except Exception as e:
                console.print(f"[yellow]Could not fetch remote versions: {e}[/yellow]")

        console.print(table)


@app.command(name="list-remote")
def list_remote(
    project_id: Optional[str] = typer.Argument(
        None,
        help="Project to inspect (e.g. 'cmip7'). If omitted, lists all known projects.",
    ),
    prerelease: bool = typer.Option(
        False, "--pre", help="Include pre-release / dev-latest versions.",
    ),
):
    """Show all versions available in the registry with full metadata."""
    import esgvoc
    from esgvoc.core.db_fetcher import DBFetcher, EsgvocNetworkError, EsgvocVersionNotFoundError
    from esgvoc.core.service.user_state import UserState

    fetcher = DBFetcher()
    state = UserState.load()
    installed_esgvoc = getattr(esgvoc, "__version__", None)

    projects = [project_id] if project_id else _KNOWN_PROJECTS

    for pid in projects:
        try:
            artifacts = fetcher._fetch_releases(pid)
        except EsgvocVersionNotFoundError:
            console.print(f"[dim]{pid}: no registry index found[/dim]")
            continue
        except EsgvocNetworkError as e:
            console.print(f"[red]{pid}: network error — {e}[/red]")
            continue

        if not prerelease:
            artifacts = [a for a in artifacts if not a.is_prerelease]

        if not artifacts:
            console.print(f"[dim]{pid}: no releases found[/dim]")
            continue

        installed = set(state.get_installed(pid))
        active = state.get_active(pid)

        table = Table(title=f"[cyan]{pid}[/cyan]", show_header=True, header_style="bold")
        table.add_column("Version")
        table.add_column("Published", style="dim")
        table.add_column("Size")
        table.add_column("Universe")
        table.add_column("Min esgvoc")
        table.add_column("Compat")
        table.add_column("Local")

        for a in artifacts:
            published = a.published_at.strftime("%Y-%m-%d") if a.published_at else "—"
            size = f"{a.size_bytes / 1_048_576:.1f} MB" if a.size_bytes else "—"
            universe = a.universe_version or "—"
            min_v = a.esgvoc_min_version or "—"

            compat, _ = fetcher.check_compatibility(a)
            compat_cell = "[green]✓[/green]" if compat else "[red]✗[/red]"

            if a.version == active:
                local = "[bold green]active[/bold green]"
            elif a.version in installed:
                local = "installed"
            else:
                local = "[dim]—[/dim]"

            table.add_row(a.version, published, size, universe, min_v, compat_cell, local)

        if installed_esgvoc:
            console.print(f"[dim]Compatibility checked against installed esgvoc {installed_esgvoc}[/dim]")
        console.print(table)
