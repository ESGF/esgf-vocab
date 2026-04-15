"""
esgvoc use <project>[@<version>]

Switch the active version of a project in the User Tier.
The project must already be installed.
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


def _parse_project_version(spec: str) -> tuple[str, Optional[str]]:
    """Parse 'project[@version]' → (project_id, version or None)."""
    if "@" in spec:
        project_id, version = spec.split("@", 1)
        return project_id.strip(), version.strip()
    return spec.strip(), None


@app.command()
def use(
    spec: str = typer.Argument(
        ...,
        help="Project and version, e.g. 'cmip7@v2.1.0' or 'cmip7' (switches to latest installed).",
    ),
):
    """Switch the active version for a project."""
    from esgvoc.core.service.user_state import UserState

    project_id, version = _parse_project_version(spec)

    state = UserState.load()
    installed = state.get_installed(project_id)

    if not installed:
        console.print(
            f"[red]No versions installed for '{project_id}'.[/red] "
            f"Run: esgvoc install {project_id}"
        )
        raise typer.Exit(1)

    if version is None:
        # Default to the newest installed
        version = installed[-1]

    if version not in installed:
        console.print(
            f"[red]Version '{version}' is not installed for '{project_id}'.[/red]\n"
            f"Installed: {', '.join(installed)}"
        )
        raise typer.Exit(1)

    db_path = UserState.db_path(project_id, version)
    if not db_path.exists():
        console.print(
            f"[red]DB file missing:[/red] {db_path}\n"
            f"Re-install with: esgvoc install {project_id}@{version}"
        )
        raise typer.Exit(1)

    state.set_active(project_id, version)
    state.save()
    console.print(f"[green]Active:[/green] {project_id} → {version}")
