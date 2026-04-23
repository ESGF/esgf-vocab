"""
esgvoc test — sanity-test a remote CV branch before building the registry artifact.

Usage:
    esgvoc test run cmip6plus --branch esgvoc_dev --universe-branch esgvoc_dev
    esgvoc test run cmip7 --branch main --universe-branch esgvoc_dev
    esgvoc test run myproject --repo myorg/MyProject-CVs --branch feature-x \\
        --universe-repo WCRP-CMIP/WCRP-universe --universe-branch esgvoc_dev

What it does
------------
1. Clones the project repo + universe repo (same as `esgvoc admin build`).
2. Builds a temporary .db in a temp dir; validates missing links (fails on any).
3. Installs the temp DB under the name '_test_run_temp' and activates it.
4. Runs an API smoke test: list collections + spot-check a few terms.
5. Cleans up (removes temp DB and pointer file).

Exit code 0 = everything OK; 1 = any failure.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="test",
    help="Sanity-test a remote CV branch before building the registry artifact.",
    no_args_is_help=True,
)
console = Console()

# ---------------------------------------------------------------------------
# Known default repos (can be overridden with --repo / --universe-repo)
# ---------------------------------------------------------------------------

_UNIVERSE_REPO = "WCRP-CMIP/WCRP-universe"

_PROJECT_REPOS: dict[str, str] = {
    "universe": "WCRP-CMIP/WCRP-universe",
    "cmip7": "WCRP-CMIP/CMIP7-CVs",
    "cmip6plus": "WCRP-CMIP/CMIP6Plus_Cvs",
    "cmip6": "WCRP-CMIP/CMIP6_Cvs",
    "input4mips": "PCMDI/input4MIPs_Cvs",
    "obs4ref": "Climate-REF/Obs4REF_CVs",
    "cordex-cmip6": "WCRP-CORDEX/cordex-cmip6-cv",
}

_TEMP_VERSION_NAME = "_test_run_temp"


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------


@app.command()
def run(
    project_id: str = typer.Argument(
        ...,
        help="Project ID, e.g. 'cmip6plus', 'cmip7'. Must match the DB project_id.",
    ),
    branch: str = typer.Option(
        ...,
        "--branch",
        "-b",
        help="Branch (or tag/SHA) of the project CV repo to test.",
    ),
    universe_branch: str = typer.Option(
        "esgvoc",
        "--universe-branch",
        "-U",
        help="Branch (or tag/SHA) of the universe repo. Defaults to 'esgvoc'.",
    ),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        help=("owner/repo of the project CV repo. Auto-detected for known projects; required for custom ones."),
    ),
    universe_repo: str = typer.Option(
        _UNIVERSE_REPO,
        "--universe-repo",
        help=f"owner/repo of the universe repo. Defaults to '{_UNIVERSE_REPO}'.",
    ),
    project_id_override: Optional[str] = typer.Option(
        None,
        "--project-id",
        help=(
            "Override the project_id embedded in the DB manifest "
            "(useful when the manifest uses a different id than the CLI argument)."
        ),
    ),
    keep: bool = typer.Option(
        False,
        "--keep",
        help="Keep the temp DB installed after the test (useful for manual inspection).",
    ),
    no_api_test: bool = typer.Option(
        False,
        "--no-api-test",
        help="Skip the API smoke test (just validate the build).",
    ),
):
    """
    Sanity-test a remote CV branch before building the registry artifact.

    \b
    Examples:
      esgvoc test run cmip6plus --branch esgvoc_dev --universe-branch esgvoc_dev
      esgvoc test run cmip7 --branch main --universe-branch esgvoc_dev
      esgvoc test run myproject --repo myorg/MyProject-CVs --branch feature-x \\
          --universe-repo WCRP-CMIP/WCRP-universe --universe-branch esgvoc_dev
    """
    # ------------------------------------------------------------------
    # Resolve project repo
    # ------------------------------------------------------------------
    if repo is None:
        if project_id in _PROJECT_REPOS:
            repo = _PROJECT_REPOS[project_id]
        else:
            console.print(f"[red]Unknown project '{project_id}'. Provide --repo owner/repo explicitly.[/red]")
            console.print(f"[dim]Known projects: {', '.join(sorted(_PROJECT_REPOS))}[/dim]")
            raise typer.Exit(1)

    manifest_overrides: dict = {}
    if project_id_override:
        manifest_overrides["project_id"] = project_id_override

    console.print(f"\n[bold cyan]esgvoc test run[/bold cyan]")
    console.print(f"  Project repo   : [cyan]{repo}[/cyan] @ [yellow]{branch}[/yellow]")
    console.print(f"  Universe repo  : [cyan]{universe_repo}[/cyan] @ [yellow]{universe_branch}[/yellow]")
    console.print()

    # ------------------------------------------------------------------
    # Step 1: build
    # ------------------------------------------------------------------
    tmp_dir = Path(tempfile.mkdtemp(prefix="esgvoc_test_"))
    tmp_db = tmp_dir / f"{project_id}_test.db"

    console.rule("[bold]Step 1/3  Build")

    try:
        from esgvoc.admin.builder import DBBuilder

        builder = DBBuilder(fail_on_missing_links=True, verbose=True)
        result = builder.build_remote(
            project_repo=repo,
            project_ref=branch,
            universe_repo=universe_repo,
            universe_ref=universe_branch,
            output_path=tmp_db,
            manifest_overrides=manifest_overrides or None,
        )
    except Exception as exc:
        console.print(f"\n[bold red]BUILD FAILED[/bold red]: {exc}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise typer.Exit(1)

    console.print(f"\n[green]Build OK[/green] → {result.summary()}")

    if no_api_test:
        if not keep:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        else:
            console.print(f"[dim]Temp DB kept at: {tmp_db}[/dim]")
        console.print("\n[bold green]PASS[/bold green]")
        return

    # ------------------------------------------------------------------
    # Step 2: install temp DB
    # ------------------------------------------------------------------
    console.rule("[bold]Step 2/3  Install temp DB")

    from esgvoc.core.service.user_state import UserState

    effective_project_id = project_id_override or project_id
    target = UserState.db_path(effective_project_id, _TEMP_VERSION_NAME)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(tmp_db), str(target))
    console.print(f"Installed as [cyan]{effective_project_id}@{_TEMP_VERSION_NAME}[/cyan]")

    # Remember what was active before so we can restore it
    state = UserState.load()
    previous_active = state.get_active(effective_project_id)

    state.set_active(effective_project_id, _TEMP_VERSION_NAME, source="local")
    console.print(f"Activated [cyan]{effective_project_id}@{_TEMP_VERSION_NAME}[/cyan]")

    api_ok = False
    try:
        # ------------------------------------------------------------------
        # Step 3: API smoke test
        # ------------------------------------------------------------------
        console.rule("[bold]Step 3/3  API smoke test")
        api_ok = _api_smoke_test(effective_project_id)
    finally:
        # ------------------------------------------------------------------
        # Cleanup
        # ------------------------------------------------------------------
        if not keep:
            # Restore previous active (or clear it)
            if previous_active:
                state.set_active(effective_project_id, previous_active, source="local")
            else:
                state.remove_active(effective_project_id)

            # Remove temp DB file
            target.unlink(missing_ok=True)
            # Clean up project dir if now empty
            try:
                target.parent.rmdir()
            except OSError:
                pass

            shutil.rmtree(tmp_dir, ignore_errors=True)
            console.print(f"\n[dim]Temp DB cleaned up.[/dim]")
        else:
            console.print(f"\n[dim]Temp DB kept at: {target}[/dim]")

    if api_ok:
        console.print("\n[bold green]PASS[/bold green]  — source is well-formed, ready for admin build workflow.")
    else:
        console.print("\n[bold red]FAIL[/bold red]  — API smoke test reported errors (see above).")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# API smoke test helper
# ---------------------------------------------------------------------------


def _api_smoke_test(project_id: str) -> bool:
    """
    Run representative esgvoc API queries against the currently active DB.
    Returns True if all checks pass.
    """
    import esgvoc.api as ev

    errors: list[str] = []

    # 1. List collections
    try:
        collections = ev.get_all_collections_in_project(project_id)
        console.print(f"  [green]✓[/green] {len(collections)} collections found")
    except Exception as exc:
        errors.append(f"get_all_collections_in_project: {exc}")
        console.print(f"  [red]✗[/red] get_all_collections_in_project: {exc}")
        # Can't continue without collections
        _print_api_summary(errors)
        return False

    # 2. Spot-check terms in the first few collections
    table = Table(title=f"Collection summary — {project_id}")
    table.add_column("Collection", style="cyan")
    table.add_column("Terms", justify="right")
    table.add_column("Status")

    spot_limit = 5  # Check up to this many collections in detail
    for coll_name in collections[:spot_limit]:
        try:
            terms = ev.get_all_terms_in_collection(project_id, coll_name)
            table.add_row(coll_name, str(len(terms)), "[green]OK[/green]")
        except Exception as exc:
            table.add_row(coll_name, "?", f"[red]ERROR: {exc}[/red]")
            errors.append(f"get_all_terms_in_collection({coll_name!r}): {exc}")

    if len(collections) > spot_limit:
        table.add_row(f"… {len(collections) - spot_limit} more", "", "[dim]not spot-checked[/dim]")

    console.print(table)

    # 3. Instantiate one term from the first collection (if any)
    if collections:
        first_coll = collections[0]
        try:
            terms = ev.get_all_terms_in_collection(project_id, first_coll)
            if terms:
                term = terms[0]
                console.print(
                    f"  [green]✓[/green] Instantiated term: [cyan]{first_coll}/{term.id}[/cyan] (type={term.type})"
                )
            else:
                console.print(f"  [yellow]⚠[/yellow] Collection '{first_coll}' is empty")
        except Exception as exc:
            errors.append(f"instantiate first term in {first_coll!r}: {exc}")
            console.print(f"  [red]✗[/red] Instantiate term: {exc}")

    _print_api_summary(errors)
    return len(errors) == 0


def _print_api_summary(errors: list[str]) -> None:
    if errors:
        console.print(f"\n[red]{len(errors)} API error(s):[/red]")
        for e in errors:
            console.print(f"  • {e}")
    else:
        console.print("\n  [green]All API checks passed.[/green]")
