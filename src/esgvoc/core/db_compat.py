"""
Compatibility between a project database and the installed esgvoc.

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
from esgvoc.core.exceptions import EsgvocIncompatibleDBError

_LOGGER = logging.getLogger(__name__)


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
