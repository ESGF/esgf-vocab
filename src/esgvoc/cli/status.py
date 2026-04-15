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
def status(
    paths: bool = typer.Option(False, "--paths", help="Show full filesystem paths."),
    user: bool = typer.Option(False, "--user", help="Show only User Tier (pre-built DBs)."),
    dev: bool = typer.Option(False, "--dev", help="Show only Dev Tier (source-based config)."),
):
    """
    Show status of installed vocabularies.

    \b
    Displays two tiers:
      User Tier — pre-built DB artifacts installed via 'esgvoc install'
      Dev Tier  — source-based config installed via 'esgvoc install' (no args)
    """
    show_user = user or not dev
    show_dev = dev or not user

    if show_user:
        _print_user_tier(paths=paths)

    if show_dev:
        _print_dev_tier(paths=paths)


def _print_user_tier(*, paths: bool) -> None:
    """Print User Tier status: installed pre-built DB artifacts."""
    from esgvoc.core.service.user_state import UserState

    state = UserState.load()
    project_ids = state.all_project_ids()

    table = Table(title="[bold cyan]User Tier[/bold cyan] — pre-built DB artifacts", show_lines=True)
    table.add_column("Project", style="cyan")
    table.add_column("Active", style="green")
    table.add_column("Installed versions")
    if paths:
        table.add_column("DB path")

    if not project_ids:
        console.print(
            "[dim]User Tier: no projects installed. "
            "Run: esgvoc install <project>[/dim]\n"
        )
        return

    for pid in sorted(project_ids):
        active = state.get_active(pid) or "—"
        installed = state.get_installed(pid)
        versions_str = ", ".join(
            f"[bold]{v}[/bold]" if v == state.get_active(pid) else v
            for v in installed
        )
        if paths:
            active_ver = state.get_active(pid)
            db = str(UserState.db_path(pid, active_ver)) if active_ver else "—"
            exists = "✓" if active_ver and UserState.db_path(pid, active_ver).exists() else "✗"
            table.add_row(pid, active, versions_str, f"{exists} {db}")
        else:
            table.add_row(pid, active, versions_str)

    display(table)
    console.print()


def _print_dev_tier(*, paths: bool) -> None:
    """Print Dev Tier status: source-based config (existing behaviour)."""
    assert service.current_state is not None
    service.current_state.get_state_summary()

    offline_components = []
    if service.current_state.universe.offline_mode:
        offline_components.append("universe")
    for project_name, project in service.current_state.projects.items():
        if project.offline_mode:
            offline_components.append(project_name)

    if offline_components:
        console.print(
            f"[yellow]Dev Tier — offline mode enabled for: {', '.join(offline_components)}[/yellow]"
        )

    table = Table(
        title="[bold yellow]Dev Tier[/bold yellow] — source-based config",
        show_header=False,
        show_lines=True,
    )

    table.add_row(
        "", "Remote github repo", "Local repository", "Cache Database", "Offline Mode",
        style="bright_green",
    )

    universe_offline_status = "✓" if service.current_state.universe.offline_mode else "✗"
    table.add_row(
        "Universe path",
        service.current_state.universe.github_repo,
        service.current_state.universe.local_path if paths else _shorten(service.current_state.universe.local_path),
        service.current_state.universe.db_path if paths else _shorten(service.current_state.universe.db_path),
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

    for proj_name, proj in service.current_state.projects.items():
        proj_offline_status = "✓" if proj.offline_mode else "✗"
        table.add_row(
            f"{proj_name} path",
            proj.github_repo,
            proj.local_path if paths else _shorten(proj.local_path),
            proj.db_path if paths else _shorten(proj.db_path),
            proj_offline_status,
            style="white",
        )
        table.add_row(
            "Version",
            proj.github_version or "N/A",
            proj.local_version or "N/A",
            proj.db_version or "N/A",
            "",
            style="bright_blue",
        )

    display(table)


def _shorten(path: str | None, max_len: int = 40) -> str:
    """Truncate a long path for display, keeping the tail."""
    if not path:
        return "N/A"
    if len(path) <= max_len:
        return path
    return "…" + path[-(max_len - 1):]
