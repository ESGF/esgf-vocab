"""
esgvoc remove <project>[@<version>]

Remove installed User Tier database(s).
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


def _parse_project_version(spec: str) -> tuple[str, Optional[str]]:
    if "@" in spec:
        project_id, version = spec.split("@", 1)
        return project_id.strip(), version.strip()
    return spec.strip(), None


@app.command()
def remove(
    spec: str = typer.Argument(
        ...,
        help="Project[@version] to remove, e.g. 'cmip7@v2.0.0' or 'cmip7' (removes all).",
    ),
    all_versions: bool = typer.Option(
        False, "--all", help="Remove all installed versions for the project.",
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation prompt.",
    ),
):
    """Remove an installed project database."""
    from esgvoc.core.service.user_state import UserState

    project_id, version = _parse_project_version(spec)

    state = UserState.load()
    installed = state.get_installed(project_id)

    if not installed:
        console.print(f"[yellow]No versions installed for '{project_id}'.[/yellow]")
        raise typer.Exit(0)

    to_remove: list[str] = []
    if all_versions or version is None:
        to_remove = list(installed)
    elif version in installed:
        to_remove = [version]
    else:
        console.print(
            f"[red]Version '{version}' is not installed for '{project_id}'.[/red]\n"
            f"Installed: {', '.join(installed)}"
        )
        raise typer.Exit(1)

    if not yes:
        items = ", ".join(f"{project_id}@{v}" for v in to_remove)
        confirmed = typer.confirm(f"Remove {items}?")
        if not confirmed:
            raise typer.Abort()

    active = state.get_active(project_id)
    for v in to_remove:
        db = UserState.db_path(project_id, v)
        if db.exists():
            db.unlink()
            console.print(f"[dim]Deleted:[/dim] {db}")
        state.remove_installed(project_id, v)
        if active == v:
            state.remove_active(project_id)
            console.print(
                f"[yellow]Note:[/yellow] '{project_id}@{v}' was the active version. "
                f"Run 'esgvoc use {project_id}@<version>' to set a new active version."
            )

    state.save()
    console.print(f"[green]Removed {len(to_remove)} version(s) for '{project_id}'.[/green]")
