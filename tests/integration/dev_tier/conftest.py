"""
Shared fixtures for Dev Tier integration tests.

Dev Tier tests use `build_dev` with the real cloned repos (provided by the
session fixture in tests/integration/conftest.py) to build genuine SQLite
databases and validate them.  No mocking of the build pipeline.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


def read_db_metadata(db_path: Path) -> dict[str, str]:
    """Read key-value rows from _esgvoc_metadata."""
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall()
        return dict(rows)
    finally:
        conn.close()


def db_table_names(db_path: Path) -> list[str]:
    """Return all table names in a SQLite database."""
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def db_row_count(db_path: Path, table: str) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
    finally:
        conn.close()
