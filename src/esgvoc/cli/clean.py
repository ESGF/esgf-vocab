"""
Clean command for managing local repositories and databases.

This module provides CLI commands for cleaning up local data,
including repositories and databases. Useful for resetting state
or switching between offline/online modes.
"""

import typer
import shutil
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm
from typing import Optional, List

from esgvoc.core.service import config_manager


app = typer.Typer()
console = Console()


def _clean_repositories(settings, config_name: Optional[str] = None):
    """Clean all local repositories for the given settings."""
    cleaned_repos = []

    # Clean universe repository
    universe_path = settings.universe.get_absolute_local_path()
    if universe_path and Path(universe_path).exists():
        shutil.rmtree(universe_path)
        cleaned_repos.append(f"Universe repository: {universe_path}")

    # Clean project repositories
    for project_name, project in settings.projects.items():
        project_path = project.get_absolute_local_path()
        if project_path and Path(project_path).exists():
            shutil.rmtree(project_path)
            cleaned_repos.append(f"Project '{project_name}' repository: {project_path}")

    return cleaned_repos


def _clean_databases(settings, config_name: Optional[str] = None):
    """Clean all local databases for the given settings."""
    cleaned_dbs = []

    # Clean universe database
    universe_db_path = settings.universe.get_absolute_db_path()
    if universe_db_path and Path(universe_db_path).exists():
        Path(universe_db_path).unlink()
        cleaned_dbs.append(f"Universe database: {universe_db_path}")

    # Clean project databases
    for project_name, project in settings.projects.items():
        project_db_path = project.get_absolute_db_path()
        if project_db_path and Path(project_db_path).exists():
            Path(project_db_path).unlink()
            cleaned_dbs.append(f"Project '{project_name}' database: {project_db_path}")

    return cleaned_dbs


