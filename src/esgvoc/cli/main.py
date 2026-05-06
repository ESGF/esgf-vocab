import typer
from rich.console import Console

from esgvoc.admin.cli import app as admin_app
from esgvoc.cli.clean import app as clean_app
from esgvoc.cli.drs import app as drs_app
from esgvoc.cli.export_import import app as export_import_app
from esgvoc.cli.find import app as find_app
from esgvoc.cli.get import app as get_app
from esgvoc.cli.install import app as install_app
from esgvoc.cli.offline import app as offline_app
from esgvoc.cli.remove import app as remove_app
from esgvoc.cli.schema import app as schema_app
from esgvoc.cli.status import app as status_app
from esgvoc.cli.test_cv import app as test_cv_app
from esgvoc.cli.update import app as update_app
from esgvoc.cli.use import app as use_app
from esgvoc.cli.valid import app as valid_app
from esgvoc.cli.versions import app as versions_app

app = typer.Typer()
console = Console()

# Register the subcommands
app.add_typer(export_import_app)
app.add_typer(get_app)
app.add_typer(status_app)
app.add_typer(valid_app)
app.add_typer(install_app)
app.add_typer(drs_app)
app.add_typer(offline_app, name="offline")
app.add_typer(clean_app, name="clean")
app.add_typer(find_app)
app.add_typer(schema_app)
app.add_typer(admin_app, name="admin")
app.add_typer(use_app)
app.add_typer(versions_app)
app.add_typer(remove_app)
app.add_typer(update_app)
app.add_typer(test_cv_app)


@app.command()
def version():
    """Show esgvoc version."""
    from esgvoc import __version__

    console.print(f"esgvoc version: [cyan]{__version__}[/cyan]")


def main():
    app()


if __name__ == "__main__":
    main()
