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

    # Check for offline mode components and display summary
    offline_components = []
    if service.current_state.universe.offline_mode:
        offline_components.append("universe")
    for project_name, project in service.current_state.projects.items():
        if project.offline_mode:
            offline_components.append(project_name)

    if offline_components:
        console.print(f"[yellow]Offline mode enabled for: {', '.join(offline_components)}[/yellow]")

    table = Table(show_header=False, show_lines=True)

    table.add_row("", "Remote github repo", "Local repository", "Cache Database", "Offline Mode", style="bright_green")

    # Universe row
    universe_offline_status = "✓" if service.current_state.universe.offline_mode else "✗"
    table.add_row(
        "Universe path",
        service.current_state.universe.github_repo,
        service.current_state.universe.local_path,
        service.current_state.universe.db_path,
        universe_offline_status,
        style="white",
    )
    table.add_row(
        "Version",
        service.current_state.universe.github_version or "N/A",
        service.current_state.universe.local_version or "N/A",
        service.current_state.universe.db_version or "N/A",
        "",
        style="bright_blue",
    )

    # Projects rows
    for proj_name, proj in service.current_state.projects.items():
        proj_offline_status = "✓" if proj.offline_mode else "✗"
        table.add_row(
            f"{proj_name} path",
            proj.github_repo,
            proj.local_path,
            proj.db_path,
            proj_offline_status,
            style="white"
        )
        table.add_row(
            "Version",
            proj.github_version or "N/A",
            proj.local_version or "N/A",
            proj.db_version or "N/A",
            "",
            style="bright_blue"
        )
    display(table)
