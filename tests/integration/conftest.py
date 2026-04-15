"""
Shared fixtures for integration tests.

Two categories:
1. Function-scoped fixtures (existing): work with the Dev Tier config system.
2. Session-scoped fixtures (new): clone real CV repos + build real SQLite DBs once per
   pytest session. These are used by user_tier/ and dev_tier/ sub-packages to test the
   full versioning pipeline without relying on a specific developer's local setup.
   Dependent tests skip gracefully when network is unavailable.

Persistent test data
--------------------
Repos and pre-built DBs are stored in ``tests/integration/test_data/`` (gitignored).
This directory is reused across runs so subsequent runs skip the clone/build step.

    tests/integration/test_data/
    ├── repos/
    │   ├── WCRP-universe/     ← shallow-cloned universe repo
    │   └── CMIP6_CVs/         ← shallow-cloned cmip6 project repo
    └── dbs/
        ├── cmip6-v1.0.0.db   ← built from repo HEAD with cv_version=1.0.0
        └── cmip6-v2.0.0.db   ← built from repo HEAD with cv_version=2.0.0

To force a full rebuild (e.g. after upstream changes): ``pytest --rebuild-test-dbs``
To force a full re-clone: ``pytest --reclone-test-repos``
Both flags can be combined: ``pytest --reclone-test-repos --rebuild-test-dbs``
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from unittest.mock import patch
from esgvoc.core import service

# ---------------------------------------------------------------------------
# Paths for persistent test data (gitignored)
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).parent
_TEST_DATA_DIR = _THIS_DIR / "data_test"
_REPOS_DIR = _TEST_DATA_DIR / "repos"
_DBS_DIR = _TEST_DATA_DIR / "dbs"

# Repo coordinates
_UNIVERSE_REPO = "https://github.com/WCRP-CMIP/WCRP-universe"
_UNIVERSE_BRANCH = "esgvoc"
_TEST_PROJECT_REPO = "https://github.com/WCRP-CMIP/CMIP6_CVs"
_TEST_PROJECT_BRANCH = "esgvoc"
_TEST_PROJECT_ID = "cmip6"

# Simulated release versions (same git HEAD, different manifest metadata)
_V1 = "v1.0.0"
_V2 = "v2.0.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _try_shallow_clone(repo_url: str, branch: str, target: Path) -> bool:
    """
    Shallow-clone a repo to *target*.  Returns False on any failure.
    Output goes to stderr so progress is visible in the terminal.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n  Cloning {repo_url} @ {branch} → {target}", file=sys.stderr)
    try:
        r = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(target)],
            timeout=300,
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"  Clone failed: {exc}", file=sys.stderr)
        return False


@pytest.fixture(scope="session")
def cloned_repos(request: pytest.FixtureRequest):
    """
    Ensure universe and cmip6 repos are available in ``data_test/repos/``.

    Behaviour:
    - ``--reclone-test-repos``: wipe and re-clone even if already present.
    - Otherwise: reuse existing clone if present; clone only when missing.
    - Skip all dependent tests gracefully when network is unavailable.

    Returns: dict {"universe": Path, "cmip6": Path}
    """
    force = request.config.getoption("--reclone-test-repos")

    universe_path = _REPOS_DIR / "WCRP-universe"
    project_path = _REPOS_DIR / "CMIP6_CVs"

    if force:
        for p in (universe_path, project_path):
            if p.exists():
                print(f"\n  --reclone-test-repos: removing {p}", file=sys.stderr)
                shutil.rmtree(p)

    _REPOS_DIR.mkdir(parents=True, exist_ok=True)

    if not universe_path.exists():
        if not _try_shallow_clone(_UNIVERSE_REPO, _UNIVERSE_BRANCH, universe_path):
            pytest.skip(
                "Network unavailable: could not clone WCRP-universe. "
                "Retry with network access (repos are cached after first clone)."
            )

    if not project_path.exists():
        if not _try_shallow_clone(_TEST_PROJECT_REPO, _TEST_PROJECT_BRANCH, project_path):
            pytest.skip(
                "Network unavailable: could not clone CMIP6_CVs. "
                "Retry with network access (repos are cached after first clone)."
            )

    print(f"\n  Using repos from: {_REPOS_DIR}", file=sys.stderr)
    return {
        "universe": universe_path,
        _TEST_PROJECT_ID: project_path,
    }


