import typer
from rich.console import Console
from rich.table import Table

from esgvoc.core import service

app = typer.Typer()
console = Console()


def display(table):
    console = Console(record=True, width=200)
    console.print(table)


@app.command()
def status():
    """
    Command to display status
    i.e summary of version of usable ressources (between remote/cached)

    """
    assert service.current_state is not None
    service.current_state.get_state_summary()
    # display(service.state_service.table())

    table = Table(show_header=False, show_lines=True)

    table.add_row("", "Remote github repo", "Local repository", "Cache Database", style="bright_green")
    table.add_row(
        "Universe path",
        service.current_state.universe.github_repo,
        service.current_state.universe.local_path,
        service.current_state.universe.db_path,
        style="white",
    )
    table.add_row(
        "Version",
        service.current_state.universe.github_version,
        service.current_state.universe.local_version,
        service.current_state.universe.db_version,
        style="bright_blue",
    )
    for proj_name, proj in service.current_state.projects.items():
        table.add_row(f"{proj_name} path", proj.github_repo, proj.local_path, proj.db_path, style="white")
        table.add_row("Version", proj.github_version, proj.local_version, proj.db_version, style="bright_blue")
    display(table)
