"""
esgvoc install [project[@version]]

Two modes:
  User Tier  — esgvoc install cmip7[@v2.1.0]
               Downloads a pre-built DB artifact from GitHub Releases.

  Dev Tier   — esgvoc install  (no arguments)
               Existing source-based install: clones repos and builds DBs locally.
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
def install(
    spec: Optional[str] = typer.Argument(
        None,
        help=(
            "User Tier: project[@version] to download, e.g. 'cmip7' or 'cmip7@v2.1.0'. "
            "Omit for Dev Tier install (clone repos + build DBs)."
        ),
    ),
    no_activate: bool = typer.Option(
        False, "--no-activate",
        help="User Tier: download but do not set as active version.",
    ),
    prerelease: bool = typer.Option(
        False, "--pre",
        help="User Tier: allow pre-release versions.",
    ),
    fail_on_missing_links: bool = typer.Option(
        False, "--fail-on-missing-links",
        help="Dev Tier: exit with code -1 if any @id references cannot be resolved.",
    ),
):
    """
    Install a project database.

    \b
    User Tier (download pre-built DB):
      esgvoc install cmip7            # latest stable
      esgvoc install cmip7@v2.1.0    # specific version
      esgvoc install cmip7 --pre      # include pre-releases

    \b
    Dev Tier (clone repos + build DBs locally):
      esgvoc install                  # uses current config
    """
    if spec is not None:
        _install_user_tier(spec, no_activate=no_activate, prerelease=prerelease)
    else:
        _install_dev_tier(fail_on_missing_links=fail_on_missing_links)


def _install_user_tier(spec: str, *, no_activate: bool, prerelease: bool) -> None:
    from esgvoc.core.db_fetcher import DBFetcher, EsgvocVersionNotFoundError
    from esgvoc.core.service.user_state import UserState
    from esgvoc.core.service.configuration.home import EsgvocHome
    from esgvoc.core.project_registry import known_project_ids

    project_id, version = _parse_project_version(spec)

    known = known_project_ids()
    if project_id not in known:
        console.print(
            f"[red]Unknown project:[/red] '{project_id}'\n"
            f"Known projects: {', '.join(sorted(known))}"
        )
        raise typer.Exit(1)

    home = EsgvocHome.resolve()
    fetcher = DBFetcher(cache_dir=home.user_cache_dir)

    requested = version or "latest"
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

    state = UserState.load()
    target = UserState.db_path(project_id, artifact.version)

    if target.exists() and artifact.checksum_sha256:
        import hashlib
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest == artifact.checksum_sha256:
            console.print(f"[dim]{project_id}@{artifact.version} already on disk, checksum matches.[/dim]")
            if not no_activate:
                state.set_active(project_id, artifact.version)
            state.add_installed(project_id, artifact.version)
            state.save()
            console.print(f"[green]Active:[/green] {project_id} → {artifact.version}")
            return

    mb = (artifact.size_bytes or 0) / 1_048_576
    console.print(
        f"Downloading [cyan]{project_id}@{artifact.version}[/cyan] "
        f"({mb:.1f} MB)…"
    )
    try:
        fetcher.download_db(artifact, target)
    except Exception as e:
        console.print(f"[red]Download failed:[/red] {e}")
        raise typer.Exit(2)

    state.add_installed(project_id, artifact.version)
    if not no_activate:
        state.set_active(project_id, artifact.version)
        console.print(f"[green]Installed and activated:[/green] {project_id} → {artifact.version}")
    else:
        console.print(f"[green]Installed:[/green] {project_id}@{artifact.version} (not activated)")

    state.save()


def _install_dev_tier(*, fail_on_missing_links: bool) -> None:
    from esgvoc.api import install as api_install
    from esgvoc.core.service import current_state

    try:
        typer.echo("Initialized default configuration")

        offline_components = []
        if current_state.universe.offline_mode:
            offline_components.append("universe")
        for project_name, project in current_state.projects.items():
            if project.offline_mode:
                offline_components.append(project_name)

        if offline_components:
            typer.echo(
                f"Note: The following components are in offline mode: {', '.join(offline_components)}"
            )
            typer.echo("Only local repositories and databases will be used.")

        result = api_install(fail_on_missing_links=fail_on_missing_links)
        current_state.get_state_summary()

        console.print("\nInstallation completed. Final status:")
        console.print(current_state.table())

        if result != 0:
            raise typer.Exit(result)

    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"Error during installation: {str(e)}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
