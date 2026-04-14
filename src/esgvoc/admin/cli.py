"""
Admin CLI commands: esgvoc admin <subcommand>

Commands:
  build           Build a project DB from repos
  build-universe  Build a standalone universe-only DB
  validate        Validate an existing DB file
  test            Quick sanity test on a DB file
  diff            Compare two DB files (metadata + term counts)
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="admin",
    help="Admin tools for building and validating pre-built database artifacts.",
    no_args_is_help=True,
)
console = Console()


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

@app.command()
def build(
    project_path: Optional[Path] = typer.Option(
        None, "--project-path", "-p",
        help="Path to a locally checked-out project CV repo (local or dev mode).",
    ),
    universe_path: Optional[Path] = typer.Option(
        None, "--universe-path", "-u",
        help="Path to a locally checked-out universe repo (dev mode, no clone).",
    ),
    project_repo: Optional[str] = typer.Option(
        None, "--project-repo",
        help="owner/repo or URL of the project CV repo (remote mode).",
    ),
    project_ref: Optional[str] = typer.Option(
        None, "--project-ref",
        help="Branch or tag of the project repo to build from.",
    ),
    universe_repo: Optional[str] = typer.Option(
        None, "--universe-repo",
        help="owner/repo or URL of the universe repo (e.g. WCRP-CMIP/WCRP-universe).",
    ),
    universe_ref: Optional[str] = typer.Option(
        None, "--universe-ref",
        help="Branch or tag of the universe repo (e.g. esgvoc_dev or v1.2.0).",
    ),
    output: Path = typer.Option(
        ..., "--output", "-o",
        help="Output .db file path.",
    ),
    project_id: Optional[str] = typer.Option(
        None, "--project-id",
        help="Override manifest project.id (useful when no esgvoc_manifest.yaml exists).",
    ),
    cv_version: Optional[str] = typer.Option(
        None, "--cv-version",
        help="Override manifest cv_version.",
    ),
    universe_version: Optional[str] = typer.Option(
        None, "--universe-version",
        help="Override manifest universe_version.",
    ),
    esgvoc_min_version: Optional[str] = typer.Option(
        None, "--esgvoc-min-version",
        help="Override esgvoc compatibility min_version.",
    ),
    esgvoc_max_version: Optional[str] = typer.Option(
        None, "--esgvoc-max-version",
        help="Override esgvoc compatibility max_version.",
    ),
    validate: bool = typer.Option(
        False, "--validate",
        help="Run validation suite after build.",
    ),
    fail_on_missing_links: bool = typer.Option(
        False, "--fail-on-missing-links",
        help="Fail if any @id references cannot be resolved.",
    ),
):
    """
    Build a pre-built project database.

    \b
    Dev mode (both repos local, no cloning — useful when repos have no tags yet):
      esgvoc admin build --project-path ./CMIP7-CVs --universe-path ./WCRP-universe --project-id cmip7 --cv-version dev --universe-version dev --output cmip7.db

    \b
    Local mode (project checked out, universe cloned):
      esgvoc admin build --project-path . --universe-repo WCRP-CMIP/WCRP-universe --universe-ref esgvoc_dev --output cmip7.db

    \b
    Remote mode (clone both repos):
      esgvoc admin build --project-repo WCRP-CMIP/CMIP7-CVs --project-ref esgvoc_dev --universe-repo WCRP-CMIP/WCRP-universe --universe-ref esgvoc_dev --output cmip7.db
    """
    from esgvoc.admin.builder import DBBuilder

    builder = DBBuilder(fail_on_missing_links=fail_on_missing_links, verbose=True)

    # Collect manifest overrides from CLI flags
    manifest_overrides: dict = {}
    if project_id:
        manifest_overrides["project_id"] = project_id
    if cv_version:
        manifest_overrides["cv_version"] = cv_version
    if universe_version:
        manifest_overrides["universe_version"] = universe_version
    if esgvoc_min_version:
        manifest_overrides["esgvoc_min_version"] = esgvoc_min_version
    if esgvoc_max_version:
        manifest_overrides["esgvoc_max_version"] = esgvoc_max_version

    try:
        if project_path is not None and universe_path is not None:
            # Dev mode: both repos local, no clone
            result = builder.build_dev(
                project_path=project_path,
                universe_path=universe_path,
                output_path=output,
                manifest_overrides=manifest_overrides or None,
                validate=validate,
            )
        elif project_path is not None:
            # Local mode: project checked out, clone universe
            if not universe_repo or not universe_ref:
                console.print(
                    "[red]Error:[/red] --universe-repo and --universe-ref are required "
                    "when using --project-path without --universe-path."
                )
                raise typer.Exit(1)
            result = builder.build_local(
                project_path=project_path,
                universe_repo=universe_repo,
                universe_ref=universe_ref,
                output_path=output,
                manifest_overrides=manifest_overrides or None,
                validate=validate,
            )
        elif project_repo is not None and project_ref is not None:
            # Remote mode: clone both
            if not universe_repo or not universe_ref:
                console.print(
                    "[red]Error:[/red] --universe-repo and --universe-ref are required "
                    "in remote mode."
                )
                raise typer.Exit(1)
            result = builder.build_remote(
                project_repo=project_repo,
                project_ref=project_ref,
                universe_repo=universe_repo,
                universe_ref=universe_ref,
                output_path=output,
                manifest_overrides=manifest_overrides or None,
                validate=validate,
            )
        else:
            console.print(
                "[red]Error:[/red] Provide one of:\n"
                "  --project-path + --universe-path          (dev mode, fully local)\n"
                "  --project-path + --universe-repo/ref      (local mode)\n"
                "  --project-repo + --project-ref + --universe-repo/ref  (remote mode)"
            )
            raise typer.Exit(1)

        console.print(f"\n[green]{result.summary()}[/green]")

    except Exception as e:
        console.print(f"[red]Build failed:[/red] {e}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# build-universe
# ---------------------------------------------------------------------------

@app.command(name="build-universe")
def build_universe(
    universe_repo: str = typer.Option(
        ..., "--universe-repo",
        help="owner/repo or URL of the universe repo.",
    ),
    universe_ref: str = typer.Option(
        ..., "--universe-ref",
        help="Branch or tag to clone.",
    ),
    output: Path = typer.Option(
        ..., "--output", "-o",
        help="Output .db file path.",
    ),
):
    """Build a standalone universe-only database."""
    from esgvoc.admin.builder import DBBuilder

    builder = DBBuilder(verbose=True)
    try:
        result = builder.build_universe(
            universe_repo=universe_repo,
            universe_ref=universe_ref,
            output_path=output,
        )
        console.print(f"\n[green]{result.summary()}[/green]")
    except Exception as e:
        console.print(f"[red]Build failed:[/red] {e}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@app.command()
def validate(
    db_path: Path = typer.Argument(..., help="Path to the .db file to validate."),
    full: bool = typer.Option(False, "--full", "-f", help="Run extended checks."),
    schema_only: bool = typer.Option(
        False, "--schema-only",
        help="Validate JSON schema of project directory (pass directory, not .db).",
    ),
):
    """
    Validate a pre-built database file.

    \b
    Basic:
      esgvoc admin validate cmip7.db

    \b
    Full:
      esgvoc admin validate --full cmip7.db

    \b
    Schema-only (validate JSON files in a project directory):
      esgvoc admin validate --schema-only /path/to/CMIP7-CVs
    """
    from esgvoc.admin.validator import DBValidator

    validator = DBValidator()

    if schema_only:
        result = validator.validate_schema(db_path)
    else:
        result = validator.validate(db_path, full=full)

    console.print(result.summary())
    if not result.passed:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# test
# ---------------------------------------------------------------------------

@app.command()
def test(
    db_path: Path = typer.Argument(..., help="Path to the .db file to test."),
):
    """Quick sanity test: open the DB and run representative queries."""
    from esgvoc.admin.validator import DBValidator

    console.print(f"Running test suite against [cyan]{db_path}[/cyan]…")
    result = DBValidator().validate(db_path, full=True)
    console.print(result.summary())
    if not result.passed:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------

@app.command()
def diff(
    baseline: Path = typer.Argument(..., help="Baseline .db file."),
    updated: Path = typer.Argument(..., help="Updated .db file to compare against baseline."),
    format: str = typer.Option("text", "--format", help="Output format: text or json."),
):
    """
    Compare two database files: metadata differences and term count changes.

    \b
    Example:
      esgvoc admin diff v2.0.0.db v2.1.0.db
      esgvoc admin diff baseline.db updated.db --format json
    """
    def read_metadata(path: Path) -> dict:
        try:
            with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
                rows = conn.execute(
                    "SELECT key, value FROM _esgvoc_metadata"
                ).fetchall()
                return dict(rows)
        except Exception:
            return {}

    def count_rows(path: Path, table: str) -> int:
        try:
            with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
                return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            return -1

    if not baseline.exists():
        console.print(f"[red]Baseline not found:[/red] {baseline}")
        raise typer.Exit(1)
    if not updated.exists():
        console.print(f"[red]Updated not found:[/red] {updated}")
        raise typer.Exit(1)

    meta_a = read_metadata(baseline)
    meta_b = read_metadata(updated)

    tables = ("universes", "udata_descriptors", "uterms", "pterms", "pcollections")
    counts = {
        t: (count_rows(baseline, t), count_rows(updated, t))
        for t in tables
    }

    if format == "json":
        import json

        out = {
            "baseline": {"path": str(baseline), "metadata": meta_a},
            "updated": {"path": str(updated), "metadata": meta_b},
            "metadata_diff": {
                k: {"baseline": meta_a.get(k), "updated": meta_b.get(k)}
                for k in set(meta_a) | set(meta_b)
                if meta_a.get(k) != meta_b.get(k)
            },
            "row_counts": {
                t: {"baseline": a, "updated": b, "delta": b - a}
                for t, (a, b) in counts.items()
            },
        }
        console.print_json(json.dumps(out, indent=2))
        return

    # Text output
    table = Table(title=f"Diff: {baseline.name} → {updated.name}")
    table.add_column("Key", style="cyan")
    table.add_column("Baseline")
    table.add_column("Updated")

    all_keys = sorted(set(meta_a) | set(meta_b))
    for key in all_keys:
        a, b = meta_a.get(key, "—"), meta_b.get(key, "—")
        style = "yellow" if a != b else ""
        table.add_row(key, a, b, style=style)

    console.print(table)

    count_table = Table(title="Row Counts")
    count_table.add_column("Table", style="cyan")
    count_table.add_column("Baseline", justify="right")
    count_table.add_column("Updated", justify="right")
    count_table.add_column("Delta", justify="right")

    for t, (a, b) in counts.items():
        delta = b - a if a >= 0 and b >= 0 else "?"
        delta_str = f"+{delta}" if isinstance(delta, int) and delta > 0 else str(delta)
        style = "green" if isinstance(delta, int) and delta > 0 else (
            "red" if isinstance(delta, int) and delta < 0 else ""
        )
        count_table.add_row(t, str(a), str(b), delta_str, style=style)

    console.print(count_table)
