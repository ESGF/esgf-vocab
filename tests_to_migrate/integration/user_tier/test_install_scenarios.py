"""
User Tier — Install scenarios with real SQLite databases.

Every "download" is intercepted by the mock fetcher which copies a locally-built
real DB file.  This tests the full install pipeline — state.json, path layout,
checksum verification — against actual SQLite content.

Plan scenarios covered:
  UT-1  Fresh install: download latest, activate, state persists
  UT-2  Install specific version
  UT-3  Install --no-activate
  UT-4  Skip re-download when checksum already matches (idempotency)
  UT-5  Re-download when file is corrupt (checksum mismatch)
  UT-6  Unknown project rejected before any network call
  UT-7  Version-not-found → exit code 3
  UT-8  Network error → exit code 2
"""
from __future__ import annotations

import hashlib
import sqlite3

import pytest
from esgvoc.cli.install import app as install_app
from esgvoc.core.db_fetcher import EsgvocNetworkError, EsgvocVersionNotFoundError

from .conftest import (
    db_is_valid_sqlite,
    fetcher_that_copies,
    install_real_db,
    read_db_metadata,
    runner,
)


# ---------------------------------------------------------------------------
# UT-1  Fresh install
# ---------------------------------------------------------------------------

class TestFreshInstall:

    def test_install_downloads_real_db_file(self, real_dbs):
        v1 = real_dbs["v1_path"]
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        ctx, mock_inst, artifact = fetcher_that_copies(v1, pid, ver)
        with ctx:
            result = runner.invoke(install_app, [pid])

        assert result.exit_code == 0, result.output
        mock_inst.download_db.assert_called_once()

    def test_installed_file_is_valid_sqlite(self, real_dbs):
        v1 = real_dbs["v1_path"]
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        ctx, _, _ = fetcher_that_copies(v1, pid, ver)
        with ctx:
            runner.invoke(install_app, [pid])

        from esgvoc.core.service.user_state import UserState

        installed_path = UserState.db_path(pid, ver)
        assert db_is_valid_sqlite(installed_path), "Installed file is not a valid SQLite DB"

    def test_installed_db_has_correct_metadata(self, real_dbs):
        v1 = real_dbs["v1_path"]
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        ctx, _, _ = fetcher_that_copies(v1, pid, ver)
        with ctx:
            runner.invoke(install_app, [pid])

        from esgvoc.core.service.user_state import UserState

        installed_path = UserState.db_path(pid, ver)
        meta = read_db_metadata(installed_path)
        assert meta["project_id"] == pid
        assert meta["cv_version"] == "1.0.0"

    def test_install_sets_active_in_state_json(self, real_dbs):
        v1 = real_dbs["v1_path"]
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        ctx, _, _ = fetcher_that_copies(v1, pid, ver)
        with ctx:
            runner.invoke(install_app, [pid])

        from esgvoc.core.service.user_state import UserState

        state = UserState.load()
        assert state.get_active(pid) == ver
        assert ver in state.get_installed(pid)

    def test_install_output_confirms_version(self, real_dbs):
        v1 = real_dbs["v1_path"]
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        ctx, _, _ = fetcher_that_copies(v1, pid, ver)
        with ctx:
            result = runner.invoke(install_app, [pid])

        assert "Installed and activated" in result.output
        assert pid in result.output
        assert ver in result.output

    def test_install_specific_version_calls_fetcher_correctly(self, real_dbs):
        v2 = real_dbs["v2_path"]
        pid = real_dbs["project_id"]
        ver = real_dbs["v2_version"]

        ctx, mock_inst, _ = fetcher_that_copies(v2, pid, ver)
        with ctx:
            result = runner.invoke(install_app, [f"{pid}@{ver}"])

        assert result.exit_code == 0, result.output
        mock_inst.get_artifact.assert_called_once_with(pid, version=ver)


# ---------------------------------------------------------------------------
# UT-3  Install --no-activate
# ---------------------------------------------------------------------------

