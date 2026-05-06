"""
Fixtures for admin_build_db tests.

Tests marked ``needs_real_repos`` require locally cloned CV repositories.
They are excluded from the default test run.

How to run them
---------------
1.  Make sure the repos are cloned somewhere on disk (e.g. alongside this
    project):

        git clone https://github.com/WCRP-CMIP/WCRP-universe
        git clone https://github.com/WCRP-CMIP/CMIP6_CVs
        git clone https://github.com/WCRP-CMIP/CMIP7_CVs

2.  Point ESGVOC_REPOS_DIR at the directory that *contains* them
    (defaults to the parent folder of the esgf-vocab checkout, so if
    your repos sit alongside esgf-vocab/ you don't need to set it):

        export ESGVOC_REPOS_DIR=/path/to/your/repos   # bash / zsh
        set -x ESGVOC_REPOS_DIR /path/to/your/repos   # fish

    Expected layout:
        <ESGVOC_REPOS_DIR>/
        ├── WCRP-universe/
        ├── CMIP6_CVs/
        └── CMIP7_CVs/          (or whatever project repos you need)

3.  Run with the marker:

        uv run pytest -m needs_real_repos tests/admin_build_db/

    These tests are also marked ``slow`` (~15 s each), so the following
    runs both:

        uv run pytest -m "needs_real_repos or slow" tests/admin_build_db/
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

# Project root = tests/admin_build_db/../../  →  esgf-vocab/
_PROJECT_ROOT = Path(__file__).parent.parent.parent

# Default repos dir = parent of the project root (sibling repos convention)
_DEFAULT_REPOS_DIR = _PROJECT_ROOT.parent


def _repos_dir() -> Path:
    env = os.environ.get("ESGVOC_REPOS_DIR")
    if env:
        return Path(env).resolve()
    return _DEFAULT_REPOS_DIR.resolve()


@pytest.fixture(scope="session")
def repos_dir() -> Path:
    """Root directory that contains the CV repository clones."""
    return _repos_dir()


@pytest.fixture(scope="session")
def universe_repo_path(repos_dir) -> Path:
    return repos_dir / "WCRP-universe"


@pytest.fixture(scope="session")
def cmip6_cvs_repo_path(repos_dir) -> Path:
    return repos_dir / "CMIP6_CVs"


@pytest.fixture(scope="session")
def cmip7_cvs_repo_path(repos_dir) -> Path:
    return repos_dir / "CMIP7_CVs"


@pytest.fixture(scope="session")
def local_repos_available(universe_repo_path, cmip6_cvs_repo_path) -> bool:
    """True if both WCRP-universe and CMIP6_CVs directories exist."""
    return universe_repo_path.exists() and cmip6_cvs_repo_path.exists()


@pytest.fixture(scope="session")
def local_repos_cmip7_available(universe_repo_path, cmip7_cvs_repo_path) -> bool:
    """True if both WCRP-universe and CMIP7_CVs directories exist."""
    return universe_repo_path.exists() and cmip7_cvs_repo_path.exists()


@pytest.fixture
def skip_if_no_local_repos(local_repos_available, repos_dir):
    """Skip the test if WCRP-universe or CMIP6_CVs are not found."""
    if not local_repos_available:
        pytest.skip(
            f"Local CV repos not found in {repos_dir}.\n"
            "Clone WCRP-universe and CMIP6_CVs there, or set ESGVOC_REPOS_DIR.\n"
            "See tests/admin_build_db/conftest.py for full instructions."
        )


@pytest.fixture
def skip_if_no_cmip7_repos(local_repos_cmip7_available, repos_dir):
    """Skip the test if WCRP-universe or CMIP7_CVs are not found."""
    if not local_repos_cmip7_available:
        pytest.skip(
            f"Local CV repos not found in {repos_dir}.\n"
            "Clone WCRP-universe and CMIP7_CVs there, or set ESGVOC_REPOS_DIR.\n"
            "See tests/admin_build_db/conftest.py for full instructions."
        )
