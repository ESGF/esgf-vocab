"""
Offline mode management CLI commands.

This module provides CLI commands for managing offline mode settings
for universe and project components.
"""

import typer
from rich.console import Console
from rich.table import Table

from esgvoc.core.service import config_manager


app = typer.Typer()
console = Console()


@app.command()
def show(
    component: str = typer.Argument(
        None,
        help="Component to show offline status for (universe or project name). Shows all if not specified."
    ),
    config: str = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration name to use"
    )
):
    """Show offline mode status for components."""
    try:
        if config:
            settings = config_manager.get_config(config)
        else:
            settings = config_manager.get_active_config()

        if component:
            # Show specific component
            if component == "universe":
                if settings.universe.offline_mode:
                    console.print(f"[green]Universe is in offline mode[/green]")
                else:
                    console.print(f"[yellow]Universe is in online mode[/yellow]")
            elif component in settings.projects:
                project = settings.projects[component]
                if project.offline_mode:
                    console.print(f"[green]Project '{component}' is in offline mode[/green]")
                else:
                    console.print(f"[yellow]Project '{component}' is in online mode[/yellow]")
            else:
                console.print(f"[red]Component '{component}' not found[/red]")
                raise typer.Exit(1)
        else:
            # Show all components
            table = Table(title="Offline Mode Status")
            table.add_column("Component", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Offline Mode", style="bold")

            # Universe
            status = "[green]✓ Enabled[/green]" if settings.universe.offline_mode else "[yellow]✗ Disabled[/yellow]"
            table.add_row("Universe", "Universe", status)

            # Projects
            for project_name, project in settings.projects.items():
                status = "[green]✓ Enabled[/green]" if project.offline_mode else "[yellow]✗ Disabled[/yellow]"
                table.add_row(project_name, "Project", status)

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def enable(
    component: str = typer.Argument(
        None,
        help="Component to enable offline mode for (universe or project name). If not specified, enables for all components."
    ),
    config: str = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration name to use"
    )
):
    """Enable offline mode for a component or all components if none specified."""
    try:
        if config:
            settings = config_manager.get_config(config)
        else:
            settings = config_manager.get_active_config()

        if component is None:
            # Enable for all components
            settings.universe.offline_mode = True
            for project in settings.projects.values():
                project.offline_mode = True
            console.print(f"[green]✓ Enabled offline mode for all components[/green]")
        elif component == "universe":
            settings.universe.offline_mode = True
            console.print(f"[green]✓ Enabled offline mode for universe[/green]")
        elif component in settings.projects:
            settings.projects[component].offline_mode = True
            console.print(f"[green]✓ Enabled offline mode for project '{component}'[/green]")
        else:
            console.print(f"[red]Component '{component}' not found[/red]")
            raise typer.Exit(1)

        # Save the updated settings
        if config:
            # Use the correct format for saving
            data = {
                "universe": settings.universe.model_dump(),
                "projects": [p.model_dump() for p in settings.projects.values()],
            }
            config_manager.save_config(data, config)
        else:
            config_manager.save_active_config(settings)
        console.print(f"[blue]Configuration saved[/blue]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def disable(
    component: str = typer.Argument(
        None,
        help="Component to disable offline mode for (universe or project name). If not specified, disables for all components."
    ),
    config: str = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration name to use"
    )
):
    """Disable offline mode for a component or all components if none specified."""
    try:
        if config:
            settings = config_manager.get_config(config)
        else:
            settings = config_manager.get_active_config()

        if component is None:
            # Disable for all components
            settings.universe.offline_mode = False
            for project in settings.projects.values():
                project.offline_mode = False
            console.print(f"[yellow]✓ Disabled offline mode for all components[/yellow]")
        elif component == "universe":
            settings.universe.offline_mode = False
            console.print(f"[yellow]✓ Disabled offline mode for universe[/yellow]")
        elif component in settings.projects:
            settings.projects[component].offline_mode = False
            console.print(f"[yellow]✓ Disabled offline mode for project '{component}'[/yellow]")
        else:
            console.print(f"[red]Component '{component}' not found[/red]")
            raise typer.Exit(1)

        # Save the updated settings
        if config:
            # Use the correct format for saving
            data = {
                "universe": settings.universe.model_dump(),
                "projects": [p.model_dump() for p in settings.projects.values()],
            }
            config_manager.save_config(data, config)
        else:
            config_manager.save_active_config(settings)
        console.print(f"[blue]Configuration saved[/blue]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def enable_all(
    config: str = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration name to use"
    )
):
    """Enable offline mode for all components."""
    try:
        if config:
            settings = config_manager.get_config(config)
        else:
            settings = config_manager.get_active_config()

        # Enable for universe
        settings.universe.offline_mode = True

        # Enable for all projects
        for project in settings.projects.values():
            project.offline_mode = True

        # Save the updated settings
        if config:
            # Use the correct format for saving
            data = {
                "universe": settings.universe.model_dump(),
                "projects": [p.model_dump() for p in settings.projects.values()],
            }
            config_manager.save_config(data, config)
        else:
            config_manager.save_active_config(settings)

        console.print(f"[green]✓ Enabled offline mode for all components[/green]")
        console.print(f"[blue]Configuration saved[/blue]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def disable_all(
    config: str = typer.Option(
        None,
        "--config",
        "-c",
        help="Configuration name to use"
    )
):
    """Disable offline mode for all components."""
    try:
        if config:
            settings = config_manager.get_config(config)
        else:
            settings = config_manager.get_active_config()

        # Disable for universe
        settings.universe.offline_mode = False

        # Disable for all projects
        for project in settings.projects.values():
            project.offline_mode = False

        # Save the updated settings
        if config:
            # Use the correct format for saving
            data = {
                "universe": settings.universe.model_dump(),
                "projects": [p.model_dump() for p in settings.projects.values()],
            }
            config_manager.save_config(data, config)
        else:
            config_manager.save_active_config(settings)

        console.print(f"[yellow]✓ Disabled offline mode for all components[/yellow]")
        console.print(f"[blue]Configuration saved[/blue]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()