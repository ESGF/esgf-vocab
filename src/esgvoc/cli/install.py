import typer
from esgvoc.core.service import current_state

app = typer.Typer()

@app.command()
def install():
    """Initialize default config and apply settings"""
    try:
        typer.echo("Initialized default configuration")
        current_state.synchronize_all()

        # Ensure versions are properly fetched after synchronization
        current_state.fetch_versions()
        current_state.get_state_summary()

        # Display final status after installation
        from rich.console import Console
        console = Console()
        typer.echo("\nInstallation completed. Final status:")
        console.print(current_state.table())

    except Exception as e:
        typer.echo(f"Error during installation: {str(e)}", err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
