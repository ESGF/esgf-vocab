"""
Shared fixtures for User Tier integration tests.

Each test runs in an isolated ESGVOC_HOME (tmp_path) so it never touches
the real user home directory.

The central helper is `fetcher_that_copies`: it patches DBFetcher so that
`download_db` copies a real locally-built SQLite file instead of downloading
from GitHub.  All other CLI/state behaviour is real.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from esgvoc.core.db_artifact import DBArtifact

runner = CliRunner()


# ---------------------------------------------------------------------------
# Environment isolation  (applied automatically to every test in this package)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """
    Route all UserState / EsgvocHome operations to a private temp directory.
    ESGVOC_OFFLINE is cleared so only tests that explicitly need offline mode
    set it themselves.
    """
    monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
    monkeypatch.delenv("ESGVOC_OFFLINE", raising=False)
    yield tmp_path


# ---------------------------------------------------------------------------
# Mock fetcher that copies a real local DB file
# ---------------------------------------------------------------------------

def fetcher_that_copies(real_db_path: Path, project_id: str, version: str):
    """
    Return (ctx_manager, mock_instance, artifact) that replaces DBFetcher.

    When the CLI calls `fetcher.download_db(artifact, target)`, the mock copies
    `real_db_path` to `target` — exactly as a real download would, but local.

    The artifact carries the real SHA-256 of `real_db_path`, so checksum
    verification inside the CLI (if any) will pass.

    Usage:
        ctx, mock_inst, artifact = fetcher_that_copies(v1_path, "cmip6", "v1.0.0")
        with ctx:
            result = runner.invoke(install_app, ["cmip6@v1.0.0"])
        mock_inst.download_db.assert_called_once()
    """
    checksum = hashlib.sha256(real_db_path.read_bytes()).hexdigest()
    size = real_db_path.stat().st_size

    artifact = DBArtifact(
        project_id=project_id,
        version=version,
        download_url=f"https://example.com/{project_id}-{version}.db",
        checksum_sha256=checksum,
        size_bytes=size,
        is_prerelease=False,
    )

    mock_inst = MagicMock()
    mock_inst.get_artifact.return_value = artifact
    mock_inst.list_versions.return_value = [version]

    def _copy(art, target, show_progress=True, **kw):
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(real_db_path), str(target))

    mock_inst.download_db.side_effect = _copy

    ctx = patch("esgvoc.core.db_fetcher.DBFetcher", return_value=mock_inst)
    return ctx, mock_inst, artifact


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def install_real_db(real_db_path: Path, project_id: str, version: str) -> Path:
    """
    Copy a real DB file into the User Tier store and register it in state.json.
    Returns the path where the DB was installed.
    """
    from esgvoc.core.service.user_state import UserState

    state = UserState.load()
    db = UserState.db_path(project_id, version)
    db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(real_db_path), str(db))
    state.add_installed(project_id, version)
    state.set_active(project_id, version)
    state.save()
    return db


def read_db_metadata(db_path: Path) -> dict[str, str]:
    """Read key-value rows from _esgvoc_metadata table in a SQLite DB."""
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall()
        return dict(rows)
    finally:
        conn.close()


def db_is_valid_sqlite(db_path: Path) -> bool:
    """Return True if path is a readable, non-corrupt SQLite database."""
    import sqlite3

    if not db_path.exists() or db_path.stat().st_size == 0:
        return False
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        return True
    except sqlite3.DatabaseError:
        return False
