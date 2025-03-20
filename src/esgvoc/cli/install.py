import typer
from esgvoc.core.service import current_state

app = typer.Typer()

@app.command()
def install():
    """Initialize default config and apply settings"""
    try:
        typer.echo("Initialized default configuration")
        current_state.synchronize_all()
    except Exception as e:
        typer.echo(f"Error during installation: {str(e)}", err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
