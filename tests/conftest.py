"""
Root-level pytest configuration.

Markers
-------
needs_db        Test requires project DB files to be installed.
                On first run (DBs absent) the `installed_dbs` session fixture
                downloads them automatically — network required that one time.
                On subsequent runs (DBs already present via ESGVOC_HOME) the
                test runs fully offline.
                Skip entirely with: pytest -m "not needs_db"

needs_network   Test always hits the wire: live HTTP assertions, real registry
                fetches, git clones from GitHub.  Cannot be satisfied by cached
                data.
                Skip with: pytest -m "not needs_network"

slow            Test is time-expensive regardless of network (full DB builds,
                large ingestion pipelines). Typically >10 s.
                Skipped by default via addopts in pyproject.toml.
                Run with: pytest -m slow

needs_db vs needs_network
    Use `needs_db`      when the test only needs the DB file present.
    Use `needs_network` when the test must contact a live server every run
                        (e.g. verifying the registry index, testing HTTP errors).
    Use both together   when a test both needs a DB *and* must verify live data.

Testing against locally built DBs
---------------------------------
By default the DB fixtures use DBs published in the registry. To test against
DBs built by `esgvoc admin build` instead (e.g. from CV branches not published
yet), build them in a directory and point ESGVOC_TEST_DBS_DIR at it:

    uv run python tests/build_test_dbs.py /tmp/test_dbs
    ESGVOC_TEST_DBS_DIR=/tmp/test_dbs uv run pytest
"""
import os
import shutil
from pathlib import Path

import pytest

TEST_DBS_DIR_ENV = "ESGVOC_TEST_DBS_DIR"
LOCAL_DB_NAME = "local"


def pytest_configure(config):
    # Markers are declared in pyproject.toml too; this safety-net registration
    # ensures they work when pytest is run outside the project root.
    config.addinivalue_line(
        "markers",
        "needs_db: test requires installed project DBs "
        "(downloads on first run; offline on subsequent runs)",
    )
    config.addinivalue_line("markers", "needs_network: test requires live network access every run")
    config.addinivalue_line(
        "markers",
        "slow: test is time-expensive (DB builds, large ingestion); skipped by default",
    )


# ---------------------------------------------------------------------------
# Session-scoped registry URL (shared by all suites)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_registry_url() -> str:
    """Registry base URL used for DB downloads during tests."""
    return os.environ.get(
        "ESGVOC_REGISTRY_BASE_URL",
        "https://raw.githubusercontent.com/WCRP-CMIP/esgvoc_registry/main",
    )


# ---------------------------------------------------------------------------
# Opt-in: locally built DBs instead of the registry ones
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def local_test_dbs(tmp_path_factory):
    """
    The DBs of $ESGVOC_TEST_DBS_DIR (one ``<project_id>.db`` per project, as built by
    tests/build_test_dbs.py), installed as ``<project_id>@local`` and activated in a
    session ESGVOC_HOME. None when ESGVOC_TEST_DBS_DIR is not set.
    """
    from esgvoc.core.service.user_state import UserState

    root = os.environ.get(TEST_DBS_DIR_ENV)
    if not root:
        yield None
        return
    sources = {path.stem: path for path in sorted(Path(root).glob("*.db"))}
    if not sources:
        pytest.fail(f"{TEST_DBS_DIR_ENV}={root} holds no <project_id>.db file: build them with tests/build_test_dbs.py")

    saved = {key: os.environ.get(key) for key in ("ESGVOC_HOME", "ESGVOC_DB_DIR")}
    os.environ["ESGVOC_HOME"] = str(tmp_path_factory.mktemp("esgvoc_local_dbs_home"))
    os.environ.pop("ESGVOC_DB_DIR", None)
    try:
        for project_id in sources:
            install_local_test_db(project_id, LOCAL_DB_NAME, sources)
            UserState.load().set_active(project_id, LOCAL_DB_NAME, source="local")
        yield sources
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def install_local_test_db(project_id: str, name: str, sources: dict[str, Path]) -> Path:
    """Install the locally built DB of *project_id* as *project_id*@*name*."""
    from esgvoc.core.service.user_state import UserState

    if project_id not in sources:
        pytest.fail(
            f"{TEST_DBS_DIR_ENV} has no {project_id}.db (found: {', '.join(sources)}): "
            "build it with tests/build_test_dbs.py"
        )
    target = UserState.db_path(project_id, name)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sources[project_id], target)
    return target
