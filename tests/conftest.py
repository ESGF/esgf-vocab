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
"""
import os

import pytest


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
