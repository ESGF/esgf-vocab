"""
esgvoc remove <project>[@<name>]

Remove an installed database.
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


def _parse_project_name(spec: str) -> tuple[str, Optional[str]]:
    if "@" in spec:
        project_id, name = spec.split("@", 1)
        return project_id.strip(), name.strip()
    return spec.strip(), None


@app.command()
def remove(
    spec: str = typer.Argument(
        ...,
        help="Project[@name] to remove, e.g. 'cmip7@v2.0.0' or 'cmip7' (removes all).",
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

    project_id, name = _parse_project_name(spec)

    state = UserState.load()
    installed = state.get_installed(project_id)

    if not installed:
        console.print(f"[yellow]No versions installed for '{project_id}'.[/yellow]")
        raise typer.Exit(0)

    to_remove: list[str] = []
    if all_versions or name is None:
        to_remove = list(installed)
    elif name in installed:
        to_remove = [name]
    else:
        console.print(
            f"[red]'{name}' is not installed for '{project_id}'.[/red]\n"
            f"Installed: {', '.join(installed)}"
        )
        raise typer.Exit(1)

    if not yes:
        items = ", ".join(f"{project_id}@{n}" for n in to_remove)
        confirmed = typer.confirm(f"Remove {items}?")
        if not confirmed:
            raise typer.Abort()

    for n in to_remove:
        db = UserState.db_path(project_id, n)
        was_active = state.get_active(project_id) == n
        state.remove_installed(project_id, n)  # deletes file + clears pointer if active
        if db.exists():
            # remove_installed already deletes it, but check in case
            db.unlink(missing_ok=True)
        console.print(f"[dim]Deleted:[/dim] {db}")
        if was_active:
            console.print(
                f"[yellow]Note:[/yellow] '{project_id}@{n}' was the active version. "
                f"Run 'esgvoc use {project_id}@<name>' to set a new active version."
            )

    console.print(f"[green]Removed {len(to_remove)} version(s) for '{project_id}'.[/green]")
