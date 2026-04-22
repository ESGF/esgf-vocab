"""
Fixtures for admin_build_db tests.

Repo discovery
--------------
Build tests need locally checked-out copies of the CV repositories.
The root directory that contains them is resolved as follows:

  1. ESGVOC_REPOS_DIR env var (absolute path)         — explicit override
  2. Parent directory of the project root              — default: the folder
     that contains esgf-vocab/ alongside WCRP-universe/, CMIP6_CVs/, etc.

Set ESGVOC_REPOS_DIR if your repos live somewhere else:

  bash / zsh:
    export ESGVOC_REPOS_DIR=/path/to/your/repos

  fish:
    set -x ESGVOC_REPOS_DIR /path/to/your/repos

Expected layout inside the repos directory:
    <repos_dir>/
    ├── WCRP-universe/
    ├── CMIP6_CVs/
    └── ...
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
def local_repos_available(universe_repo_path, cmip6_cvs_repo_path) -> bool:
    """True if both expected repo directories exist."""
    return universe_repo_path.exists() and cmip6_cvs_repo_path.exists()


@pytest.fixture
def skip_if_no_local_repos(local_repos_available, repos_dir):
    if not local_repos_available:
        pytest.skip(
            f"Local CV repos not found in {repos_dir}. "
            f"Clone WCRP-universe and CMIP6_CVs there, "
            f"or set ESGVOC_REPOS_DIR to point to the directory that contains them."
        )
