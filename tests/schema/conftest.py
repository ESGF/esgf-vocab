"""
Fixtures for schema generation tests.

Installs project DBs covering all term kinds:
  - cmip7       : PLAIN + PATTERN terms
  - cmip6plus   : COMPOSITE terms
  - cordex-cmip5: PLAIN terms
  - input4mips  : PLAIN terms

Resolution strategy mirrors tests/python_api/conftest.py:
  1. DBs already present → reuse, zero network.
  2. DBs absent + ESGVOC_OFFLINE → skip.
  3. DBs absent + network → download once.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from esgvoc.core.service.user_state import UserState

PROJECTS_TO_INSTALL = [
    ("cmip7", "latest"),
    ("cmip6plus", "latest"),
    ("cordex-cmip5", "latest"),
    ("input4mips", "latest"),
]


@pytest.fixture(scope="session")
def installed_schema_dbs(tmp_path_factory, test_registry_url):
    """
    Ensure project DBs needed for schema tests are available.

    Uses @latest so we always test against the most recent stable snapshot.
    """
    from esgvoc.core.db_fetcher import DBFetcher

    offline = os.environ.get("ESGVOC_OFFLINE", "").lower() == "true"

    # Check if all needed projects already have an active version.
    state = UserState.load()
    all_active = all(state.get_active(pid) for pid, _ in PROJECTS_TO_INSTALL)

    if all_active:
        yield {pid: state.get_active(pid) for pid, _ in PROJECTS_TO_INSTALL}
        return

    if offline:
        missing = [pid for pid, _ in PROJECTS_TO_INSTALL if not state.get_active(pid)]
        pytest.skip(
            f"needs_db: DBs not active and ESGVOC_OFFLINE=true. "
            f"Missing: {', '.join(missing)}. "
            f"Pre-install with: esgvoc use " + " ".join(f"{pid}@latest" for pid in missing)
        )

    fetcher = DBFetcher()
    installed: dict[str, str] = {}

    for project_id, version_spec in PROJECTS_TO_INSTALL:
        snapshot = fetcher.get_snapshot(project_id, version_spec)
        target = UserState.db_path(project_id, snapshot.version)
        if not target.exists():
            fetcher.download_db(snapshot, target, show_progress=False)
        UserState.load().set_active(project_id, snapshot.version, source="registry")
        installed[project_id] = snapshot.version

    yield installed
