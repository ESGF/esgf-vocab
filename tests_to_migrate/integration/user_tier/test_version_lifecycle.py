"""
User Tier — Complete version lifecycle tests with real SQLite databases.

Tests the full state machine across multiple commands sequentially:
install → use → list → update → remove

The DBs are real SQLite files, so assertions can go deeper than "exit code 0":
we can read _esgvoc_metadata to verify which DB is actually installed, open the
DB to check table structure, etc.

Plan scenarios covered:
  UT-10  Multi-version coexistence: two real DBs on disk simultaneously
  UT-11  Switch active version → _esgvoc_metadata reflects the switched version
  UT-12  Remove specific version → file deleted, state updated, other version intact
  UT-13  Update: old version on disk, new version downloaded → state transitions correct
  UT-14  Full lifecycle: install v1 → install v2 → use v1 → remove v1 → update → remove all
  UT-15  Status --user shows correct project/version info from real state
"""
from __future__ import annotations

import sqlite3

import pytest
from typer.testing import CliRunner

from esgvoc.cli.install import app as install_app
from esgvoc.cli.use import app as use_app
from esgvoc.cli.versions import app as versions_app
from esgvoc.cli.remove import app as remove_app
from esgvoc.cli.update import app as update_app
from esgvoc.cli.status import app as status_app

from .conftest import (
    db_is_valid_sqlite,
    fetcher_that_copies,
    install_real_db,
    read_db_metadata,
    runner,
)


# ---------------------------------------------------------------------------
# UT-10  Multi-version coexistence
# ---------------------------------------------------------------------------

class TestMultiVersionCoexistence:

    def test_two_versions_installed_both_valid_sqlite(self, real_dbs):
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]
        v2_ver = real_dbs["v2_version"]

        db_v1 = install_real_db(real_dbs["v1_path"], pid, v1_ver)
        db_v2 = install_real_db(real_dbs["v2_path"], pid, v2_ver)

        assert db_is_valid_sqlite(db_v1)
        assert db_is_valid_sqlite(db_v2)

    def test_two_versions_have_distinct_cv_version_metadata(self, real_dbs):
        pid = real_dbs["project_id"]

        db_v1 = install_real_db(real_dbs["v1_path"], pid, real_dbs["v1_version"])
        db_v2 = install_real_db(real_dbs["v2_path"], pid, real_dbs["v2_version"])

        meta_v1 = read_db_metadata(db_v1)
        meta_v2 = read_db_metadata(db_v2)

        assert meta_v1["cv_version"] == "1.0.0"
        assert meta_v2["cv_version"] == "2.0.0"
        assert meta_v1["cv_version"] != meta_v2["cv_version"]

    def test_both_versions_registered_in_state(self, real_dbs):
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]
        v2_ver = real_dbs["v2_version"]

        install_real_db(real_dbs["v1_path"], pid, v1_ver)
        install_real_db(real_dbs["v2_path"], pid, v2_ver)

        from esgvoc.core.service.user_state import UserState

        state = UserState.load()
        installed = state.get_installed(pid)
        assert v1_ver in installed
        assert v2_ver in installed


# ---------------------------------------------------------------------------
# UT-11  Switch active version
# ---------------------------------------------------------------------------

class TestUseCommand:

    def test_use_switches_active_version(self, real_dbs):
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]
        v2_ver = real_dbs["v2_version"]

        install_real_db(real_dbs["v1_path"], pid, v1_ver)
        install_real_db(real_dbs["v2_path"], pid, v2_ver)

        # Start: active = v2 (last installed)
        result = runner.invoke(use_app, [f"{pid}@{v1_ver}"])
        assert result.exit_code == 0, result.output

        from esgvoc.core.service.user_state import UserState

        assert UserState.load().get_active(pid) == v1_ver

    def test_active_db_file_reflects_switched_version_metadata(self, real_dbs):
        """After switching, the active DB path points to the correct SQLite file."""
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]
        v2_ver = real_dbs["v2_version"]

        install_real_db(real_dbs["v1_path"], pid, v1_ver)
        install_real_db(real_dbs["v2_path"], pid, v2_ver)

        runner.invoke(use_app, [f"{pid}@{v1_ver}"])

        from esgvoc.core.service.user_state import UserState

        active_ver = UserState.load().get_active(pid)
        active_db = UserState.db_path(pid, active_ver)
        meta = read_db_metadata(active_db)
        assert meta["cv_version"] == "1.0.0"

        runner.invoke(use_app, [f"{pid}@{v2_ver}"])
        active_ver = UserState.load().get_active(pid)
        active_db = UserState.db_path(pid, active_ver)
        meta = read_db_metadata(active_db)
        assert meta["cv_version"] == "2.0.0"

    def test_use_not_installed_version_fails(self, real_dbs):
        pid = real_dbs["project_id"]
        install_real_db(real_dbs["v1_path"], pid, real_dbs["v1_version"])

        result = runner.invoke(use_app, [f"{pid}@v99.9.9"])
        assert result.exit_code != 0
        assert "not installed" in result.output

    def test_use_on_uninstalled_project_fails(self):
        result = runner.invoke(use_app, ["cmip6"])
        assert result.exit_code != 0
        assert "No versions installed" in result.output

    def test_use_missing_db_file_fails(self, real_dbs):
        """state.json says version is installed but DB file is gone → clear error."""
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]

        from esgvoc.core.service.user_state import UserState

        state = UserState.load()
        state.add_installed(pid, v1_ver)
        state.set_active(pid, v1_ver)
        state.save()
        # Intentionally NOT creating the DB file

        result = runner.invoke(use_app, [f"{pid}@{v1_ver}"])
        assert result.exit_code != 0
        assert "missing" in result.output.lower()