@pytest.fixture(scope="session")
def real_dbs(request: pytest.FixtureRequest, cloned_repos):
    """
    Ensure two real SQLite databases are available in ``data_test/dbs/``.

    Both DBs are built from the same cloned repo HEAD but carry different version
    metadata in ``_esgvoc_metadata``, simulating two successive published releases:

      - v1.0.0  (older release, cv_version=1.0.0)
      - v2.0.0  (current release, cv_version=2.0.0)

    Behaviour:
    - ``--rebuild-test-dbs``: wipe and rebuild even if already present.
    - Otherwise: reuse existing DBs if present; build only when missing.

    The mock fetcher in user_tier tests copies these local files instead of
    downloading from GitHub — all other CLI/state behaviour is real.

    Returns:
        {
            "project_id":  "cmip6",
            "v1_version":  "v1.0.0",   "v1_path": Path,   "v1_result": BuildResult | None,
            "v2_version":  "v2.0.0",   "v2_path": Path,   "v2_result": BuildResult | None,
        }
    ``v1_result`` / ``v2_result`` are None when the DB was loaded from cache.
    """
    from esgvoc.admin.builder import DBBuilder

    force = request.config.getoption("--rebuild-test-dbs")

    _DBS_DIR.mkdir(parents=True, exist_ok=True)

    universe_path = cloned_repos["universe"]
    project_path = cloned_repos[_TEST_PROJECT_ID]

    builder = DBBuilder(verbose=True)

    def _build_if_missing(version: str, cv_version: str) -> tuple[Path, object]:
        db_path = _DBS_DIR / f"{_TEST_PROJECT_ID}-{version}.db"
        if force and db_path.exists():
            print(f"\n  --rebuild-test-dbs: removing {db_path}", file=sys.stderr)
            db_path.unlink()
        if db_path.exists():
            print(f"\n  Reusing cached DB: {db_path}", file=sys.stderr)
            result = None  # No BuildResult when reusing cache
        else:
            print(f"\n  Building {db_path} ...", file=sys.stderr)
            result = builder.build_dev(
                project_path=project_path,
                universe_path=universe_path,
                output_path=db_path,
                manifest_overrides={
                    "project_id": _TEST_PROJECT_ID,
                    "cv_version": cv_version,
                    "universe_version": "1.0.0",
                },
            )
            print(f"  Done: {db_path.stat().st_size / 1_048_576:.1f} MB", file=sys.stderr)
        return db_path, result

    v1_path, v1_result = _build_if_missing(_V1, "1.0.0")
    v2_path, v2_result = _build_if_missing(_V2, "2.0.0")

    return {
        "project_id": _TEST_PROJECT_ID,
        "v1_version": _V1,
        "v2_version": _V2,
        "v1_path": v1_path,
        "v2_path": v2_path,
        "v1_result": v1_result,  # BuildResult or None if reused from cache
        "v2_result": v2_result,
    }


@pytest.fixture(scope="function")
def default_config_test():
    """
    Store current config, switch to default for testing, then restore original config.
    This follows the same pattern as existing tests in test_config.py.
    """
    assert service.config_manager is not None

    # Store the original active config name
    before_test_active = service.config_manager.get_active_config_name()

    # Initialize registry and switch to default
    service.config_manager._init_registry()
    service.config_manager.switch_config("default")

    yield service.config_manager

    # Restore the original config
    service.config_manager.switch_config(before_test_active)
    current_state = service.get_state()


@pytest.fixture(scope="function")
def mock_subprocess():
    """Mock subprocess.run for git operations."""
    with patch("subprocess.run") as mock_run:
        from unittest.mock import MagicMock

        mock_run.return_value = MagicMock(returncode=0)
        yield mock_run


@pytest.fixture(scope="function")
def sample_config_modifications():
    """Sample config modifications for testing different path types."""
    return {
        "absolute_paths": {
            "universe_local_path": "/tmp/test_absolute/repos/WCRP-universe",
            "universe_db_path": "/tmp/test_absolute/dbs/universe.sqlite",
            "project_local_path": "/tmp/test_absolute/repos/CMIP6_CVs",
            "project_db_path": "/tmp/test_absolute/dbs/cmip6.sqlite",
        },
        "dot_relative_paths": {
            "universe_local_path": "./test_repos/WCRP-universe",
            "universe_db_path": "./test_dbs/universe.sqlite",
            "project_local_path": "./test_repos/CMIP6_CVs",
            "project_db_path": "./test_dbs/cmip6.sqlite",
        },
        "platform_relative_paths": {
            "universe_local_path": "repos/WCRP-universe",
            "universe_db_path": "dbs/universe.sqlite",
            "project_local_path": "repos/CMIP6_CVs",
            "project_db_path": "dbs/cmip6.sqlite",
        },
    }


def modify_default_config_paths(config_manager, path_type, sample_modifications):
    """
    Helper function to modify the default config with different path types.
    Returns the modified config data.
    """
    # Get current default config
    config = config_manager.get_active_config()
    config_data = config.dump()

    paths = sample_modifications[path_type]

    # Modify universe paths
    config_data["universe"]["local_path"] = paths["universe_local_path"]
    config_data["universe"]["db_path"] = paths["universe_db_path"]

    # Modify first project paths (assumes at least one project exists)
    if config_data["projects"]:
        config_data["projects"][0]["local_path"] = paths["project_local_path"]
        config_data["projects"][0]["db_path"] = paths["project_db_path"]

    return config_data


def create_test_config_variant(config_manager, variant_name, path_type, sample_modifications):
    """
    Create a test config variant with specific path type.
    Save it and switch to it for testing.
    """
    modified_config = modify_default_config_paths(config_manager, path_type, sample_modifications)
    config_manager.save_config(modified_config, variant_name)
    config_manager.switch_config(variant_name)
    return config_manager.get_active_config()


def cleanup_test_config(config_manager, config_name):
    """
    Clean up a test config if it exists.
    """
    try:
        configs = config_manager.list_configs()
        if config_name in configs:
            config_manager.remove_config(config_name)
    except (ValueError, KeyError):
        # Config doesn't exist, nothing to clean up
        pass

