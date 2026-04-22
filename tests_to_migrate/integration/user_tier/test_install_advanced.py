"""
User Tier — Advanced install scenarios and compatibility checks.

Plan scenarios covered:
  UT-9   Install with --pre flag requests dev-latest from the fetcher
  UT-26  DBFetcher.check_compatibility: incompatible min_version → (False, msg)
  UT-27  DBFetcher.check_compatibility: incompatible max_version → (False, msg)
  UT-28  DBFetcher.check_compatibility: compatible artifact → (True, "")
  UT-29  update --no-activate downloads new version but keeps old active
  UT-35  Air-gapped / manual install: copy DB + write state → status works
  UT-36  Air-gapped install: use command switches to manually registered version
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from esgvoc.cli.install import app as install_app
from esgvoc.cli.status import app as status_app
from esgvoc.cli.update import app as update_app
from esgvoc.cli.use import app as use_app
from esgvoc.core.db_artifact import DBArtifact

from .conftest import fetcher_that_copies, install_real_db, runner


# ---------------------------------------------------------------------------
# UT-9  Install with --pre flag
# ---------------------------------------------------------------------------

class TestInstallPreRelease:
    """UT-9: --pre flag causes fetcher to request 'dev-latest'."""

    def test_pre_flag_calls_get_artifact_with_dev_latest(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        checksum = hashlib.sha256(real_dbs["v1_path"].read_bytes()).hexdigest()
        artifact = DBArtifact(
            project_id=pid, version=ver,
            download_url=f"https://example.com/{pid}-{ver}.db",
            checksum_sha256=checksum, size_bytes=real_dbs["v1_path"].stat().st_size,
            is_prerelease=True,
        )

        mock_inst = MagicMock()
        mock_inst.get_artifact.return_value = artifact
        mock_inst.list_versions.return_value = [ver]

        def _copy(art, target, **kw):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(real_dbs["v1_path"]), str(target))

        mock_inst.download_db.side_effect = _copy

        with patch("esgvoc.core.db_fetcher.DBFetcher", return_value=mock_inst):
            result = runner.invoke(install_app, [pid, "--pre"])

        assert result.exit_code == 0, result.output
        # The fetcher should have been asked for "dev-latest"
        mock_inst.get_artifact.assert_called_once()
        call_args = mock_inst.get_artifact.call_args
        assert "dev-latest" in (call_args.args + tuple(call_args.kwargs.values())), (
            f"Expected 'dev-latest' in fetcher.get_artifact call; got: {call_args}"
        )

    def test_pre_flag_installs_and_activates_prerelease_db(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = "dev-20240401"  # simulated pre-release version string

        ctx, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid, ver)
        # Override the artifact to be a pre-release
        ctx2, mock_inst, artifact = fetcher_that_copies(real_dbs["v1_path"], pid, ver)
        artifact = DBArtifact(
            project_id=pid, version=ver,
            download_url=f"https://example.com/{pid}-{ver}.db",
            checksum_sha256=artifact.checksum_sha256,
            size_bytes=artifact.size_bytes,
            is_prerelease=True,
        )
        mock_inst.get_artifact.return_value = artifact

        with ctx2:
            result = runner.invoke(install_app, [pid, "--pre"])

        assert result.exit_code == 0, result.output

        from esgvoc.core.service.user_state import UserState
        state = UserState.load()
        assert ver in state.get_installed(pid)


# ---------------------------------------------------------------------------
# UT-26 / UT-27 / UT-28  DBFetcher.check_compatibility
# ---------------------------------------------------------------------------

class TestCompatibilityChecks:
    """UT-26 to UT-28: check_compatibility logic for min/max version constraints."""

    def _make_artifact(self, min_v=None, max_v=None) -> DBArtifact:
        return DBArtifact(
            project_id="cmip6",
            version="v1.0.0",
            download_url="https://example.com/cmip6-v1.0.0.db",
            is_prerelease=False,
            esgvoc_min_version=min_v,
            esgvoc_max_version=max_v,
        )

    def test_compatible_no_constraints(self):
        """UT-28: No constraints → compatible."""
        from esgvoc.core.db_fetcher import DBFetcher
        fetcher = DBFetcher.__new__(DBFetcher)
        fetcher.offline = False
        artifact = self._make_artifact()
        ok, msg = fetcher.check_compatibility(artifact)
        assert ok is True
        assert msg == ""

    def test_incompatible_min_version_too_high(self, monkeypatch):
        """UT-26: min_version > installed esgvoc → incompatible."""
        import esgvoc
        monkeypatch.setattr(esgvoc, "__version__", "1.0.0", raising=False)

        from esgvoc.core.db_fetcher import DBFetcher
        fetcher = DBFetcher.__new__(DBFetcher)
        fetcher.offline = False
        artifact = self._make_artifact(min_v="99.0.0")

        ok, msg = fetcher.check_compatibility(artifact)
        assert ok is False
        assert "requires" in msg.lower() or "99.0.0" in msg

    def test_incompatible_max_version_too_low(self, monkeypatch):
        """UT-27: max_version ≤ installed esgvoc → incompatible (warning)."""
        import esgvoc
        monkeypatch.setattr(esgvoc, "__version__", "99.0.0", raising=False)

        from esgvoc.core.db_fetcher import DBFetcher
        fetcher = DBFetcher.__new__(DBFetcher)
        fetcher.offline = False
        artifact = self._make_artifact(max_v="1.0.0")

        ok, msg = fetcher.check_compatibility(artifact)
        # According to the implementation, max_version breach returns False with a warning
        assert ok is False
        assert "1.0.0" in msg

    def test_compatible_within_min_max_range(self, monkeypatch):
        """Artifact with min=1.0.0 max=99.0.0 → compatible when installed=2.0.0."""
        import esgvoc
        monkeypatch.setattr(esgvoc, "__version__", "2.0.0", raising=False)

        from esgvoc.core.db_fetcher import DBFetcher
        fetcher = DBFetcher.__new__(DBFetcher)
        fetcher.offline = False
        artifact = self._make_artifact(min_v="1.0.0", max_v="99.0.0")

        ok, msg = fetcher.check_compatibility(artifact)
        assert ok is True

    def test_unknown_esgvoc_version_is_always_compatible(self, monkeypatch):
        """If esgvoc.__version__ is unset, all artifacts are allowed."""
        import esgvoc
        monkeypatch.setattr(esgvoc, "__version__", None, raising=False)

        from esgvoc.core.db_fetcher import DBFetcher
        fetcher = DBFetcher.__new__(DBFetcher)
        fetcher.offline = False
        artifact = self._make_artifact(min_v="99.0.0")  # would normally fail

        ok, msg = fetcher.check_compatibility(artifact)
        assert ok is True


# ---------------------------------------------------------------------------
# UT-29  update --no-activate
# ---------------------------------------------------------------------------

class TestUpdateNoActivate:
    """UT-29: update --no-activate downloads new version but keeps old active."""

    def test_no_activate_keeps_old_active(self, real_dbs):
        pid = real_dbs["project_id"]
        ver_old = real_dbs["v1_version"]
        ver_new = real_dbs["v2_version"]

        # Install v1 as active
        ctx_old, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid, ver_old)
        with ctx_old:
            runner.invoke(install_app, [pid])

        # Update to v2 without activating
        ctx_new, mock_inst, artifact_new = fetcher_that_copies(
            real_dbs["v2_path"], pid, ver_new
        )
        mock_inst.list_versions.return_value = [ver_new, ver_old]

        with ctx_new:
            result = runner.invoke(update_app, [pid, "--no-activate"])

        assert result.exit_code == 0, result.output

        from esgvoc.core.service.user_state import UserState
        state = UserState.load()

        # Active should still be v1
        assert state.get_active(pid) == ver_old, (
            f"Active should remain {ver_old}, got {state.get_active(pid)}"
        )
        # v2 should now be installed
        assert ver_new in state.get_installed(pid), \
            f"{ver_new} not found in installed versions: {state.get_installed(pid)}"

    def test_no_activate_new_db_file_exists_on_disk(self, real_dbs):
        pid = real_dbs["project_id"]
        ver_old = real_dbs["v1_version"]
        ver_new = real_dbs["v2_version"]

        ctx_old, _, _ = fetcher_that_copies(real_dbs["v1_path"], pid, ver_old)
        with ctx_old:
            runner.invoke(install_app, [pid])

        ctx_new, mock_inst, _ = fetcher_that_copies(real_dbs["v2_path"], pid, ver_new)
        mock_inst.list_versions.return_value = [ver_new, ver_old]

        with ctx_new:
            runner.invoke(update_app, [pid, "--no-activate"])

        from esgvoc.core.service.user_state import UserState
        assert UserState.db_path(pid, ver_new).exists(), \
            f"New DB {ver_new} should be on disk after --no-activate"


# ---------------------------------------------------------------------------
# UT-35 / UT-36  Air-gapped / manual installation (Scenario 8)
# ---------------------------------------------------------------------------

class TestManualAirgappedInstall:
    """
    UT-35 / UT-36: Simulate Scenario 8 — no network, user copies a DB manually
    and registers it in state.json.  All CLI operations (use, status) should
    work normally with the manually installed DB.
    """

    def _manual_install(self, real_dbs) -> tuple[str, str, Path]:
        """
        Copy a real DB to the User Tier dbs/ dir and write state.json manually.
        Returns (project_id, version, db_path).
        """
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]

        from esgvoc.core.service.user_state import UserState

        db_dest = UserState.db_path(pid, ver)
        db_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(real_dbs["v1_path"]), str(db_dest))

        state = UserState.load()
        state.add_installed(pid, ver)
        state.set_active(pid, ver)
        state.save()
        return pid, ver, db_dest

    def test_manually_installed_db_appears_in_status(self, real_dbs):
        """UT-35: After manual copy + state edit, status shows the project."""
        pid, ver, _ = self._manual_install(real_dbs)

        result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0, result.output
        assert pid in result.output
        assert ver in result.output

    def test_manually_installed_db_file_is_valid_sqlite(self, real_dbs):
        """UT-35: The copied DB is readable as SQLite."""
        _, ver, db_dest = self._manual_install(real_dbs)

        import sqlite3
        conn = sqlite3.connect(str(db_dest))
        rows = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        assert rows[0] == "ok"

    def test_use_command_works_on_manually_installed_version(self, real_dbs):
        """UT-36: After manual install of v1, install v2 via mock, then switch to v1."""
        pid, ver_v1, _ = self._manual_install(real_dbs)
        ver_v2 = real_dbs["v2_version"]

        # Also manually install v2
        from esgvoc.core.service.user_state import UserState
        db_v2 = UserState.db_path(pid, ver_v2)
        db_v2.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(real_dbs["v2_path"]), str(db_v2))
        state = UserState.load()
        state.add_installed(pid, ver_v2)
        state.set_active(pid, ver_v2)  # v2 is now active
        state.save()

        # Switch back to v1 using the CLI
        result = runner.invoke(use_app, [f"{pid}@{ver_v1}"])
        assert result.exit_code == 0, result.output

        state = UserState.load()
        assert state.get_active(pid) == ver_v1

    def test_status_paths_shows_manual_db_path(self, real_dbs):
        """UT-35: status --paths shows the actual file path of the manually copied DB."""
        pid, ver, db_dest = self._manual_install(real_dbs)

        result = runner.invoke(status_app, ["--user", "--paths"])
        assert result.exit_code == 0, result.output
        # The DB filename or directory should appear in the paths output
        assert ".db" in result.output
