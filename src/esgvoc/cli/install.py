import typer
from rich.console import Console

from esgvoc.api import install as api_install
from esgvoc.core.service import current_state

app = typer.Typer()

@app.command()
def install(
    fail_on_missing_links: bool = typer.Option(
        False,
        "--fail-on-missing-links",
        help="Exit with code -1 if any @id references cannot be resolved during database population.",
    ),
):
    """Initialize default config and apply settings"""
    try:
        typer.echo("Initialized default configuration")

        # Check if any components are in offline mode
        offline_components = []
        if current_state.universe.offline_mode:
            offline_components.append("universe")
        for project_name, project in current_state.projects.items():
            if project.offline_mode:
                offline_components.append(project_name)

        if offline_components:
            typer.echo(f"Note: The following components are in offline mode: {', '.join(offline_components)}")
            typer.echo("Only local repositories and databases will be used.")

        result = api_install(fail_on_missing_links=fail_on_missing_links)

        current_state.get_state_summary()

        # Display final status after installation
        console = Console()
        typer.echo("\nInstallation completed. Final status:")
        console.print(current_state.table())

        # Exit with code -1 if missing links were found
        if result != 0:
            raise typer.Exit(result)

    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"Error during installation: {str(e)}", err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