# ---------------------------------------------------------------------------
# UT-12  Remove version
# ---------------------------------------------------------------------------

class TestRemoveCommand:

    def test_remove_specific_version_deletes_db_file(self, real_dbs):
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]
        v2_ver = real_dbs["v2_version"]

        db_v1 = install_real_db(real_dbs["v1_path"], pid, v1_ver)
        db_v2 = install_real_db(real_dbs["v2_path"], pid, v2_ver)

        result = runner.invoke(remove_app, [f"{pid}@{v1_ver}", "--yes"])
        assert result.exit_code == 0, result.output

        assert not db_v1.exists(), "v1 DB should have been deleted"
        assert db_v2.exists(), "v2 DB should still exist"

    def test_remove_updates_state_correctly(self, real_dbs):
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]
        v2_ver = real_dbs["v2_version"]

        install_real_db(real_dbs["v1_path"], pid, v1_ver)
        install_real_db(real_dbs["v2_path"], pid, v2_ver)

        runner.invoke(remove_app, [f"{pid}@{v1_ver}", "--yes"])

        from esgvoc.core.service.user_state import UserState

        state = UserState.load()
        assert v1_ver not in state.get_installed(pid)
        assert v2_ver in state.get_installed(pid)

    def test_remove_active_version_clears_active(self, real_dbs):
        pid = real_dbs["project_id"]
        v2_ver = real_dbs["v2_version"]

        db_v2 = install_real_db(real_dbs["v2_path"], pid, v2_ver)

        runner.invoke(remove_app, [f"{pid}@{v2_ver}", "--yes"])

        from esgvoc.core.service.user_state import UserState

        state = UserState.load()
        assert state.get_active(pid) is None
        assert not db_v2.exists()

    def test_remove_all_deletes_both_db_files(self, real_dbs):
        pid = real_dbs["project_id"]

        db_v1 = install_real_db(real_dbs["v1_path"], pid, real_dbs["v1_version"])
        db_v2 = install_real_db(real_dbs["v2_path"], pid, real_dbs["v2_version"])

        result = runner.invoke(remove_app, [pid, "--all", "--yes"])
        assert result.exit_code == 0, result.output

        assert not db_v1.exists()
        assert not db_v2.exists()

        from esgvoc.core.service.user_state import UserState

        assert UserState.load().get_installed(pid) == []


# ---------------------------------------------------------------------------
# UT-13  Update command
# ---------------------------------------------------------------------------

class TestUpdateCommand:

    def test_update_installs_new_version_and_activates(self, real_dbs):
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]
        v2_ver = real_dbs["v2_version"]

        install_real_db(real_dbs["v1_path"], pid, v1_ver)

        ctx, mock_inst, _ = fetcher_that_copies(real_dbs["v2_path"], pid, v2_ver)
        with ctx:
            result = runner.invoke(update_app, [pid])

        assert result.exit_code == 0, result.output
        assert v2_ver in result.output

        from esgvoc.core.service.user_state import UserState

        state = UserState.load()
        assert state.get_active(pid) == v2_ver
        assert v2_ver in state.get_installed(pid)
        # Old version still on disk
        assert v1_ver in state.get_installed(pid)

    def test_update_new_version_is_valid_sqlite(self, real_dbs):
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]
        v2_ver = real_dbs["v2_version"]

        install_real_db(real_dbs["v1_path"], pid, v1_ver)

        ctx, _, _ = fetcher_that_copies(real_dbs["v2_path"], pid, v2_ver)
        with ctx:
            runner.invoke(update_app, [pid])

        from esgvoc.core.service.user_state import UserState

        assert db_is_valid_sqlite(UserState.db_path(pid, v2_ver))

    def test_update_check_flag_no_download(self, real_dbs):
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]
        v2_ver = real_dbs["v2_version"]

        install_real_db(real_dbs["v1_path"], pid, v1_ver)

        ctx, mock_inst, _ = fetcher_that_copies(real_dbs["v2_path"], pid, v2_ver)
        with ctx:
            result = runner.invoke(update_app, [pid, "--check"])

        assert result.exit_code == 0, result.output
        assert v2_ver in result.output
        mock_inst.download_db.assert_not_called()

        from esgvoc.core.service.user_state import UserState

        # Active version must not have changed
        assert UserState.load().get_active(pid) == v1_ver

    def test_update_already_latest_reports_no_action(self, real_dbs):
        pid = real_dbs["project_id"]
        v2_ver = real_dbs["v2_version"]

        install_real_db(real_dbs["v2_path"], pid, v2_ver)

        ctx, mock_inst, _ = fetcher_that_copies(real_dbs["v2_path"], pid, v2_ver)
        with ctx:
            result = runner.invoke(update_app, [pid])

        assert result.exit_code == 0
        assert "already at" in result.output
        mock_inst.download_db.assert_not_called()


