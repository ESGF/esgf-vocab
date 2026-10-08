"""
Compatibility between a project database and the installed esgvoc.

A database file must first be a valid esgvoc database: an empty or damaged file
would otherwise only fail later, on the first query, with "no such table".

Each database embeds the ``esgvoc_min_version`` of its CV (``esgvoc.min_version`` in
``esgvoc_manifest.yaml``, default: the esgvoc version that built it) in its
``_esgvoc_metadata`` table. A database requiring a more recent esgvoc must not be used,
as its content may not be readable by the installed esgvoc.
"""

from __future__ import annotations

import functools
import logging
import sqlite3
from pathlib import Path

import esgvoc
from esgvoc.core.db_fetcher import DBFetcher, _parse_version
from esgvoc.core.db_snapshot import DBSnapshot
from esgvoc.core.exceptions import EsgvocDbError, EsgvocIncompatibleDBError

_LOGGER = logging.getLogger(__name__)


@functools.lru_cache(maxsize=None)
def _read_db_file_problem(db_path: str, mtime_ns: int, size: int, terms_table: str) -> str | None:
    # mtime_ns and size only invalidate the cache when the file is replaced.
    if size == 0:
        return "the file is empty"
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (terms_table,)
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error as e:
        return f"the file is not a valid SQLite database ({e})"
    return None if row else f"it has no '{terms_table}' table"


def db_file_problem_message(project_id: str, version: str, db_path: Path) -> str | None:
    """
    Return a message explaining why *db_path* is not a usable esgvoc database of
    *project_id* (empty, not SQLite, or without terms table), or None if it is usable.
    """
    terms_table = "uterms" if project_id == "universe" else "pterms"
    stat = db_path.stat()
    problem = _read_db_file_problem(str(db_path), stat.st_mtime_ns, stat.st_size, terms_table)
    if problem is None:
        return None
    return (
        f"{project_id}@{version} is not a valid esgvoc database: {problem}.\n"
        f"  File: {db_path}\n"
        f"Reinstall it: 'esgvoc use {project_id}@{version}' re-downloads a registry version; "
        f"rebuild and 'esgvoc admin install' a local one."
    )


def check_db_file(project_id: str, version: str, db_path: Path) -> None:
    """
    :raises EsgvocDbError: If *db_path* is empty, not a SQLite database, or has no terms table.
    """
    if message := db_file_problem_message(project_id, version, db_path):
        raise EsgvocDbError(message)


@functools.lru_cache(maxsize=None)
def _read_min_version(db_path: str, mtime_ns: int) -> str | None:
    # mtime_ns only invalidates the cache when the file is replaced.
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            row = conn.execute("SELECT value FROM _esgvoc_metadata WHERE key='esgvoc_min_version'").fetchone()
        finally:
            conn.close()
    except sqlite3.Error as e:
        # DBs built before the metadata table existed carry no requirement.
        _LOGGER.debug("Could not read esgvoc_min_version from %s: %s", db_path, e)
        return None
    return row[0] if row else None


def get_min_version(db_path: Path) -> str | None:
    """Return the esgvoc_min_version embedded in *db_path*, or None if absent."""
    return _read_min_version(str(db_path), db_path.stat().st_mtime_ns)


def incompatibility_message(project_id: str, version: str, min_version: str | None) -> str | None:
    """
    Return a message explaining why *project_id*@*version* cannot be used with the installed
    esgvoc, or None if it is compatible (or if the versions cannot be compared).
    """
    installed = _parse_version(esgvoc.__version__)
    required = _parse_version(min_version)
    if installed is None or required is None or installed >= required:
        return None
    return (
        f"{project_id}@{version} requires esgvoc >= {min_version}, but esgvoc {esgvoc.__version__} is installed.\n"
        f"To use this version of {project_id}, upgrade esgvoc to {min_version} or later:\n"
        f'    pip install --upgrade "esgvoc>={min_version}"\n'
        f"Or keep your esgvoc and activate a version of {project_id} it supports (see the Compat column):\n"
        f"    esgvoc list-remote {project_id}"
    )


def snapshot_incompatibility_message(snapshot: DBSnapshot) -> str | None:
    """Same as incompatibility_message, from the esgvoc_min_version published in the registry."""
    return incompatibility_message(snapshot.project_id, snapshot.version, snapshot.esgvoc_min_version)


def newer_incompatible_release(fetcher: DBFetcher, snapshot: DBSnapshot) -> DBSnapshot | None:
    """
    Return the newest stable release of the project of *snapshot* if it is not *snapshot*
    and requires a more recent esgvoc, None otherwise.
    """
    newest = fetcher.get_snapshot(snapshot.project_id, "latest", compatible_only=False)
    if newest.version == snapshot.version or snapshot_incompatibility_message(newest) is None:
        return None
    return newest


def check_db_compatibility(project_id: str, version: str, db_path: Path) -> None:
    """
    :raises EsgvocIncompatibleDBError: If *db_path* requires a more recent esgvoc.
    """
    if message := incompatibility_message(project_id, version, get_min_version(db_path)):
        raise EsgvocIncompatibleDBError(message)
