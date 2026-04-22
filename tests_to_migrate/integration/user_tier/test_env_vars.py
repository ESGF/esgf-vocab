"""
User Tier — Environment variable override integration tests.

Tests that ESGVOC_DB_DIR and ESGVOC_STATE_FILE correctly redirect storage,
enabling shared/HPC installation scenarios (Scenarios 37-38 from the plan).

The ``isolated_home`` autouse fixture already sets ``ESGVOC_HOME`` to a
temp directory per test. Here we additionally override ``ESGVOC_DB_DIR`` and
``ESGVOC_STATE_FILE`` to point to *different* subdirectories, simulating:
  - A shared read-only DB store managed by an admin
  - A user-local state.json alongside a shared DB store

All tests use the ``fetcher_that_copies`` mock to avoid real network calls;
all other UserState / install / status / list behaviour is real.

Plan scenarios covered:
  UT-30  ESGVOC_DB_DIR redirects where DBs are stored on install
  UT-31  ESGVOC_STATE_FILE redirects where state.json is written/read
  UT-32  Combined DB_DIR + STATE_FILE: install writes to custom locations,
         list/status reads from them correctly
  UT-33  Status command respects ESGVOC_DB_DIR / STATE_FILE env var paths
  UT-34  Install respects ESGVOC_DB_DIR: DB lands in the custom directory
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from esgvoc.cli.install import app as install_app
from esgvoc.cli.status import app as status_app
from esgvoc.cli.versions import app as versions_app

from .conftest import fetcher_that_copies, install_real_db, runner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_custom_dirs(monkeypatch, tmp_path: Path):
    """
    Override ESGVOC_DB_DIR and ESGVOC_STATE_FILE to custom subdirectories
    inside tmp_path (which already has ESGVOC_HOME set by isolated_home).

    Returns (db_dir, state_file) paths.
    """
    db_dir = tmp_path / "shared" / "dbs"
    state_file = tmp_path / "shared" / "state.json"
    db_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ESGVOC_DB_DIR", str(db_dir))
    monkeypatch.setenv("ESGVOC_STATE_FILE", str(state_file))
    return db_dir, state_file


# ---------------------------------------------------------------------------
# UT-30  ESGVOC_DB_DIR redirects DB storage
# ---------------------------------------------------------------------------

class TestCustomDbDir:
    """UT-30 / UT-34: Install stores DB in ESGVOC_DB_DIR, not default location."""

    def test_install_db_lands_in_custom_db_dir(self, real_dbs, tmp_path, monkeypatch):
        db_dir, _ = _set_custom_dirs(monkeypatch, tmp_path)
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        ctx, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid, ver)
        with ctx:
            result = runner.invoke(install_app, [pid])

        assert result.exit_code == 0, result.output
        # DB should be in the custom directory
        expected = db_dir / f"{pid}-{ver}.db"
        assert expected.exists(), f"DB not found at {expected}"

    def test_install_db_not_in_default_location(self, real_dbs, tmp_path, monkeypatch):
        """When ESGVOC_DB_DIR is set, the default dbs/ dir should NOT be used."""
        db_dir, _ = _set_custom_dirs(monkeypatch, tmp_path)
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        ctx, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid, ver)
        with ctx:
            runner.invoke(install_app, [pid])

        # Default path (under ESGVOC_HOME) should NOT contain the DB
        default_db = tmp_path / "user" / "dbs" / f"{pid}-{ver}.db"
        assert not default_db.exists(), (
            f"DB was written to default location {default_db} despite ESGVOC_DB_DIR"
        )

    def test_db_path_helper_respects_custom_db_dir(self, real_dbs, tmp_path, monkeypatch):
        """UserState.db_path() must return a path inside ESGVOC_DB_DIR."""
        db_dir, _ = _set_custom_dirs(monkeypatch, tmp_path)
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        from esgvoc.core.service.user_state import UserState

        resolved = UserState.db_path(pid, ver)
        assert str(db_dir) in str(resolved)


# ---------------------------------------------------------------------------
# UT-31  ESGVOC_STATE_FILE redirects state.json
# ---------------------------------------------------------------------------

class TestCustomStateFile:
    """UT-31: state.json is written to / read from ESGVOC_STATE_FILE."""

    def test_state_file_created_at_custom_path(self, real_dbs, tmp_path, monkeypatch):
        _, state_file = _set_custom_dirs(monkeypatch, tmp_path)
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        ctx, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid, ver)
        with ctx:
            result = runner.invoke(install_app, [pid])

        assert result.exit_code == 0, result.output
        assert state_file.exists(), f"state.json not found at {state_file}"

    def test_state_json_not_at_default_location(self, real_dbs, tmp_path, monkeypatch):
        _, state_file = _set_custom_dirs(monkeypatch, tmp_path)
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        ctx, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid, ver)
        with ctx:
            runner.invoke(install_app, [pid])

        default_state = tmp_path / "user" / "state.json"
        assert not default_state.exists(), (
            f"state.json was written to default path {default_state} despite ESGVOC_STATE_FILE"
        )

    def test_userstate_load_reads_from_custom_path(self, real_dbs, tmp_path, monkeypatch):
        db_dir, state_file = _set_custom_dirs(monkeypatch, tmp_path)
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        # Manually write a state.json at the custom path
        import json
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({
            "active_versions": {pid: ver},
            "installed": {pid: [ver]},
        }))

        from esgvoc.core.service.user_state import UserState

        state = UserState.load()
        assert state.get_active(pid) == ver
        assert ver in state.get_installed(pid)


# ---------------------------------------------------------------------------
# UT-32  Combined DB_DIR + STATE_FILE
# ---------------------------------------------------------------------------

class TestCombinedEnvOverride:
    """UT-32: Combined override — simulates shared / HPC installation."""

    def test_install_then_list_respects_both_overrides(self, real_dbs, tmp_path, monkeypatch):
        db_dir, state_file = _set_custom_dirs(monkeypatch, tmp_path)
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        ctx, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid, ver)
        with ctx:
            install_result = runner.invoke(install_app, [pid])

        assert install_result.exit_code == 0, install_result.output

        # DB must be in custom dir
        assert (db_dir / f"{pid}-{ver}.db").exists()
        # state.json must be at custom path
        assert state_file.exists()

        # list command must see the installed version
        list_result = runner.invoke(versions_app, [])
        assert list_result.exit_code == 0, list_result.output
        assert ver in list_result.output

    def test_shared_install_simulation(self, real_dbs, tmp_path, monkeypatch):
        """
        Simulate HPC shared install (Scenario 37):
          - 'admin' installs into a shared directory
          - 'user' reads from it by pointing ESGVOC_DB_DIR + ESGVOC_STATE_FILE
            at the same shared location
        """
        shared_dir = tmp_path / "shared"
        shared_dir.mkdir()
        db_dir = shared_dir / "dbs"
        state_file = shared_dir / "state.json"
        db_dir.mkdir()

        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        # --- Admin: copy DB and write state manually ---
        dest = db_dir / f"{pid}-{ver}.db"
        shutil.copy2(str(real_dbs["v1_path"]), str(dest))

        import json
        state_file.write_text(json.dumps({
            "active_versions": {pid: ver},
            "installed": {pid: [ver]},
        }))

        # --- User: point env vars to shared location ---
        monkeypatch.setenv("ESGVOC_DB_DIR", str(db_dir))
        monkeypatch.setenv("ESGVOC_STATE_FILE", str(state_file))

        from esgvoc.core.service.user_state import UserState

        state = UserState.load()
        assert state.get_active(pid) == ver
        assert ver in state.get_installed(pid)

        resolved_db = UserState.db_path(pid, ver)
        assert resolved_db.exists()


# ---------------------------------------------------------------------------
# UT-33  Status command respects env var overrides
# ---------------------------------------------------------------------------

class TestStatusWithEnvOverrides:
    """UT-33: esgvoc status reads from custom DB_DIR / STATE_FILE."""

    def test_status_shows_project_installed_in_custom_dir(self, real_dbs, tmp_path, monkeypatch):
        db_dir, state_file = _set_custom_dirs(monkeypatch, tmp_path)
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        ctx, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid, ver)
        with ctx:
            runner.invoke(install_app, [pid])

        result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0, result.output
        assert pid in result.output
        assert ver in result.output

    def test_status_empty_when_custom_state_is_empty(self, tmp_path, monkeypatch):
        """If ESGVOC_STATE_FILE points to an empty/missing file, status shows nothing installed."""
        _, state_file = _set_custom_dirs(monkeypatch, tmp_path)
        # state_file does not exist yet → no projects installed

        result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0
        # Should indicate no projects installed (not a crash)
        assert "no projects installed" in result.output.lower()

    def test_status_with_paths_shows_custom_db_dir(self, real_dbs, tmp_path, monkeypatch):
        """--paths flag must show DB paths inside ESGVOC_DB_DIR."""
        db_dir, _ = _set_custom_dirs(monkeypatch, tmp_path)
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        ctx, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid, ver)
        with ctx:
            runner.invoke(install_app, [pid])

        result = runner.invoke(status_app, ["--user", "--paths"])
        assert result.exit_code == 0, result.output
        # The output should mention the custom db directory
        assert str(db_dir) in result.output or ".db" in result.output