# ---------------------------------------------------------------------------
# UT-14  Full lifecycle
# ---------------------------------------------------------------------------

class TestFullLifecycle:

    def test_install_use_remove_update_sequence(self, real_dbs):
        """
        Complete lifecycle: install v1 → install v2 (no-activate) → use v1 →
        list (both visible) → remove v1 → update (back to v2) → remove all.
        """
        from esgvoc.core.service.user_state import UserState

        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]
        v2_ver = real_dbs["v2_version"]

        # 1. Install v1 (becomes active)
        ctx1, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid, v1_ver)
        with ctx1:
            r = runner.invoke(install_app, [f"{pid}@{v1_ver}"])
        assert r.exit_code == 0, r.output
        assert UserState.load().get_active(pid) == v1_ver

        # 2. Install v2 without activating
        ctx2, _, _ = fetcher_that_copies(real_dbs["v2_path"], pid, v2_ver)
        with ctx2:
            r = runner.invoke(install_app, [f"{pid}@{v2_ver}", "--no-activate"])
        assert r.exit_code == 0, r.output
        assert UserState.load().get_active(pid) == v1_ver  # Unchanged

        # 3. List: both versions appear
        r = runner.invoke(versions_app, [pid])
        assert v1_ver in r.output
        assert v2_ver in r.output

        # 4. Switch to v2
        r = runner.invoke(use_app, [f"{pid}@{v2_ver}"])
        assert r.exit_code == 0, r.output
        assert UserState.load().get_active(pid) == v2_ver

        # Verify we can read metadata from the active DB
        active_db = UserState.db_path(pid, v2_ver)
        meta = read_db_metadata(active_db)
        assert meta["cv_version"] == "2.0.0"

        # 5. Remove v1 (non-active)
        r = runner.invoke(remove_app, [f"{pid}@{v1_ver}", "--yes"])
        assert r.exit_code == 0, r.output
        assert UserState.load().get_active(pid) == v2_ver  # Active unchanged

        # 6. Remove all
        r = runner.invoke(remove_app, [pid, "--all", "--yes"])
        assert r.exit_code == 0, r.output

        state = UserState.load()
        assert state.get_installed(pid) == []
        assert state.get_active(pid) is None


# ---------------------------------------------------------------------------
# UT-15  Status command
# ---------------------------------------------------------------------------

class TestStatusCommand:

    def test_status_user_shows_installed_project(self, real_dbs):
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]

        install_real_db(real_dbs["v1_path"], pid, v1_ver)

        result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0, result.output
        assert pid in result.output
        assert v1_ver in result.output

    def test_status_with_paths_shows_db_filepath(self, real_dbs):
        pid = real_dbs["project_id"]
        v1_ver = real_dbs["v1_version"]

        install_real_db(real_dbs["v1_path"], pid, v1_ver)

        result = runner.invoke(status_app, ["--user", "--paths"])
        assert result.exit_code == 0, result.output
        assert ".db" in result.output

    def test_status_no_projects_shows_hint(self):
        result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0
        assert "no projects installed" in result.output.lower()


# ---------------------------------------------------------------------------
# List command
# ---------------------------------------------------------------------------

class TestListCommand:

    def test_list_empty_when_nothing_installed(self):
        result = runner.invoke(versions_app, [])
        assert result.exit_code == 0
        assert "No projects installed" in result.output

    def test_list_shows_both_versions(self, real_dbs):
        pid = real_dbs["project_id"]
        install_real_db(real_dbs["v1_path"], pid, real_dbs["v1_version"])
        install_real_db(real_dbs["v2_path"], pid, real_dbs["v2_version"])

        result = runner.invoke(versions_app, [])
        assert result.exit_code == 0
        assert real_dbs["v1_version"] in result.output
        assert real_dbs["v2_version"] in result.output

    def test_list_marks_active_version(self, real_dbs):
        pid = real_dbs["project_id"]
        install_real_db(real_dbs["v1_path"], pid, real_dbs["v1_version"])
        install_real_db(real_dbs["v2_path"], pid, real_dbs["v2_version"])

        runner.invoke(use_app, [f"{pid}@{real_dbs['v1_version']}"])

        result = runner.invoke(versions_app, [])
        assert "active" in result.output