class TestInstallNoActivate:

    def test_no_activate_leaves_active_unset(self, real_dbs):
        v1 = real_dbs["v1_path"]
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        ctx, _, _ = fetcher_that_copies(v1, pid, ver)
        with ctx:
            result = runner.invoke(install_app, [pid, "--no-activate"])

        assert result.exit_code == 0, result.output
        assert "not activated" in result.output

        from esgvoc.core.service.user_state import UserState

        state = UserState.load()
        assert state.get_active(pid) is None
        assert ver in state.get_installed(pid)

    def test_no_activate_db_still_written_to_disk(self, real_dbs):
        v1 = real_dbs["v1_path"]
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        ctx, _, _ = fetcher_that_copies(v1, pid, ver)
        with ctx:
            runner.invoke(install_app, [pid, "--no-activate"])

        from esgvoc.core.service.user_state import UserState

        assert db_is_valid_sqlite(UserState.db_path(pid, ver))


# ---------------------------------------------------------------------------
# UT-4  Idempotency: skip re-download if checksum matches
# ---------------------------------------------------------------------------

class TestIdempotency:

    def test_skip_download_when_file_already_present_and_checksum_matches(self, real_dbs):
        """
        When the target file already exists with the correct SHA-256, the CLI
        should skip the download call entirely and just activate.
        """
        v1 = real_dbs["v1_path"]
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        # Pre-install the real DB file into the user store
        install_real_db(v1, pid, ver)

        ctx, mock_inst, _ = fetcher_that_copies(v1, pid, ver)
        with ctx:
            result = runner.invoke(install_app, [pid])

        assert result.exit_code == 0, result.output
        assert "already on disk" in result.output
        mock_inst.download_db.assert_not_called()

    def test_redownload_when_existing_file_is_corrupt(self, real_dbs, tmp_path):
        """
        If the target file exists but its SHA-256 doesn't match, the CLI
        must re-download (call download_db once).
        """
        v1 = real_dbs["v1_path"]
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        from esgvoc.core.service.user_state import UserState

        # Write a corrupted file (wrong content → wrong checksum)
        target = UserState.db_path(pid, ver)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"this is not a valid sqlite database")

        ctx, mock_inst, _ = fetcher_that_copies(v1, pid, ver)
        with ctx:
            result = runner.invoke(install_app, [pid])

        assert result.exit_code == 0, result.output
        mock_inst.download_db.assert_called_once()
        # After re-download the file should be valid
        assert db_is_valid_sqlite(UserState.db_path(pid, ver))


# ---------------------------------------------------------------------------
# UT-6  Unknown project
# ---------------------------------------------------------------------------

class TestUnknownProject:

    def test_unknown_project_rejected_exit_1(self):
        result = runner.invoke(install_app, ["not-a-real-project"])
        assert result.exit_code == 1
        assert "Unknown project" in result.output

    def test_unknown_project_does_not_reach_fetcher(self):
        from unittest.mock import patch

        with patch("esgvoc.core.db_fetcher.DBFetcher") as MockFetcher:
            runner.invoke(install_app, ["not-a-real-project"])
            MockFetcher.assert_not_called()


# ---------------------------------------------------------------------------
# UT-7 / UT-8  Network / version errors
# ---------------------------------------------------------------------------

class TestNetworkErrors:

    def test_version_not_found_exits_3(self):
        from unittest.mock import patch

        with patch("esgvoc.core.db_fetcher.DBFetcher") as MockFetcher:
            MockFetcher.return_value.get_artifact.side_effect = (
                EsgvocVersionNotFoundError("v99.0.0 not found")
            )
            result = runner.invoke(install_app, ["cmip6@v99.0.0"])

        assert result.exit_code == 3
        assert "Version not found" in result.output

    def test_network_error_on_fetch_exits_2(self):
        from unittest.mock import patch

        with patch("esgvoc.core.db_fetcher.DBFetcher") as MockFetcher:
            MockFetcher.return_value.get_artifact.side_effect = (
                EsgvocNetworkError("connection refused")
            )
            result = runner.invoke(install_app, ["cmip6"])

        assert result.exit_code == 2

    def test_network_error_on_download_exits_2(self, real_dbs):
        from unittest.mock import patch, MagicMock

        v1 = real_dbs["v1_path"]
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        _, _, artifact = fetcher_that_copies(v1, pid, ver)

        with patch("esgvoc.core.db_fetcher.DBFetcher") as MockFetcher:
            inst = MockFetcher.return_value
            inst.get_artifact.return_value = artifact
            inst.download_db.side_effect = EsgvocNetworkError("timeout")

            result = runner.invoke(install_app, [pid])

        assert result.exit_code == 2
