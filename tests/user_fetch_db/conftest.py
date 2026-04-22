"""
Shared fixtures for user_fetch_db tests.

Every test runs in an isolated ESGVOC_HOME so it never touches the developer's
real installation.
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Route all UserState / EsgvocHome calls to a private tmp directory."""
    monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
    monkeypatch.delenv("ESGVOC_OFFLINE", raising=False)
    monkeypatch.delenv("ESGVOC_DB_DIR", raising=False)
    yield tmp_path


@pytest.fixture
def minimal_db(tmp_path) -> Path:
    """
    Create a minimal valid SQLite database with _esgvoc_metadata table.
    Useful for tests that need a real DB file without building one.
    """
    db_path = tmp_path / "minimal.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE _esgvoc_metadata (key TEXT PRIMARY KEY, value TEXT)"
    )
    conn.executemany(
        "INSERT INTO _esgvoc_metadata VALUES (?, ?)",
        [
            ("project_id", "testproject"),
            ("cv_version", "1.0.0"),
            ("universe_version", "1.0.0"),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


def make_db(path: Path, project_id: str = "testproject", version: str = "1.0.0") -> Path:
    """Helper: create a minimal SQLite DB at *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE _esgvoc_metadata (key TEXT PRIMARY KEY, value TEXT)"
    )
    conn.executemany(
        "INSERT INTO _esgvoc_metadata VALUES (?, ?)",
        [("project_id", project_id), ("cv_version", version)],
    )
    conn.commit()
    conn.close()
    return path


def sha256(path: Path) -> str:
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return h