@app.command()
def repos(
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration name to use. Uses active configuration if not specified."
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt"
    )
):
    """Clean all local repositories."""
    try:
        if config:
            settings = config_manager.get_config(config)
            config_display = f"configuration '{config}'"
        else:
            settings = config_manager.get_active_config()
            config_display = f"active configuration"

        # Ask for confirmation unless --force is used
        if not force:
            console.print(f"[yellow]This will delete all local repositories for {config_display}.[/yellow]")
            console.print("[yellow]Any local changes will be lost.[/yellow]")
            if not Confirm.ask("Are you sure you want to continue?"):
                console.print("[blue]Operation cancelled.[/blue]")
                return

        # Clean repositories
        cleaned_repos = _clean_repositories(settings, config)

        if cleaned_repos:
            console.print(f"[green]✓ Cleaned {len(cleaned_repos)} repositories:[/green]")
            for repo in cleaned_repos:
                console.print(f"  - {repo}")
        else:
            console.print("[yellow]No repositories found to clean.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def dbs(
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration name to use. Uses active configuration if not specified."
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt"
    )
):
    """Clean all local databases."""
    try:
        if config:
            settings = config_manager.get_config(config)
            config_display = f"configuration '{config}'"
        else:
            settings = config_manager.get_active_config()
            config_display = f"active configuration"

        # Ask for confirmation unless --force is used
        if not force:
            console.print(f"[yellow]This will delete all local databases for {config_display}.[/yellow]")
            console.print("[yellow]All cached data will be lost.[/yellow]")
            if not Confirm.ask("Are you sure you want to continue?"):
                console.print("[blue]Operation cancelled.[/blue]")
                return

        # Clean databases
        cleaned_dbs = _clean_databases(settings, config)

        if cleaned_dbs:
            console.print(f"[green]✓ Cleaned {len(cleaned_dbs)} databases:[/green]")
            for db in cleaned_dbs:
                console.print(f"  - {db}")
        else:
            console.print("[yellow]No databases found to clean.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def all(
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration name to use. Uses active configuration if not specified."
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt"
    )
):
    """Clean all local repositories and databases."""
    try:
        if config:
            settings = config_manager.get_config(config)
            config_display = f"configuration '{config}'"
        else:
            settings = config_manager.get_active_config()
            config_display = f"active configuration"

        # Ask for confirmation unless --force is used
        if not force:
            console.print(f"[yellow]This will delete all local repositories and databases for {config_display}.[/yellow]")
            console.print("[yellow]Any local changes and cached data will be lost.[/yellow]")
            if not Confirm.ask("Are you sure you want to continue?"):
                console.print("[blue]Operation cancelled.[/blue]")
                return

        # Clean both repositories and databases
        cleaned_repos = _clean_repositories(settings, config)
        cleaned_dbs = _clean_databases(settings, config)

        total_cleaned = len(cleaned_repos) + len(cleaned_dbs)

        if total_cleaned > 0:
            console.print(f"[green]✓ Cleaned {total_cleaned} items:[/green]")

            if cleaned_repos:
                console.print(f"[green]  Repositories ({len(cleaned_repos)}):[/green]")
                for repo in cleaned_repos:
                    console.print(f"    - {repo}")

            if cleaned_dbs:
                console.print(f"[green]  Databases ({len(cleaned_dbs)}):[/green]")
                for db in cleaned_dbs:
                    console.print(f"    - {db}")
        else:
            console.print("[yellow]No repositories or databases found to clean.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def component(
    component_name: str = typer.Argument(
        ...,
        help="Component to clean (universe or project name)"
    ),
    what: str = typer.Option(
        "all",
        "--what",
        "-w",
        help="What to clean: 'repos', 'dbs', or 'all' (default)"
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration name to use. Uses active configuration if not specified."
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt"
    )
):
    """Clean repositories and/or databases for a specific component."""
    if what not in ["repos", "dbs", "all"]:
        console.print(f"[red]Invalid value for --what: {what}. Must be 'repos', 'dbs', or 'all'[/red]")
        raise typer.Exit(1)

    try:
        if config:
            settings = config_manager.get_config(config)
            config_display = f"configuration '{config}'"
        else:
            settings = config_manager.get_active_config()
            config_display = f"active configuration"

        # Validate component exists
        if component_name == "universe":
            component = settings.universe
        elif component_name in settings.projects:
            component = settings.projects[component_name]
        else:
            console.print(f"[red]Component '{component_name}' not found in {config_display}[/red]")
            raise typer.Exit(1)

        # Ask for confirmation unless --force is used
        if not force:
            what_desc = {"repos": "repositories", "dbs": "databases", "all": "repositories and databases"}[what]
            console.print(f"[yellow]This will delete {what_desc} for component '{component_name}' in {config_display}.[/yellow]")
            if what in ["repos", "all"]:
                console.print("[yellow]Any local changes will be lost.[/yellow]")
            if what in ["dbs", "all"]:
                console.print("[yellow]Any cached data will be lost.[/yellow]")
            if not Confirm.ask("Are you sure you want to continue?"):
                console.print("[blue]Operation cancelled.[/blue]")
                return

        cleaned_items = []

        # Clean repository if requested
        if what in ["repos", "all"]:
            component_path = component.get_absolute_local_path()
            if component_path and Path(component_path).exists():
                shutil.rmtree(component_path)
                cleaned_items.append(f"Repository: {component_path}")

        # Clean database if requested
        if what in ["dbs", "all"]:
            component_db_path = component.get_absolute_db_path()
            if component_db_path and Path(component_db_path).exists():
                Path(component_db_path).unlink()
                cleaned_items.append(f"Database: {component_db_path}")

        if cleaned_items:
            console.print(f"[green]✓ Cleaned {len(cleaned_items)} items for component '{component_name}':[/green]")
            for item in cleaned_items:
                console.print(f"  - {item}")
        else:
            what_desc = {"repos": "repositories", "dbs": "databases", "all": "repositories or databases"}[what]
            console.print(f"[yellow]No {what_desc} found to clean for component '{component_name}'.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()