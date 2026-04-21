"""
esgvoc use <project>[@<name>]

Activate a version of a project.  Downloads from the registry automatically
if the DB is not already present locally.

Name resolution:
  project@v2.1.0         — registry version (auto-download if not present)
  project@latest         — latest stable    (auto-download)
  project@dev-latest     — latest pre-release (auto-download)
  project@my-experiment  — local build (must already exist via esgvoc admin install)

If no name is given, activates the newest installed version.
"""

from __future__ import annotations

import re
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer()
console = Console()

# Patterns that indicate a registry-sourced name (auto-download eligible)
_REGISTRY_PATTERNS = re.compile(
    r"^(v\d+\.\d+\.\d+.*|latest|dev-latest)$"
)


def _is_registry_name(name: str) -> bool:
    return bool(_REGISTRY_PATTERNS.match(name))


def _parse_project_name(spec: str) -> tuple[str, Optional[str]]:
    """Parse 'project[@name]' → (project_id, name or None)."""
    if "@" in spec:
        project_id, name = spec.split("@", 1)
        return project_id.strip(), name.strip()
    return spec.strip(), None


@app.command()
def use(
    spec: str = typer.Argument(
        ...,
        help=(
            "Project and version, e.g. 'cmip7@v2.1.0', 'cmip7@latest', "
            "or 'cmip7@my-experiment'. Omit name to activate newest installed."
        ),
    ),
    prerelease: bool = typer.Option(
        False, "--pre",
        help="When using 'latest', include pre-release versions.",
    ),
):
    """Activate a project version, downloading from the registry if needed."""
    from esgvoc.core.service.user_state import UserState
    from esgvoc.core.service.configuration.home import EsgvocHome

    project_id, name = _parse_project_name(spec)

    state = UserState.load()

    # ---------------------------------------------------------------
    # Case 1: no name given → activate newest already-installed version
    # ---------------------------------------------------------------
    if name is None:
        installed = state.get_installed(project_id)
        if not installed:
            console.print(
                f"[red]No versions installed for '{project_id}'.[/red]\n"
                f"Run: esgvoc use {project_id}@latest"
            )
            raise typer.Exit(1)
        name = installed[-1]
        console.print(f"[dim]Defaulting to newest installed: {name}[/dim]")

    # ---------------------------------------------------------------
    # Case 2: registry name → auto-download if not on disk
    # ---------------------------------------------------------------
    target = UserState.db_path(project_id, name)

    if not target.exists() and _is_registry_name(name):
        from esgvoc.core.db_fetcher import DBFetcher, EsgvocVersionNotFoundError
        from esgvoc.core.github_registry import known_project_ids

        known = known_project_ids()
        if project_id not in known:
            console.print(
                f"[red]Unknown project:[/red] '{project_id}'\n"
                f"Known projects: {', '.join(sorted(known))}"
            )
            raise typer.Exit(1)

        home = EsgvocHome.resolve()
        fetcher = DBFetcher(cache_dir=home.registry_cache_dir)

        requested = name
        if prerelease and requested == "latest":
            requested = "dev-latest"

        console.print(f"Fetching release info for [cyan]{project_id}@{requested}[/cyan]…")
        try:
            artifact = fetcher.get_artifact(project_id, version=requested)
        except EsgvocVersionNotFoundError as e:
            console.print(f"[red]Version not found:[/red] {e}")
            raise typer.Exit(3)
        except Exception as e:
            console.print(f"[red]Failed to fetch release info:[/red] {e}")
            raise typer.Exit(2)

        # Use the resolved concrete version as the name on disk
        # (e.g. "latest" resolves to "v2.1.0")
        name = artifact.version
        target = UserState.db_path(project_id, name)

        # Check if already on disk with matching checksum
        if target.exists() and artifact.checksum_sha256:
            import hashlib
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            if digest == artifact.checksum_sha256:
                console.print(f"[dim]{project_id}@{name} already on disk, checksum matches.[/dim]")
                _activate(state, project_id, name, "registry", artifact.checksum_sha256)
                return

        mb = (artifact.size_bytes or 0) / 1_048_576
        console.print(f"Downloading [cyan]{project_id}@{name}[/cyan] ({mb:.1f} MB)…")
        try:
            fetcher.download_db(artifact, target)
        except Exception as e:
            console.print(f"[red]Download failed:[/red] {e}")
            raise typer.Exit(2)

        _activate(state, project_id, name, "registry", artifact.checksum_sha256)
        return

    # ---------------------------------------------------------------
    # Case 3: local name or already-downloaded registry version
    # ---------------------------------------------------------------
    if not target.exists():
        if _is_registry_name(name):
            console.print(
                f"[red]DB file missing:[/red] {target}\n"
                f"Re-run: esgvoc use {project_id}@{name}"
            )
        else:
            console.print(
                f"[red]'{name}' is not installed for '{project_id}'.[/red]\n"
                f"Build and install it first: esgvoc admin build … && esgvoc admin install {project_id} <path> --name {name}"
            )
        raise typer.Exit(1)

    source = "registry" if _is_registry_name(name) else "local"
    _activate(state, project_id, name, source, checksum=None)


def _activate(
    state,
    project_id: str,
    name: str,
    source: str,
    checksum: Optional[str],
) -> None:
    """Write the pointer file and report success."""
    state.set_active(project_id, name, source=source, checksum=checksum)
    console.print(f"[green]Active:[/green] {project_id} → {name}")
