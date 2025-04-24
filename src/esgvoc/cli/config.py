import os
from pathlib import Path
from typing import List, Optional

import toml
import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

import esgvoc.core.service as service
from esgvoc.core.service.configuration.setting import ServiceSettings

app = typer.Typer()
console = Console()


def display(table):
    """
    Function to display a rich table in the console.

    :param table: The table to be displayed
    """
    console = Console(record=True, width=200)
    console.print(table)


@app.command()
def list():
    """
    List all available configurations.

    Displays all available configurations along with the active one.
    """
    config_manager = service.get_config_manager()
    configs = config_manager.list_configs()
    active_config = config_manager.get_active_config_name()

    table = Table(title="Available Configurations")
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="green")
    table.add_column("Status", style="magenta")

    for name, path in configs.items():
        status = "🟢 Active" if name == active_config else ""
        table.add_row(name, path, status)

    display(table)


@app.command()
def show(
    name: Optional[str] = typer.Argument(
        None, help="Name of the configuration to show. If not provided, shows the active configuration."
    ),
):
    """
    Show the content of a specific configuration.

    Args:
        name: Name of the configuration to show. Shows the active configuration if not specified.
    """
    config_manager = service.get_config_manager()
    if name is None:
        name = config_manager.get_active_config_name()
        console.print(f"Showing active configuration: [cyan]{name}[/cyan]")

    configs = config_manager.list_configs()
    if name not in configs:
        console.print(f"[red]Error: Configuration '{name}' not found.[/red]")
        raise typer.Exit(1)

    config_path = configs[name]
    try:
        with open(config_path, "r") as f:
            content = f.read()

        syntax = Syntax(content, "toml", theme="monokai", line_numbers=True)
        console.print(syntax)
    except Exception as e:
        console.print(f"[red]Error reading configuration file: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def switch(name: str = typer.Argument(..., help="Name of the configuration to switch to.")):
    """
    Switch to a different configuration.

    Args:
        name: Name of the configuration to switch to.
    """
    config_manager = service.get_config_manager()
    configs = config_manager.list_configs()

    if name not in configs:
        console.print(f"[red]Error: Configuration '{name}' not found.[/red]")
        raise typer.Exit(1)

    try:
        config_manager.switch_config(name)
        console.print(f"[green]Successfully switched to configuration: [cyan]{name}[/cyan][/green]")

        # Reset the state to use the new configuration
        service.current_state = service.get_state()
    except Exception as e:
        console.print(f"[red]Error switching configuration: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def create(
    name: str = typer.Argument(..., help="Name for the new configuration."),
    base: Optional[str] = typer.Option(
        None, "--base", "-b", help="Base the new configuration on an existing one. Uses the default if not specified."
    ),
    switch_to: bool = typer.Option(False, "--switch", "-s", help="Switch to the new configuration after creating it."),
):
    """
    Create a new configuration.

    Args:
        name: Name for the new configuration.
        base: Base the new configuration on an existing one. Uses the default if not specified.
        switch_to: Switch to the new configuration after creating it.
    """
    config_manager = service.get_config_manager()
    configs = config_manager.list_configs()

    if name in configs:
        console.print(f"[red]Error: Configuration '{name}' already exists.[/red]")
        raise typer.Exit(1)

    if base and base not in configs:
        console.print(f"[red]Error: Base configuration '{base}' not found.[/red]")
        raise typer.Exit(1)

    try:
        if base:
            # Load the base configuration
            base_config = config_manager.get_config(base)
            config_data = base_config.dump()
        else:
            # Use default settings
            config_data = ServiceSettings.DEFAULT_SETTINGS

        # Add the new configuration
        config_manager.add_config(name, config_data)
        console.print(f"[green]Successfully created configuration: [cyan]{name}[/cyan][/green]")

        if switch_to:
            config_manager.switch_config(name)
            console.print(f"[green]Switched to configuration: [cyan]{name}[/cyan][/green]")
            # Reset the state to use the new configuration
            service.current_state = service.get_state()

    except Exception as e:
        console.print(f"[red]Error creating configuration: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def remove(name: str = typer.Argument(..., help="Name of the configuration to remove.")):
    """
    Remove a configuration.

    Args:
        name: Name of the configuration to remove.
    """
    config_manager = service.get_config_manager()
    configs = config_manager.list_configs()

    if name not in configs:
        console.print(f"[red]Error: Configuration '{name}' not found.[/red]")
        raise typer.Exit(1)

    if name == "default":
        console.print("[red]Error: Cannot remove the default configuration.[/red]")
        raise typer.Exit(1)

    confirm = typer.confirm(f"Are you sure you want to remove configuration '{name}'?")
    if not confirm:
        console.print("Operation cancelled.")
        return

    try:
        active_config = config_manager.get_active_config_name()
        config_manager.remove_config(name)
        console.print(f"[green]Successfully removed configuration: [cyan]{name}[/cyan][/green]")

        if active_config == name:
            console.print("[yellow]Active configuration was removed. Switched to default.[/yellow]")
            # Reset the state to use the default configuration
            service.current_state = service.get_state()
    except Exception as e:
        console.print(f"[red]Error removing configuration: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def edit(
    name: Optional[str] = typer.Argument(
        None, help="Name of the configuration to edit. Edits the active configuration if not specified."
    ),
    editor: Optional[str] = typer.Option(
        None, "--editor", "-e", help="Editor to use. Uses the system default if not specified."
    ),
):
    """
    Edit a configuration using the system's default editor or a specified one.

    Args:
        name: Name of the configuration to edit. Edits the active configuration if not specified.
        editor: Editor to use. Uses the system default if not specified.
    """
    config_manager = service.get_config_manager()
    if name is None:
        name = config_manager.get_active_config_name()
        console.print(f"Editing active configuration: [cyan]{name}[/cyan]")

    configs = config_manager.list_configs()
    if name not in configs:
        console.print(f"[red]Error: Configuration '{name}' not found.[/red]")
        raise typer.Exit(1)

    config_path = configs[name]

    editor_cmd = editor or os.environ.get("EDITOR", "vim")
    try:
        # Launch the editor properly by using a list of arguments instead of a string
        import subprocess

        result = subprocess.run([editor_cmd, str(config_path)], check=True)
        if result.returncode == 0:
            console.print(f"[green]Successfully edited configuration: [cyan]{name}[/cyan][/green]")

            # Reset the state if we edited the active configuration
            if name == config_manager.get_active_config_name():
                service.current_state = service.get_state()
        else:
            console.print("[yellow]Editor exited with an error.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error launching editor: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def set(
    changes: List[str] = typer.Argument(
        ...,
        help="Changes in format 'component:key=value', where component is 'universe' or a project name. Multiple can be specified.",
    ),
    config_name: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Name of the configuration to modify. Modifies the active configuration if not specified.",
    ),
):
    """
    Modify configuration settings using a consistent syntax for universe and projects.

    Args:
        changes: List of changes in format 'component:key=value'. For example:
                'universe:branch=main' - Change the universe branch
                'cmip6:github_repo=https://github.com/new/repo' - Change a project's repository
        config_name: Name of the configuration to modify. Modifies the active configuration if not specified.

    Examples:
        # Change the universe branch in the active configuration
        esgvoc set 'universe:branch=esgvoc_dev'

        # Change multiple components at once
        esgvoc set 'universe:branch=esgvoc_dev' 'cmip6:branch=esgvoc_dev'

        # Change settings in a specific configuration
        esgvoc set 'universe:local_path=repos/prod/universe' --config prod

        # Change the GitHub repository URL for a project
        esgvoc set 'cmip6:github_repo=https://github.com/WCRP-CMIP/CMIP6_CVs_new'
    """
    config_manager = service.get_config_manager()
    if config_name is None:
        config_name = config_manager.get_active_config_name()
        console.print(f"Modifying active configuration: [cyan]{config_name}[/cyan]")

    configs = config_manager.list_configs()
    if config_name not in configs:
        console.print(f"[red]Error: Configuration '{config_name}' not found.[/red]")
        raise typer.Exit(1)

    try:
        # Load the configuration
        config = config_manager.get_config(config_name)
        modified = False

        # Process all changes with the same format
        for change in changes:
            try:
                # Format should be component:setting=value (where component is 'universe' or a project name)
                component_part, setting_part = change.split(":", 1)
                setting_key, setting_value = setting_part.split("=", 1)

                # Handle universe settings
                if component_part == "universe":
                    if setting_key == "github_repo":
                        config.universe.github_repo = setting_value
                        modified = True
                    elif setting_key == "branch":
                        config.universe.branch = setting_value
                        modified = True
                    elif setting_key == "local_path":
                        config.universe.local_path = setting_value
                        modified = True
                    elif setting_key == "db_path":
                        config.universe.db_path = setting_value
                        modified = True
                    else:
                        console.print(f"[yellow]Warning: Unknown universe setting '{setting_key}'. Skipping.[/yellow]")
                        continue

                    console.print(f"[green]Updated universe.{setting_key} = {setting_value}[/green]")

                # Handle project settings
                elif component_part in config.projects:
                    project = config.projects[component_part]
                    if setting_key == "github_repo":
                        project.github_repo = setting_value
                    elif setting_key == "branch":
                        project.branch = setting_value
                    elif setting_key == "local_path":
                        project.local_path = setting_value
                    elif setting_key == "db_path":
                        project.db_path = setting_value
                    else:
                        console.print(f"[yellow]Warning: Unknown project setting '{setting_key}'. Skipping.[/yellow]")
                        continue

                    modified = True
                    console.print(f"[green]Updated {component_part}.{setting_key} = {setting_value}[/green]")
                else:
                    console.print(
                        f"[yellow]Warning: Component '{component_part}' not found in configuration. Skipping.[/yellow]"
                    )
                    continue

            except ValueError:
                console.print(
                    f"[yellow]Warning: Invalid change format '{change}'. Should be 'component:key=value'. Skipping.[/yellow]"
                )

        if modified:
            # Save the modified configuration
            config_manager.save_active_config(config)
            console.print(f"[green]Successfully updated configuration: [cyan]{config_name}[/cyan][/green]")

            # Reset the state if we modified the active configuration
            if config_name == config_manager.get_active_config_name():
                service.current_state = service.get_state()
        else:
            console.print("[yellow]No changes were made to the configuration.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error updating configuration: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def add_project(
    name: Optional[str] = typer.Argument(
        None, help="Name of the configuration to modify. Modifies the active configuration if not specified."
    ),
    project_name: str = typer.Option(..., "--name", "-n", help="Name of the project to add."),
    github_repo: str = typer.Option(..., "--repo", "-r", help="GitHub repository URL for the project."),
    branch: str = typer.Option("main", "--branch", "-b", help="Branch for the project repository."),
    local_path: Optional[str] = typer.Option(None, "--local", "-l", help="Local path for the project repository."),
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path for the project."),
):
    """
    Add a new project to a configuration.

    Args:
        name: Name of the configuration to modify. Modifies the active configuration if not specified.
        project_name: Name of the project to add.
        github_repo: GitHub repository URL for the project.
        branch: Branch for the project repository.
        local_path: Local path for the project repository.
        db_path: Database path for the project.
    """
    config_manager = service.get_config_manager()
    if name is None:
        name = config_manager.get_active_config_name()
        console.print(f"Modifying active configuration: [cyan]{name}[/cyan]")

    configs = config_manager.list_configs()
    if name not in configs:
        console.print(f"[red]Error: Configuration '{name}' not found.[/red]")
        raise typer.Exit(1)

    try:
        # Load the configuration
        config = config_manager.get_config(name)

        # Check if project already exists
        if project_name in config.projects:
            console.print(f"[red]Error: Project '{project_name}' already exists in configuration '{name}'.[/red]")
            raise typer.Exit(1)

        # Set default paths if not provided
        if local_path is None:
            local_path = f"repos/{project_name}"
        if db_path is None:
            db_path = f"dbs/{project_name}.sqlite"

        # Create the project settings
        from esgvoc.core.service.configuration.setting import ProjectSettings

        project_settings = ProjectSettings(
            project_name=project_name, github_repo=github_repo, branch=branch, local_path=local_path, db_path=db_path
        )

        # Add to configuration
        config.projects[project_name] = project_settings

        # Save the configuration
        config_manager.save_active_config(config)
        console.print(
            f"[green]Successfully added project [cyan]{project_name}[/cyan] to configuration [cyan]{name}[/cyan][/green]"
        )

        # Reset the state if we modified the active configuration
        if name == config_manager.get_active_config_name():
            service.current_state = service.get_state()

    except Exception as e:
        console.print(f"[red]Error adding project: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def remove_project(
    name: Optional[str] = typer.Argument(
        None, help="Name of the configuration to modify. Modifies the active configuration if not specified."
    ),
    project_name: str = typer.Argument(..., help="Name of the project to remove."),
):
    """
    Remove a project from a configuration.

    Args:
        name: Name of the configuration to modify. Modifies the active configuration if not specified.
        project_name: Name of the project to remove.
    """
    config_manager = service.get_config_manager()
    if name is None:
        name = config_manager.get_active_config_name()
        console.print(f"Modifying active configuration: [cyan]{name}[/cyan]")

    configs = config_manager.list_configs()
    if name not in configs:
        console.print(f"[red]Error: Configuration '{name}' not found.[/red]")
        raise typer.Exit(1)

    try:
        # Load the configuration
        config = config_manager.get_config(name)

        # Check if project exists
        if project_name not in config.projects:
            console.print(f"[red]Error: Project '{project_name}' not found in configuration '{name}'.[/red]")
            raise typer.Exit(1)

        # Confirm removal
        confirm = typer.confirm(
            f"Are you sure you want to remove project '{project_name}' from configuration '{name}'?"
        )
        if not confirm:
            console.print("Operation cancelled.")
            return

        # Remove project
        del config.projects[project_name]

        # Save the configuration
        config_manager.save_active_config(config)
        console.print(
            f"[green]Successfully removed project [cyan]{project_name}[/cyan] from configuration [cyan]{name}[/cyan][/green]"
        )

        # Reset the state if we modified the active configuration
        if name == config_manager.get_active_config_name():
            service.current_state = service.get_state()

    except Exception as e:
        console.print(f"[red]Error removing project: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
