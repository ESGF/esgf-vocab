"""
esgvoc status

Show status of all installed project databases.

Reads from the filesystem (per-project subdirs) and pointer files.
No state.json reconciliation required.
"""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


@app.command()
def status(
    paths: bool = typer.Option(False, "--paths", help="Show full filesystem paths."),
):
    """Show status of installed vocabularies."""
    from esgvoc.core.service.user_state import UserState

    state = UserState.load()
    project_ids = state.all_project_ids()

    if not project_ids:
        console.print(
            "[dim]No projects installed.\n"
            "Run: esgvoc use <project>@latest[/dim]"
        )
        return

    table = Table(title="Installed Vocabularies", show_lines=True)
    table.add_column("Project", style="cyan")
    table.add_column("Active", style="green")
    table.add_column("Source", style="dim")
    table.add_column("Installed versions")
    if paths:
        table.add_column("DB path")

    for pid in sorted(project_ids):
        active = state.get_active(pid) or "—"
        source = state.get_active_source(pid) or "—"
        installed = state.get_installed(pid)
        versions_str = ", ".join(
            f"[bold]{v}[/bold]" if v == active else v
            for v in installed
        )

        if paths:
            active_ver = state.get_active(pid)
            if active_ver:
                db = str(UserState.db_path(pid, active_ver))
                exists_mark = "✓" if UserState.db_path(pid, active_ver).exists() else "✗"
                path_cell = f"{exists_mark} {db}"
            else:
                path_cell = "—"
            table.add_row(pid, active, source, versions_str, path_cell)
        else:
            table.add_row(pid, active, source, versions_str)

    console.print(table)
