import os
import shutil
from pathlib import Path
from typing import List, Optional

import toml
import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

# Import service module but don't initialize it immediately
import esgvoc.core.service.configuration.config_manager as config_manager_module
from esgvoc.core.service.configuration.setting import ServiceSettings

def get_service():
    """Get the service module, importing it only when needed."""
    import esgvoc.core.service as service
    return service

app = typer.Typer()
console = Console()


def _get_fresh_config(config_manager, config_name: str):
    """
    Get a fresh configuration, bypassing any potential caching issues.
    """
    # Force reload from file to ensure we have the latest state
    configs = config_manager.list_configs()
    config_path = configs[config_name]

    # Load directly from file to avoid any caching
    try:
        data = toml.load(config_path)
        projects = {p["project_name"]: ServiceSettings.ProjectSettings(**p) for p in data.pop("projects", [])}
        from esgvoc.core.service.configuration.setting import UniverseSettings

        return ServiceSettings(universe=UniverseSettings(**data["universe"]), projects=projects)
    except Exception:
        # Fallback to config manager if direct load fails
        return config_manager.get_config(config_name)


def _save_and_reload_config(config_manager, config_name: str, config):
    """
    Save configuration and ensure proper state reload.
    """
    config_manager.save_active_config(config)

    # Reset the state if we modified the active configuration
    if config_name == config_manager.get_active_config_name():
        service.current_state = service.get_state()

        # Clear any potential caches in the config manager
        if hasattr(config_manager, "_cached_config"):
            config_manager._cached_config = None
        if hasattr(config_manager, "cache"):
            config_manager.cache.clear()

    """
    Function to display a rich table in the console.

    :param table: The table to be displayed
    """
    console = Console(record=True, width=200)
    console.print(table)


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
    service = get_service()
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
    service = get_service()
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
    service = get_service()
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
    service = get_service()
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
            config_data = ServiceSettings._get_default_settings()

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
    service = get_service()
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
    service = get_service()
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
        esgvoc config set 'universe:branch=esgvoc_dev'

        # Enable offline mode for universe
        esgvoc config set 'universe:offline_mode=true'

        # Enable offline mode for a specific project
        esgvoc config set 'cmip6:offline_mode=true'

        # Change multiple components at once
        esgvoc config set 'universe:branch=esgvoc_dev' 'cmip6:branch=esgvoc_dev'

        # Change settings in a specific configuration
        esgvoc config set 'universe:local_path=repos/prod/universe' --config prod

        # Change the GitHub repository URL for a project
        esgvoc config set 'cmip6:github_repo=https://github.com/WCRP-CMIP/CMIP6_CVs_new'
    """
    service = get_service()
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
                    elif setting_key == "offline_mode":
                        config.universe.offline_mode = setting_value.lower() in ("true", "1", "yes", "on")
                        modified = True
                    else:
                        console.print(f"[yellow]Warning: Unknown universe setting '{setting_key}'. Skipping.[/yellow]")
                        continue

                    console.print(f"[green]Updated universe.{setting_key} = {setting_value}[/green]")

                # Handle project settings using the new update_project method
                elif component_part in config.projects:
                    # Use the new update_project method
                    if config.update_project(component_part, **{setting_key: setting_value}):
                        modified = True
                        console.print(f"[green]Updated {component_part}.{setting_key} = {setting_value}[/green]")
                    else:
                        console.print(f"[yellow]Warning: Unknown project setting '{setting_key}'. Skipping.[/yellow]")
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


# 🔹 NEW: Enhanced project management commands using ServiceSettings methods


@app.command()
def list_available_projects():
    """
    List all available default projects that can be added.
    """
    available_projects = ServiceSettings._get_default_project_configs()

    table = Table(title="Available Default Projects")
    table.add_column("Project Name", style="cyan")
    table.add_column("Repository", style="green")
    table.add_column("Branch", style="yellow")

    for project_name, config in available_projects.items():
        table.add_row(project_name, config["github_repo"], config["branch"])

    display(table)


@app.command()
def list_projects(
    config_name: Optional[str] = typer.Option(
        None, "--config", "-c", help="Configuration name. Uses active configuration if not specified."
    ),
):
    """
    List all projects in a configuration.
    """
    service = get_service()
    config_manager = service.get_config_manager()
    if config_name is None:
        config_name = config_manager.get_active_config_name()
        console.print(f"Showing projects in active configuration: [cyan]{config_name}[/cyan]")

    configs = config_manager.list_configs()
    if config_name not in configs:
        console.print(f"[red]Error: Configuration '{config_name}' not found.[/red]")
        raise typer.Exit(1)

    try:
        config = config_manager.get_config(config_name)

        if not config.projects:
            console.print(f"[yellow]No projects found in configuration '{config_name}'.[/yellow]")
            return

        table = Table(title=f"Projects in Configuration: {config_name}")
        table.add_column("Project Name", style="cyan")
        table.add_column("Repository", style="green")
        table.add_column("Branch", style="yellow")
        table.add_column("Local Path", style="blue")
        table.add_column("DB Path", style="magenta")

        for project_name, project in config.projects.items():
            table.add_row(
                project_name,
                project.github_repo,
                project.branch or "main",
                project.local_path or "N/A",
                project.db_path or "N/A",
            )

        display(table)

    except Exception as e:
        console.print(f"[red]Error listing projects: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def add_project(
    project_name: str = typer.Argument(..., help="Name of the project to add."),
    config_name: Optional[str] = typer.Option(
        None, "--config", "-c", help="Configuration name. Uses active configuration if not specified."
    ),
    from_default: bool = typer.Option(
        True, "--from-default/--custom", help="Add from default configuration or specify custom settings."
    ),
    # Custom project options (only used when --custom is specified)
    github_repo: Optional[str] = typer.Option(
        None, "--repo", "-r", help="GitHub repository URL (for custom projects)."
    ),
    branch: Optional[str] = typer.Option("main", "--branch", "-b", help="Branch (for custom projects)."),
    local_path: Optional[str] = typer.Option(None, "--local", "-l", help="Local path (for custom projects)."),
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="Database path (for custom projects)."),
):
    """
    Add a project to a configuration.

    By default, adds from available default projects. Use --custom to specify custom settings.

    Examples:
        # Add a default project
        esgvoc add-project input4mip

        # Add a custom project
        esgvoc add-project my_project --custom --repo https://github.com/me/repo
    """
    service = get_service()
    config_manager = service.get_config_manager()
    if config_name is None:
        config_name = config_manager.get_active_config_name()
        console.print(f"Modifying active configuration: [cyan]{config_name}[/cyan]")

    configs = config_manager.list_configs()
    if config_name not in configs:
        console.print(f"[red]Error: Configuration '{config_name}' not found.[/red]")
        raise typer.Exit(1)

    try:
        # 🔹 FORCE FRESH LOAD: Load configuration directly from file to bypass any caching
        configs = config_manager.list_configs()
        config_path = configs[config_name]

        # Load fresh configuration from file
        try:
            config = ServiceSettings.load_from_file(config_path)
            console.print(f"[blue]Debug: Loaded fresh config from file[/blue]")
        except Exception as e:
            console.print(f"[yellow]Debug: Failed to load from file ({e}), using config manager[/yellow]")
            config = config_manager.get_config(config_name)

        # 🔹 DEBUG: Show current projects before adding
        current_projects = []
        if hasattr(config, "projects") and config.projects:
            current_projects = [name for name in config.projects.keys()]
        console.print(f"[blue]Debug: Current projects: {current_projects}[/blue]")

        if from_default:
            # Add from default configuration
            if config.add_project_from_default(project_name):
                console.print(
                    f"[green]Successfully added default project [cyan]{project_name}[/cyan] to configuration [cyan]{config_name}[/cyan][/green]"
                )
            else:
                if config.has_project(project_name):
                    console.print(
                        f"[red]Error: Project '{project_name}' already exists in configuration '{config_name}'.[/red]"
                    )
                else:
                    available = config.get_available_default_projects()
                    console.print(f"[red]Error: '{project_name}' is not a valid default project.[/red]")
                    console.print(f"[yellow]Available default projects: {', '.join(available)}[/yellow]")
                raise typer.Exit(1)
        else:
            # Add custom project
            if not github_repo:
                console.print("[red]Error: --repo is required when adding custom projects.[/red]")
                raise typer.Exit(1)

            # Set default paths if not provided
            if local_path is None:
                local_path = f"repos/{project_name}"
            if db_path is None:
                db_path = f"dbs/{project_name}.sqlite"

            custom_config = {
                "project_name": project_name,
                "github_repo": github_repo,
                "branch": branch,
                "local_path": local_path,
                "db_path": db_path,
            }

            if config.add_project_custom(custom_config):
                console.print(
                    f"[green]Successfully added custom project [cyan]{project_name}[/cyan] to configuration [cyan]{config_name}[/cyan][/green]"
                )
            else:
                console.print(
                    f"[red]Error: Project '{project_name}' already exists in configuration '{config_name}'.[/red]"
                )
                raise typer.Exit(1)

        # Save the configuration
        config_manager.save_active_config(config)

        # Reset the state if we modified the active configuration
        if config_name == config_manager.get_active_config_name():
            service.current_state = service.get_state()

    except ValueError as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error adding project: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def remove_project(
    project_name: str = typer.Argument(..., help="Name of the project to remove."),
    config_name: Optional[str] = typer.Option(
        None, "--config", "-c", help="Configuration name. Uses active configuration if not specified."
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt."),
):
    """
    Remove a project from a configuration.
    """
    service = get_service()
    config_manager = service.get_config_manager()
    if config_name is None:
        config_name = config_manager.get_active_config_name()
        console.print(f"Modifying active configuration: [cyan]{config_name}[/cyan]")

    configs = config_manager.list_configs()
    if config_name not in configs:
        console.print(f"[red]Error: Configuration '{config_name}' not found.[/red]")
        raise typer.Exit(1)

    try:
        # 🔹 FORCE FRESH LOAD for removal too
        configs = config_manager.list_configs()
        config_path = configs[config_name]

        try:
            config = ServiceSettings.load_from_file(config_path)
            console.print(f"[blue]Debug: Loaded fresh config from file for removal[/blue]")
        except Exception as e:
            console.print(f"[yellow]Debug: Failed to load from file ({e}), using config manager[/yellow]")
            config = config_manager.get_config(config_name)

        if not config.has_project(project_name):
            console.print(f"[red]Error: Project '{project_name}' not found in configuration '{config_name}'.[/red]")
            raise typer.Exit(1)

        # Confirm removal unless forced
        if not force:
            confirm = typer.confirm(
                f"Are you sure you want to remove project '{project_name}' from configuration '{config_name}'?"
            )
            if not confirm:
                console.print("Operation cancelled.")
                return

        # Remove project using the new method
        if config.remove_project(project_name):
            console.print(
                f"[green]Successfully removed project [cyan]{project_name}[/cyan] from configuration [cyan]{config_name}[/cyan][/green]"
            )
        else:
            console.print(f"[red]Error: Failed to remove project '{project_name}'.[/red]")
            raise typer.Exit(1)

        # Save the configuration
        config_manager.save_active_config(config)

        # 🔹 DEBUG: Verify the project was actually removed
        remaining_projects = []
        if hasattr(config, "projects") and config.projects:
            remaining_projects = [name for name in config.projects.keys()]
        console.print(f"[blue]Debug: Projects after removal: {remaining_projects}[/blue]")

        # Reset the state if we modified the active configuration
        if config_name == config_manager.get_active_config_name():
            service.current_state = service.get_state()

    except Exception as e:
        console.print(f"[red]Error removing project: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def update_project(
    project_name: str = typer.Argument(..., help="Name of the project to update."),
    config_name: Optional[str] = typer.Option(
        None, "--config", "-c", help="Configuration name. Uses active configuration if not specified."
    ),
    github_repo: Optional[str] = typer.Option(None, "--repo", "-r", help="New GitHub repository URL."),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="New branch."),
    local_path: Optional[str] = typer.Option(None, "--local", "-l", help="New local path."),
    db_path: Optional[str] = typer.Option(None, "--db", "-d", help="New database path."),
):
    """
    Update settings for an existing project.
    """
    service = get_service()
    config_manager = service.get_config_manager()
    if config_name is None:
        config_name = config_manager.get_active_config_name()
        console.print(f"Modifying active configuration: [cyan]{config_name}[/cyan]")

    configs = config_manager.list_configs()
    if config_name not in configs:
        console.print(f"[red]Error: Configuration '{config_name}' not found.[/red]")
        raise typer.Exit(1)

    try:
        config = config_manager.get_config(config_name)

        if not config.has_project(project_name):
            console.print(f"[red]Error: Project '{project_name}' not found in configuration '{config_name}'.[/red]")
            raise typer.Exit(1)

        # Build update dict with non-None values
        updates = {}
        if github_repo is not None:
            updates["github_repo"] = github_repo
        if branch is not None:
            updates["branch"] = branch
        if local_path is not None:
            updates["local_path"] = local_path
        if db_path is not None:
            updates["db_path"] = db_path

        if not updates:
            console.print(
                "[yellow]No updates specified. Use --repo, --branch, --local, or --db to specify changes.[/yellow]"
            )
            return

        # Update project using the new method
        if config.update_project(project_name, **updates):
            console.print(
                f"[green]Successfully updated project [cyan]{project_name}[/cyan] in configuration [cyan]{config_name}[/cyan][/green]"
            )
            for key, value in updates.items():
                console.print(f"  [green]{key} = {value}[/green]")
        else:
            console.print(f"[red]Error: Failed to update project '{project_name}'.[/red]")
            raise typer.Exit(1)

        # Save the configuration
        config_manager.save_active_config(config)

        # Reset the state if we modified the active configuration
        if config_name == config_manager.get_active_config_name():
            service.current_state = service.get_state()

    except Exception as e:
        console.print(f"[red]Error updating project: {str(e)}[/red]")
        raise typer.Exit(1)


# 🔹 NEW: Simple config management commands


@app.command()
def add(
    project_names: List[str] = typer.Argument(..., help="Names of the projects to add from defaults."),
    config_name: Optional[str] = typer.Option(
        None, "--config", "-c", help="Configuration name. Uses active configuration if not specified."
    ),
):
    """
    Add one or more default projects to the current configuration and install their CVs.

    This will:
    1. Add the projects to the configuration using default settings
    2. Download the projects' CVs by running synchronize_all

    Examples:
        esgvoc config add input4mip
        esgvoc config add input4mip obs4mip cordex-cmip6
        esgvoc config add obs4mip --config my_config
    """
    service = get_service()
    config_manager = service.get_config_manager()
    if config_name is None:
        config_name = config_manager.get_active_config_name()
        console.print(f"Adding to active configuration: [cyan]{config_name}[/cyan]")

    configs = config_manager.list_configs()
    if config_name not in configs:
        console.print(f"[red]Error: Configuration '{config_name}' not found.[/red]")
        raise typer.Exit(1)

    try:
        # Load fresh configuration from file
        configs = config_manager.list_configs()
        config_path = configs[config_name]
        config = ServiceSettings.load_from_file(config_path)

        added_projects = []
        skipped_projects = []
        invalid_projects = []

        # Process each project
        for project_name in project_names:
            # Check if project already exists
            if config.has_project(project_name):
                skipped_projects.append(project_name)
                console.print(f"[yellow]⚠ Project '{project_name}' already exists - skipping[/yellow]")
                continue

            # Add the project from defaults
            try:
                if config.add_project_from_default(project_name):
                    added_projects.append(project_name)
                    console.print(f"[green]✓ Added project [cyan]{project_name}[/cyan][/green]")
                else:
                    invalid_projects.append(project_name)
                    console.print(f"[red]✗ Invalid project '{project_name}'[/red]")
            except ValueError as e:
                invalid_projects.append(project_name)
                console.print(f"[red]✗ Invalid project '{project_name}'[/red]")

        # Show summary of what was processed
        if added_projects:
            console.print(
                f"[green]Successfully added {len(added_projects)} project(s): {', '.join(added_projects)}[/green]"
            )
        if skipped_projects:
            console.print(
                f"[yellow]Skipped {len(skipped_projects)} existing project(s): {', '.join(skipped_projects)}[/yellow]"
            )
        if invalid_projects:
            available = config.get_available_default_projects()
            console.print(f"[red]Invalid project(s): {', '.join(invalid_projects)}[/red]")
            console.print(f"[yellow]Available projects: {', '.join(available)}[/yellow]")

        # Only proceed if we actually added something
        if added_projects:
            # Save the configuration to the correct file
            if config_name == config_manager.get_active_config_name():
                config_manager.save_active_config(config)
                # Reset the state if we modified the active configuration
                service.current_state = service.get_state()
            else:
                # Save to specific config file
                config_path = configs[config_name]
                config.save_to_file(config_path)

            # Download the CVs for all added projects
            console.print(f"[blue]Downloading CVs for {len(added_projects)} project(s)...[/blue]")
            service.current_state.synchronize_all()
            console.print(f"[green]✓ Successfully installed CVs for all added projects[/green]")
        elif invalid_projects and not skipped_projects:
            # Exit with error only if we had invalid projects and nothing was skipped
            raise typer.Exit(1)

    except ValueError as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error adding project: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def rm(
    project_names: List[str] = typer.Argument(..., help="Names of the projects to remove."),
    config_name: Optional[str] = typer.Option(
        None, "--config", "-c", help="Configuration name. Uses active configuration if not specified."
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt."),
    keep_files: bool = typer.Option(
        False, "--keep-files", help="Keep local repos and databases (only remove from config)."
    ),
):
    """
    Remove one or more projects from the configuration and delete their repos/databases.

    This will:
    1. Remove the projects from the configuration
    2. Delete the local repository directories (unless --keep-files)
    3. Delete the database files (unless --keep-files)

    Examples:
        esgvoc config rm input4mip
        esgvoc config rm input4mip obs4mip cordex-cmip6
        esgvoc config rm obs4mip --force
        esgvoc config rm cmip6 input4mip --keep-files  # Remove from config but keep files
    """
    service = get_service()
    config_manager = service.get_config_manager()
    if config_name is None:
        config_name = config_manager.get_active_config_name()
        console.print(f"Removing from active configuration: [cyan]{config_name}[/cyan]")

    configs = config_manager.list_configs()
    if config_name not in configs:
        console.print(f"[red]Error: Configuration '{config_name}' not found.[/red]")
        raise typer.Exit(1)

    try:
        # Load fresh configuration from file
        configs = config_manager.list_configs()
        config_path = configs[config_name]
        config = ServiceSettings.load_from_file(config_path)

        # Check which projects exist and collect their details
        valid_projects = []
        invalid_projects = []
        projects_to_remove = {}  # project_name -> project_object

        for project_name in project_names:
            if config.has_project(project_name):
                project = config.get_project(project_name)
                projects_to_remove[project_name] = project
                valid_projects.append(project_name)
            else:
                invalid_projects.append(project_name)
                console.print(f"[red]✗ Project '{project_name}' not found in configuration[/red]")

        if invalid_projects:
            console.print(f"[red]Invalid project(s): {', '.join(invalid_projects)}[/red]")

        if not valid_projects:
            console.print("[red]No valid projects to remove.[/red]")
            raise typer.Exit(1)

        # Show what will be removed and confirm unless forced
        console.print(f"[yellow]Projects to remove: {', '.join(valid_projects)}[/yellow]")
        if not force:
            action_desc = "remove from config only" if keep_files else "remove from config and delete all files"
            project_word = "project" if len(valid_projects) == 1 else "projects"
            confirm = typer.confirm(f"Are you sure you want to {action_desc} for {len(valid_projects)} {project_word}?")
            if not confirm:
                console.print("Operation cancelled.")
                return

        # Get base directory for file cleanup
        base_dir = config_manager.data_config_dir or str(config_manager.data_dir)

        removed_projects = []
        # Remove each project
        for project_name in valid_projects:
            project = projects_to_remove[project_name]

            if config.remove_project(project_name):
                removed_projects.append(project_name)
                console.print(f"[green]✓ Removed [cyan]{project_name}[/cyan] from configuration[/green]")

                # Clean up filesystem unless --keep-files
                if not keep_files and project:
                    # Clean up local repository
                    if project.local_path:
                        repo_path = Path(base_dir) / project.local_path
                        if repo_path.exists():
                            shutil.rmtree(repo_path)
                            console.print(f"[green]  ✓ Deleted repository: {repo_path}[/green]")
                        else:
                            console.print(f"[yellow]  Repository not found: {repo_path}[/yellow]")

                    # Clean up database
                    if project.db_path:
                        db_path = Path(base_dir) / project.db_path
                        if db_path.exists():
                            db_path.unlink()
                            console.print(f"[green]  ✓ Deleted database: {db_path}[/green]")
                        else:
                            console.print(f"[yellow]  Database not found: {db_path}[/yellow]")
            else:
                console.print(f"[red]✗ Failed to remove '{project_name}'[/red]")

        if removed_projects:
            console.print(
                f"[green]Successfully removed {len(removed_projects)} project(s): {', '.join(removed_projects)}[/green]"
            )

            # Save the configuration to the correct file
            if config_name == config_manager.get_active_config_name():
                config_manager.save_active_config(config)
                # Reset the state if we modified the active configuration
                service.current_state = service.get_state()
            else:
                # Save to specific config file
                config_path = configs[config_name]
                config.save_to_file(config_path)
        else:
            console.print("[red]No projects were successfully removed.[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error removing project: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def init(
    name: str = typer.Argument(..., help="Name for the new empty configuration."),
    no_switch: bool = typer.Option(
        False, "--no-switch", help="Don't switch to the new configuration (stays on current)."
    ),
):
    """
    Create a new empty configuration with only universe settings (no projects).

    This creates a minimal configuration with just the universe component,
    allowing you to add projects selectively using 'esgvoc config add'.
    By default, switches to the new configuration after creation.

    Examples:
        esgvoc config init minimal
        esgvoc config init test --no-switch  # Create but don't switch
    """
    service = get_service()
    config_manager = service.get_config_manager()
    configs = config_manager.list_configs()

    if name in configs:
        console.print(f"[red]Error: Configuration '{name}' already exists.[/red]")
        raise typer.Exit(1)

    try:
        # Create empty configuration with only universe settings
        default_settings = ServiceSettings._get_default_settings()
        empty_config_data = {
            "universe": default_settings["universe"],
            "projects": [],  # No projects - completely empty
        }

        # Add the new configuration
        config_manager.add_config(name, empty_config_data)
        console.print(f"[green]✓ Created empty configuration: [cyan]{name}[/cyan][/green]")

        # Switch to new config by default (unless --no-switch is used)
        if not no_switch:
            config_manager.switch_config(name)
            console.print(f"[green]✓ Switched to configuration: [cyan]{name}[/cyan][/green]")
            # Reset the state to use the new configuration
            service.current_state = service.get_state()

    except Exception as e:
        console.print(f"[red]Error creating configuration: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def migrate(
    config_name: Optional[str] = typer.Option(
        None, "--config", "-c", help="Configuration name to migrate. Migrates all configs if not specified."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be changed without making changes."),
):
    """
    Migrate configuration(s) to convert relative paths to absolute paths.

    This command is needed when upgrading to newer versions that require absolute paths.
    By default, migrates all configurations. Use --config to migrate only a specific one.

    Examples:
        esgvoc config migrate              # Migrate all configurations
        esgvoc config migrate --config user_config  # Migrate specific configuration
        esgvoc config migrate --dry-run    # Show what would be changed
    """
    import os
    from pathlib import Path

    # Enable migration mode to allow loading configs with relative paths
    os.environ['ESGVOC_MIGRATION_MODE'] = '1'

    try:
        # Use config manager directly to avoid service initialization issues
        from esgvoc.core.service.configuration.config_manager import ConfigManager
        config_manager = ConfigManager(ServiceSettings, app_name="esgvoc", app_author="ipsl", default_settings=ServiceSettings._get_default_settings())
        configs = config_manager.list_configs()

        # Determine which configs to migrate
        if config_name:
            if config_name not in configs:
                console.print(f"[red]Error: Configuration '{config_name}' not found.[/red]")
                raise typer.Exit(1)
            configs_to_migrate = {config_name: configs[config_name]}
        else:
            configs_to_migrate = configs

        console.print(f"[blue]Migrating {len(configs_to_migrate)} configuration(s)...[/blue]")

        migrated_count = 0
        for name, config_path in configs_to_migrate.items():
            console.print(f"\n[cyan]Processing configuration: {name}[/cyan]")

            try:
                # Load the raw TOML data first to check for relative paths
                with open(config_path, 'r') as f:
                    raw_data = toml.load(f)

                changes_made = []

                # Check universe paths
                if 'universe' in raw_data:
                    universe = raw_data['universe']
                    for path_field in ['local_path', 'db_path']:
                        if path_field in universe and universe[path_field]:
                            path_val = universe[path_field]
                            if not Path(path_val).is_absolute():
                                changes_made.append(f"universe.{path_field}: {path_val} -> <absolute>")

                # Check project paths
                if 'projects' in raw_data:
                    for project in raw_data['projects']:
                        project_name = project.get('project_name', 'unknown')
                        for path_field in ['local_path', 'db_path']:
                            if path_field in project and project[path_field]:
                                path_val = project[path_field]
                                if not Path(path_val).is_absolute():
                                    changes_made.append(f"{project_name}.{path_field}: {path_val} -> <absolute>")

                if changes_made:
                    console.print(f"[yellow]Found {len(changes_made)} relative paths to migrate:[/yellow]")
                    for change in changes_made:
                        console.print(f"  • {change}")

                    if not dry_run:
                        # Load using ServiceSettings which will auto-convert to absolute paths
                        migrated_config = ServiceSettings.load_from_file(config_path)

                        # Save back to file (now with absolute paths)
                        migrated_config.save_to_file(config_path)
                        console.print(f"[green]✓ Successfully migrated configuration: {name}[/green]")
                        migrated_count += 1
                    else:
                        console.print(f"[blue]  (dry-run: would migrate configuration: {name})[/blue]")
                        migrated_count += 1
                else:
                    console.print(f"[dim]No relative paths found in {name} - already migrated[/dim]")

            except Exception as e:
                console.print(f"[red]Error processing {name}: {str(e)}[/red]")
                continue

        # Summary
        action = "would be migrated" if dry_run else "migrated"
        if migrated_count > 0:
            console.print(f"\n[green]✓ {migrated_count} configuration(s) {action} successfully[/green]")
            if not dry_run:
                console.print("[blue]All relative paths have been converted to absolute paths.[/blue]")
                console.print("[blue]You can now use the configuration system normally.[/blue]")
        else:
            console.print(f"\n[blue]No configurations needed migration - all paths are already absolute[/blue]")

    except Exception as e:
        console.print(f"[red]Error during migration: {str(e)}[/red]")
        raise typer.Exit(1)
    finally:
        # Disable migration mode
        if 'ESGVOC_MIGRATION_MODE' in os.environ:
            del os.environ['ESGVOC_MIGRATION_MODE']


@app.command()
def offline(
    enable: Optional[bool] = typer.Option(
        None, "--enable/--disable", help="Enable or disable offline mode. If not specified, shows current status."
    ),
    component: Optional[str] = typer.Option(
        "universe", "--component", "-c", help="Component to modify: 'universe' or project name (default: universe)"
    ),
    config_name: Optional[str] = typer.Option(
        None, "--config", help="Configuration name. Uses active configuration if not specified."
    ),
):
    """
    Enable, disable, or show offline mode status.

    Examples:
        esgvoc config offline --enable               # Enable offline mode for universe
        esgvoc config offline --disable              # Disable offline mode for universe
        esgvoc config offline --enable -c cmip6      # Enable offline mode for cmip6 project
        esgvoc config offline                        # Show current offline mode status
    """
    service = get_service()
    config_manager = service.get_config_manager()

    if config_name is None:
        config_name = config_manager.get_active_config_name()

    configs = config_manager.list_configs()
    if config_name not in configs:
        console.print(f"[red]Error: Configuration '{config_name}' not found.[/red]")
        raise typer.Exit(1)

    try:
        config = config_manager.get_config(config_name)

        if enable is None:
            # Show current status
            if component == "universe":
                status = "enabled" if config.universe.offline_mode else "disabled"
                console.print(f"Universe offline mode is [cyan]{status}[/cyan] in configuration '{config_name}'")
            elif component in config.projects:
                status = "enabled" if config.projects[component].offline_mode else "disabled"
                console.print(f"Project '{component}' offline mode is [cyan]{status}[/cyan] in configuration '{config_name}'")
            else:
                console.print(f"[red]Error: Component '{component}' not found.[/red]")
                raise typer.Exit(1)
        else:
            # Update offline mode
            if component == "universe":
                config.universe.offline_mode = enable
                status = "enabled" if enable else "disabled"
                console.print(f"[green]Universe offline mode {status} in configuration '{config_name}'[/green]")
            elif component in config.projects:
                config.projects[component].offline_mode = enable
                status = "enabled" if enable else "disabled"
                console.print(f"[green]Project '{component}' offline mode {status} in configuration '{config_name}'[/green]")
            else:
                console.print(f"[red]Error: Component '{component}' not found.[/red]")
                raise typer.Exit(1)

            # Save the configuration
            config_manager.save_active_config(config)

            # Reset the state if we modified the active configuration
            if config_name == config_manager.get_active_config_name():
                service.current_state = service.get_state()

    except Exception as e:
        console.print(f"[red]Error managing offline mode: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def avail(
    config_name: Optional[str] = typer.Option(
        None, "--config", "-c", help="Configuration name. Uses active configuration if not specified."
    ),
):
    """
    Show a table of all available default projects and their status in the configuration.

    Projects are marked as:
    - ✓ Active: Project is in the current configuration
    - ○ Available: Project can be added to the configuration

    Examples:
        esgvoc config avail
        esgvoc config avail --config my_config
    """
    service = get_service()
    config_manager = service.get_config_manager()
    if config_name is None:
        config_name = config_manager.get_active_config_name()
        console.print(f"Showing project availability for: [cyan]{config_name}[/cyan]")

    configs = config_manager.list_configs()
    if config_name not in configs:
        console.print(f"[red]Error: Configuration '{config_name}' not found.[/red]")
        raise typer.Exit(1)

    try:
        # Load configuration
        config_path = configs[config_name]
        config = ServiceSettings.load_from_file(config_path)

        # Get all available default projects
        available_projects = ServiceSettings._get_default_project_configs()

        table = Table(title=f"Available Projects (Configuration: {config_name})")
        table.add_column("Status", style="bold")
        table.add_column("Project Name", style="cyan")
        table.add_column("Repository", style="green")
        table.add_column("Branch", style="yellow")

        for project_name, project_config in available_projects.items():
            # Check if project is in current configuration
            if config.has_project(project_name):
                status = "[green]✓ Active[/green]"
            else:
                status = "[dim]○ Available[/dim]"

            table.add_row(status, project_name, project_config["github_repo"], project_config["branch"])

        display(table)

        # Show summary
        active_count = len([p for p in available_projects.keys() if config.has_project(p)])
        total_count = len(available_projects)
        console.print(
            f"\n[blue]Summary: {active_count}/{total_count} projects active in configuration '{config_name}'[/blue]"
        )

    except Exception as e:
        console.print(f"[red]Error showing available projects: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
