"""
esgvoc update [project]

Download and activate the latest stable version of a project.
Use --check to only report without downloading.
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def update(
    project_id: Optional[str] = typer.Argument(
        None,
        help="Project to update (e.g. 'cmip7'). If omitted, updates all installed projects.",
    ),
    check: bool = typer.Option(
        False, "--check", help="Only report available updates, do not download.",
    ),
    prerelease: bool = typer.Option(
        False, "--pre", help="Include pre-release versions.",
    ),
    no_activate: bool = typer.Option(
        False, "--no-activate",
        help="Download but do not switch the active version.",
    ),
):
    """Update installed project(s) to the latest available version."""
    from esgvoc.core.db_fetcher import DBFetcher, EsgvocVersionNotFoundError
    from esgvoc.core.service.user_state import UserState

    fetcher = DBFetcher()
    state = UserState.load()

    projects = [project_id] if project_id else state.all_project_ids()
    if not projects:
        console.print("[dim]No projects installed.[/dim]")
        raise typer.Exit(0)

    any_updated = False
    for pid in projects:
        try:
            artifact = fetcher.get_artifact(pid, version="latest" if not prerelease else "dev-latest")
        except EsgvocVersionNotFoundError as e:
            console.print(f"[yellow]{pid}:[/yellow] {e}")
            continue
        except Exception as e:
            console.print(f"[red]{pid}: Failed to fetch releases:[/red] {e}")
            continue

        active = state.get_active(pid)
        latest = artifact.version

        if active == latest:
            console.print(f"[dim]{pid}:[/dim] already at {latest}")
            continue

        if check:
            console.print(f"[cyan]{pid}:[/cyan] {active or 'none'} → {latest} [dim](use without --check to update)[/dim]")
            continue

        # Download
        target = UserState.db_path(pid, artifact.version)
        if not target.exists():
            console.print(f"Downloading {pid}@{latest}…")
            try:
                fetcher.download_db(artifact, target)
            except Exception as e:
                console.print(f"[red]Download failed:[/red] {e}")
                continue
        else:
            console.print(f"[dim]{pid}@{latest} already on disk[/dim]")

        state.add_installed(pid, artifact.version)
        if not no_activate:
            state.set_active(pid, artifact.version, source="registry",
                             checksum=artifact.checksum_sha256)
            console.print(f"[green]{pid}:[/green] {active or 'none'} → {artifact.version} (active)")
        else:
            console.print(f"[green]{pid}:[/green] {artifact.version} installed (not activated)")

        any_updated = True

    if any_updated:
        state.save()
