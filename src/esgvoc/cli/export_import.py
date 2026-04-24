"""
esgvoc export / esgvoc import — Air-Gapped Bundle

Export installed databases and state into a portable .tar.gz bundle that can
be transferred to an offline machine and imported there.

Bundle layout inside the tar.gz:
    manifest.json          — bundle metadata (version, created_at, projects)
    state.json             — active-version mappings from UserState
    dbs/
        cmip6-v1.0.0.db   — one file per exported version
        ...

Usage:
    esgvoc export --all --output bundle.tar.gz
    esgvoc export cmip6 cmip7 --output bundle.tar.gz
    esgvoc import /media/usb/bundle.tar.gz
"""

from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console

app = typer.Typer()
console = Console()

_BUNDLE_FORMAT_VERSION = "1"


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

@app.command("export")
def export_cmd(
    projects: Optional[List[str]] = typer.Argument(
        None,
        help="Projects to export (e.g. 'cmip6 cmip7').  Defaults to all installed.",
    ),
    output: Path = typer.Option(
        ..., "--output", "-o",
        help="Output bundle path, e.g. bundle.tar.gz",
    ),
    all_projects: bool = typer.Option(
        False, "--all",
        help="Export all installed projects (overrides positional arguments).",
    ),
    include_cache: bool = typer.Option(
        True, "--include-cache/--no-cache",
        help="Include the registry cache file in the bundle.",
    ),
):
    """
    Export installed databases to a portable bundle for air-gapped transfer.

    \b
    Examples:
      esgvoc export --all --output bundle.tar.gz
      esgvoc export cmip6 cmip7 --output cmip7-bundle.tar.gz
    """
    import esgvoc
    from esgvoc.core.service.configuration.home import EsgvocHome
    from esgvoc.core.service.user_state import UserState

    state = UserState.load()
    home = EsgvocHome.resolve()

    # Determine which projects to export
    if all_projects or not projects:
        project_ids = state.all_project_ids()
    else:
        project_ids = list(projects)

    if not project_ids:
        console.print("[yellow]No installed projects found. Nothing to export.[/yellow]")
        raise typer.Exit(0)

    # Collect DB files to include
    entries: list[dict] = []
    missing: list[str] = []
    for pid in project_ids:
        for ver in state.get_installed(pid):
            db = UserState.db_path(pid, ver)
            if db.exists():
                entries.append({
                    "project_id": pid,
                    "version": ver,
                    "active": state.get_active(pid) == ver,
                    "filename": db.name,
                    "_path": db,
                })
            else:
                missing.append(f"{pid}@{ver}")

    if missing:
        console.print(
            f"[yellow]Warning:[/yellow] DB files missing on disk (skipped): {', '.join(missing)}"
        )

    if not entries:
        console.print("[red]No DB files found to export.[/red]")
        raise typer.Exit(1)

    # Build the bundle in a temp directory then move atomically
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "esgvoc_bundle_version": _BUNDLE_FORMAT_VERSION,
        "esgvoc_version": getattr(esgvoc, "__version__", "unknown"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "projects": [
            {k: v for k, v in e.items() if not k.startswith("_")}
            for e in entries
        ],
    }

    console.print(f"Exporting {len(entries)} database(s)…")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        dbs_dir = tmp_path / "dbs"
        dbs_dir.mkdir()

        # Copy DB files
        for entry in entries:
            src: Path = entry["_path"]
            dst = dbs_dir / entry["filename"]
            shutil.copy2(str(src), str(dst))
            mb = src.stat().st_size / 1_048_576
            console.print(f"  + {entry['filename']} ({mb:.1f} MB)")

        # Write manifest
        (tmp_path / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        # Write state.json snapshot
        (tmp_path / "state.json").write_text(
            json.dumps(state.dump(), indent=2), encoding="utf-8"
        )

        # Optionally include registry cache
        if include_cache:
            cache_file = home.user_cache_dir / "registry_cache.json"
            if cache_file.exists():
                shutil.copy2(str(cache_file), str(tmp_path / "registry_cache.json"))

        # Create the tar.gz
        with tarfile.open(str(output), "w:gz") as tar:
            tar.add(str(tmp_path), arcname="")

    total_mb = output.stat().st_size / 1_048_576
    console.print(f"[green]Created:[/green] {output} ({total_mb:.1f} MB)")


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------

@app.command("import")
def import_cmd(
    bundle: Path = typer.Argument(
        ...,
        help="Path to a bundle file produced by 'esgvoc export'.",
    ),
    activate: bool = typer.Option(
        True, "--activate/--no-activate",
        help="Set imported versions as active (mirrors the bundle's active_versions).",
    ),
    offline: bool = typer.Option(
        False, "--offline/--no-offline",
        help="Persist offline mode after import (useful on air-gapped machines).",
    ),
    force: bool = typer.Option(
        False, "--force",
        help="Overwrite existing DB files even when they already exist.",
    ),
):
    """
    Import a database bundle produced by 'esgvoc export'.

    \b
    Example:
      esgvoc import /media/usb/bundle.tar.gz
    """
    from esgvoc.core.service.configuration.home import EsgvocHome
    from esgvoc.core.service.user_state import UserState

    bundle = Path(bundle)
    if not bundle.exists():
        console.print(f"[red]Bundle not found:[/red] {bundle}")
        raise typer.Exit(1)

    console.print(f"Importing bundle [cyan]{bundle}[/cyan]…")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Extract bundle
        try:
            with tarfile.open(str(bundle), "r:gz") as tar:
                tar.extractall(str(tmp_path))
        except (tarfile.TarError, OSError) as e:
            console.print(f"[red]Failed to extract bundle:[/red] {e}")
            raise typer.Exit(1) from None from None

        # Validate manifest
        manifest_file = tmp_path / "manifest.json"
        if not manifest_file.exists():
            console.print("[red]Invalid bundle:[/red] manifest.json not found.")
            raise typer.Exit(1) from None

        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid bundle manifest:[/red] {e}")
            raise typer.Exit(1) from None

        fmt_ver = manifest.get("esgvoc_bundle_version")
        if fmt_ver != _BUNDLE_FORMAT_VERSION:
            console.print(
                f"[yellow]Warning:[/yellow] bundle format version '{fmt_ver}' "
                f"(expected '{_BUNDLE_FORMAT_VERSION}'). Proceeding anyway."
            )

        projects_meta: list[dict] = manifest.get("projects", [])
        if not projects_meta:
            console.print("[yellow]Bundle contains no projects.[/yellow]")
            raise typer.Exit(0)

        # Load or read bundle's state.json for active-version info
        bundle_state_file = tmp_path / "state.json"
        bundle_state: dict = {}
        if bundle_state_file.exists():
            try:
                bundle_state = json.loads(bundle_state_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

        bundle_active: dict[str, str] = bundle_state.get("active_versions", {})

        # Copy DB files into the user tier store
        state = UserState.load()
        home = EsgvocHome.resolve()
        dbs_src = tmp_path / "dbs"

        imported = []
        skipped = []
        for meta in projects_meta:
            pid = meta["project_id"]
            ver = meta["version"]
            fname = meta["filename"]
            src = dbs_src / fname
            dst = UserState.db_path(pid, ver)

            if not src.exists():
                console.print(f"  [yellow]skip[/yellow] {fname} (not found in bundle)")
                continue

            if dst.exists() and not force:
                console.print(f"  [dim]skip[/dim] {pid}@{ver} (already on disk)")
                state.add_installed(pid, ver)
                skipped.append((pid, ver))
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(dst))
                state.add_installed(pid, ver)
                mb = dst.stat().st_size / 1_048_576
                console.print(f"  [green]+[/green] {pid}@{ver} ({mb:.1f} MB)")
                imported.append((pid, ver))

        # Apply active-version mappings from the bundle (if --activate)
        if activate:
            for pid, ver in imported + skipped:
                if bundle_active.get(pid) == ver:
                    state.set_active(pid, ver)

        state.save()

        # Optionally restore registry cache
        cache_src = tmp_path / "registry_cache.json"
        if cache_src.exists():
            cache_dst = home.user_cache_dir / "registry_cache.json"
            shutil.copy2(str(cache_src), str(cache_dst))
            console.print("  [dim]registry cache restored[/dim]")

    # Summary
    total = len(imported) + len(skipped)
    console.print(
        f"\n[green]Done.[/green] {total} project version(s) ready "
        f"({len(imported)} imported, {len(skipped)} already present)."
    )

    if offline:
        console.print(
            "\n[yellow]Tip:[/yellow] To force offline mode for all commands use: "
            "esgvoc offline enable"
        )
