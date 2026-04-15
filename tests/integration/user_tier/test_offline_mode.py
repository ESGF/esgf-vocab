"""
User Tier — Offline mode integration tests with real installed databases.

Offline mode (ESGVOC_OFFLINE=true) should:
  - Block all network operations in DBFetcher with a clear EsgvocOfflineError
  - Allow read-only commands (list, use, status) to work against already-installed DBs
  - Allow remove to work (no network needed)
  - Fail install / update gracefully (exit code, not crash)

Plan scenarios covered:
  UT-20  DBFetcher raises EsgvocOfflineError when ESGVOC_OFFLINE=true
  UT-21  Install fails offline with exit code 2
  UT-22  List works offline (reads from state.json only)
  UT-23  Use works offline (only updates state.json)
  UT-24  Remove works offline (deletes file + updates state.json)
  UT-25  Status --user works offline
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from esgvoc.cli.install import app as install_app
from esgvoc.cli.remove import app as remove_app
from esgvoc.cli.status import app as status_app
from esgvoc.cli.update import app as update_app
from esgvoc.cli.use import app as use_app
from esgvoc.cli.versions import app as versions_app

from .conftest import install_real_db, runner


@pytest.fixture
def offline(monkeypatch):
    """Enable offline mode for the duration of a test."""
    monkeypatch.setenv("ESGVOC_OFFLINE", "true")
    yield


# ---------------------------------------------------------------------------
# UT-20  DBFetcher offline behaviour
# ---------------------------------------------------------------------------

class TestDBFetcherOffline:

    def test_fetcher_is_offline_when_env_set(self, tmp_path, offline):
        from esgvoc.core.db_fetcher import DBFetcher, EsgvocOfflineError

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        assert fetcher.offline is True

        with pytest.raises(EsgvocOfflineError):
            fetcher.list_versions("cmip6")

    def test_fetcher_is_offline_via_constructor_flag(self, tmp_path):
        from esgvoc.core.db_fetcher import DBFetcher, EsgvocOfflineError

        fetcher = DBFetcher(cache_dir=tmp_path / "cache", offline=True)
        assert fetcher.offline is True

        with pytest.raises(EsgvocOfflineError):
            fetcher.get_artifact("cmip6", version="latest")

    def test_fetcher_is_online_by_default(self, tmp_path):
        """Verify the autouse isolated_home fixture correctly clears ESGVOC_OFFLINE."""
        from esgvoc.core.db_fetcher import DBFetcher

        fetcher = DBFetcher(cache_dir=tmp_path / "cache")
        assert fetcher.offline is False


# ---------------------------------------------------------------------------
# UT-21  Install / update fail offline
# ---------------------------------------------------------------------------

class TestInstallOffline:

    def test_install_offline_fails(self, offline):
        from unittest.mock import patch
        from esgvoc.core.db_fetcher import EsgvocOfflineError

        with patch("esgvoc.core.db_fetcher.DBFetcher") as MockFetcher:
            MockFetcher.return_value.get_artifact.side_effect = EsgvocOfflineError(
                "ESGVOC_OFFLINE is set"
            )
            result = runner.invoke(install_app, ["cmip6"])

        assert result.exit_code != 0
        # Output must not be empty: should explain what happened
        assert result.output.strip()

    def test_update_offline_does_not_change_state(self, real_dbs, offline):
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, v1_ver)

        from unittest.mock import patch
        from esgvoc.core.db_fetcher import EsgvocOfflineError

        with patch("esgvoc.core.db_fetcher.DBFetcher") as MockFetcher:
            MockFetcher.return_value.get_artifact.side_effect = EsgvocOfflineError(
                "offline"
            )
            runner.invoke(update_app, [pid])

        from esgvoc.core.service.user_state import UserState

        # Active version must remain unchanged
        assert UserState.load().get_active(pid) == v1_ver


# ---------------------------------------------------------------------------
# UT-22  List works offline
# ---------------------------------------------------------------------------

class TestListOffline:

    def test_list_shows_installed_dbs_offline(self, real_dbs, offline):
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, v1_ver)

        result = runner.invoke(versions_app, [])
        assert result.exit_code == 0
        assert v1_ver in result.output

    def test_list_empty_offline_graceful(self, offline):
        result = runner.invoke(versions_app, [])
        assert result.exit_code == 0
        assert "No projects installed" in result.output


# ---------------------------------------------------------------------------
# UT-23  Use works offline
# ---------------------------------------------------------------------------

class TestUseOffline:

    def test_use_switches_active_version_offline(self, real_dbs, offline):
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]
        v2_ver = real_dbs["v2_version"]

        install_real_db(real_dbs["v1_path"], pid, v1_ver)
        install_real_db(real_dbs["v2_path"], pid, v2_ver)

        result = runner.invoke(use_app, [f"{pid}@{v1_ver}"])
        assert result.exit_code == 0, result.output

        from esgvoc.core.service.user_state import UserState

        assert UserState.load().get_active(pid) == v1_ver


# ---------------------------------------------------------------------------
# UT-24  Remove works offline
# ---------------------------------------------------------------------------

class TestRemoveOffline:

    def test_remove_deletes_file_offline(self, real_dbs, offline):
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]
        v2_ver = real_dbs["v2_version"]

        db_v1 = install_real_db(real_dbs["v1_path"], pid, v1_ver)
        install_real_db(real_dbs["v2_path"], pid, v2_ver)

        result = runner.invoke(remove_app, [f"{pid}@{v1_ver}", "--yes"])
        assert result.exit_code == 0, result.output
        assert not db_v1.exists()

        from esgvoc.core.service.user_state import UserState

        assert v1_ver not in UserState.load().get_installed(pid)


# ---------------------------------------------------------------------------
# UT-25  Status works offline
# ---------------------------------------------------------------------------

class TestStatusOffline:

    def test_status_user_works_offline(self, real_dbs, offline):
        pid = real_dbs["project_id"]
        install_real_db(real_dbs["v1_path"], pid, real_dbs["v1_version"])

        result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0
        assert pid in result.output
