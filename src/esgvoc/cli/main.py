import typer
from rich.console import Console
from rich.table import Table

from esgvoc.cli.clean import app as clean_app
from esgvoc.cli.cmor import app as cmor_app
from esgvoc.cli.config import app as config_app
from esgvoc.cli.drs import app as drs_app
from esgvoc.cli.find import app as find_app
from esgvoc.cli.get import app as get_app
from esgvoc.cli.install import app as install_app
from esgvoc.cli.offline import app as offline_app
from esgvoc.cli.status import app as status_app
from esgvoc.cli.test_cv import app as test_cv_app
from esgvoc.cli.valid import app as valid_app
from esgvoc.core.service.configuration.setting import ServiceSettings

app = typer.Typer()
console = Console()

# Register the subcommands
app.add_typer(get_app)
app.add_typer(status_app)
app.add_typer(valid_app)
app.add_typer(install_app)
app.add_typer(drs_app)
app.add_typer(config_app, name="config")
app.add_typer(offline_app, name="offline")
app.add_typer(clean_app, name="clean")
app.add_typer(test_cv_app, name="test")
app.add_typer(find_app)
app.add_typer(cmor_app)

# maybe remove during a future refactor


@app.command()
def list_projects():
    """List all available projects with their default configurations."""
    default_configs = ServiceSettings._get_default_project_configs()

    table = Table(title="Available Projects")
    table.add_column("Project Name", style="cyan")
    table.add_column("Repository", style="green")
    table.add_column("Default Branch", style="yellow")
    table.add_column("Local Path", style="blue")

    for project_name, config in default_configs.items():
        table.add_row(project_name, config["github_repo"], config["branch"], config["local_path"])

    console.print(table)
    console.print(f"\n[blue]Total: {len(default_configs)} projects available[/blue]")


@app.command()
def version(
    check: bool = typer.Option(False, "--check", "-c", help="Check PyPI for available updates"),
    reset_reminder: bool = typer.Option(False, "--reset-reminder", help="Reset update reminder timer"),
):
    """Show esgvoc version and optionally check for updates."""
    from esgvoc import __version__
    from esgvoc.core.version_checker import get_version_checker

    console.print(f"esgvoc version: [cyan]{__version__}[/cyan]")

    checker = get_version_checker()

    if reset_reminder:
        if checker:
            checker.reset_reminder()
            console.print("[green]Update reminder has been reset.[/green]")
        else:
            console.print("[yellow]Version checker not initialized.[/yellow]")
        return

    if check:
        if checker is None:
            console.print("[yellow]Version checker not initialized.[/yellow]")
            raise typer.Exit(1)

        console.print("\n[dim]Checking for updates...[/dim]")

        # Force a fresh check, bypassing cache intervals
        info = checker.check_now()

        table = Table(title="Version Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Current Version", info["current_version"])
        table.add_row("Latest Version", info["latest_version"] or "Unknown")
        table.add_row("Last Checked", info["last_checked"] or "Never")

        if info["update_available"]:
            table.add_row("Update Available", "[bold green]Yes[/bold green]")
        else:
            table.add_row("Update Available", "[dim]No[/dim]")

        console.print(table)

        if info["update_available"]:
            console.print("\n[yellow]Update using one of:[/yellow]")
            console.print("  pip install --upgrade esgvoc")
            console.print("  uv pip install --upgrade esgvoc")
            console.print("  conda update esgvoc")
            console.print("\n[yellow]After updating, reinstall vocabularies with:[/yellow]")
            console.print("  esgvoc install")


def main():
    app()


if __name__ == "__main__":
    main()
