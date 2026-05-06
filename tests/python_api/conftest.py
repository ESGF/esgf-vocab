"""
Fixtures for python_api tests.

DB resolution strategy (in order):
  1. DBs already present in the current home (default ~/.local/share/esgvoc/
     or ESGVOC_HOME if set) → reuse, zero network calls.
  2. DBs absent and ESGVOC_OFFLINE=true → skip all dependent tests with a
     hint on how to pre-install.
  3. DBs absent and network available → download once to a session tmp dir.

In practice: run `esgvoc use universe@v1.0.0 && esgvoc use cmip7@v1.0.0` once
and the tests will run offline from that point on.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from esgvoc.core.service.user_state import UserState

# ---------------------------------------------------------------------------
# Projects the API test suite requires
# ---------------------------------------------------------------------------

PROJECTS_TO_INSTALL = [
    ("universe", "v1.0.0"),
    ("cmip7", "v1.0.0"),
]


# ---------------------------------------------------------------------------
# Session-scoped DB installation
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def installed_dbs(tmp_path_factory, test_registry_url):
    """
    Ensure universe@v1.0.0 and cmip7@v1.0.0 are available for the session.

    Resolution order:
      1. ESGVOC_HOME already set and all DB files present → reuse, no network.
      2. DBs absent but network available → download once to a session tmp dir.
      3. DBs absent and ESGVOC_OFFLINE=true → skip all dependent tests with a
         clear message explaining how to pre-install the databases.

    Returns a dict: {"universe": Path, "cmip7": Path}
    """
    offline = os.environ.get("ESGVOC_OFFLINE", "").lower() == "true"

    # Check the current home (respects ESGVOC_HOME if set, otherwise platformdirs default).
    candidate: dict[str, Path] = {}
    all_found = True
    for project_id, version in PROJECTS_TO_INSTALL:
        db = UserState.db_path(project_id, version)
        if db.exists():
            candidate[project_id] = db
        else:
            all_found = False
            break

    if all_found:
        # Every DB is present — activate and yield with zero network calls.
        state = UserState.load()
        for project_id, version in PROJECTS_TO_INSTALL:
            if state.get_active(project_id) != version:
                state.set_active(project_id, version, source="registry")
        yield candidate
        return

    # Some or all DBs are missing.
    if offline:
        missing = [
            f"{pid}@{ver}"
            for pid, ver in PROJECTS_TO_INSTALL
            if not UserState.db_path(pid, ver).exists()
        ]
        pytest.skip(
            f"needs_db: DBs not installed and ESGVOC_OFFLINE=true. "
            f"Missing: {', '.join(missing)}. "
            f"Pre-install with: ESGVOC_REGISTRY_BASE_URL=... esgvoc use {' '.join(missing)}"
        )

    # --- Download path (network required this one time) ---
    from esgvoc.core.db_fetcher import DBFetcher

    home = tmp_path_factory.mktemp("esgvoc_session_home")
    os.environ["ESGVOC_HOME"] = str(home)
    os.environ["ESGVOC_REGISTRY_BASE_URL"] = test_registry_url

    fetcher = DBFetcher()
    installed: dict[str, Path] = {}

    for project_id, version in PROJECTS_TO_INSTALL:
        target = UserState.db_path(project_id, version)
        if not target.exists():
            snapshot = fetcher.get_snapshot(project_id, version)
            fetcher.download_db(snapshot, target, show_progress=False)
        UserState.load().set_active(project_id, version, source="registry")
        installed[project_id] = target

    yield installed

    os.environ.pop("ESGVOC_HOME", None)
    os.environ.pop("ESGVOC_REGISTRY_BASE_URL", None)


@pytest.fixture(scope="session")
def universe_db(installed_dbs) -> Path:
    return installed_dbs["universe"]


@pytest.fixture(scope="session")
def cmip7_db(installed_dbs) -> Path:
    return installed_dbs["cmip7"]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def read_metadata(db_path: Path) -> dict[str, str]:
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall()
        return dict(rows)
    finally:
        conn.close()
