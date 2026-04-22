"""
Tests for the `esgvoc use` CLI command.

Downloads are intercepted by patching DBFetcher — no real network calls.
"""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from esgvoc.cli.use import app as use_app
from esgvoc.core.db_artifact import DBArtifact
from esgvoc.core.service.user_state import UserState
from .conftest import make_db, sha256

runner = CliRunner()


def _make_artifact(db_path: Path, project_id: str, version: str) -> DBArtifact:
    return DBArtifact(
        project_id=project_id,
        version=version,
        download_url=f"https://example.com/{project_id}-{version}.db",
        checksum_sha256=sha256(db_path),
        size_bytes=db_path.stat().st_size,
        is_prerelease=False,
    )


def mock_fetcher(artifact: DBArtifact):
    """Return a context manager that patches DBFetcher with a mock that copies the DB."""
    mock = MagicMock()
    mock.get_artifact.return_value = artifact

    def _copy(art, target, show_progress=True, **kw):
        target.parent.mkdir(parents=True, exist_ok=True)
        # Simulate download by creating a minimal DB
        conn = sqlite3.connect(str(target))
        conn.execute(
            "CREATE TABLE _esgvoc_metadata (key TEXT PRIMARY KEY, value TEXT)"
        )
        conn.executemany(
            "INSERT INTO _esgvoc_metadata VALUES (?, ?)",
            [("project_id", art.project_id), ("cv_version", art.version)],
        )
        conn.commit()
        conn.close()

    mock.download_db.side_effect = _copy
    return patch("esgvoc.cli.use.DBFetcher", return_value=mock), mock


class TestUseRegistryVersion:
    def test_use_downloads_and_activates(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        # Pre-create the DB so the checksum check passes
        db = UserState.db_path("universe", "v1.0.0")
        db.parent.mkdir(parents=True, exist_ok=True)
        make_db(db, "universe", "1.0.0")
        artifact = _make_artifact(db, "universe", "v1.0.0")
        db.unlink()  # remove so the use command must "download" it

        mock_inst = MagicMock()
        mock_inst.get_artifact.return_value = artifact

        def _copy(art, target, show_progress=True, **kw):
            make_db(target, "universe", "1.0.0")

        mock_inst.download_db.side_effect = _copy

        # DBFetcher is lazily imported inside the function body — patch at module level
        with patch("esgvoc.core.db_fetcher.DBFetcher", return_value=mock_inst):
            result = runner.invoke(use_app, ["universe@v1.0.0"])

        assert result.exit_code == 0, result.output
        state = UserState.load()
        assert state.get_active("universe") == "v1.0.0"

    def test_use_skips_download_if_checksum_matches(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        db = UserState.db_path("universe", "v1.0.0")
        make_db(db, "universe", "1.0.0")
        artifact = _make_artifact(db, "universe", "v1.0.0")

        mock_inst = MagicMock()
        mock_inst.get_artifact.return_value = artifact

        with patch("esgvoc.core.db_fetcher.DBFetcher", return_value=mock_inst):
            result = runner.invoke(use_app, ["universe@v1.0.0"])

        assert result.exit_code == 0, result.output
        mock_inst.download_db.assert_not_called()

    def test_use_unknown_project_exits_nonzero(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        result = runner.invoke(use_app, ["totally_unknown_project@v1.0.0"])
        assert result.exit_code != 0

    def test_use_version_not_found_exit_3(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        from esgvoc.core.db_fetcher import EsgvocVersionNotFoundError

        mock_inst = MagicMock()
        mock_inst.get_artifact.side_effect = EsgvocVersionNotFoundError("not found")

        with patch("esgvoc.core.db_fetcher.DBFetcher", return_value=mock_inst):
            result = runner.invoke(use_app, ["universe@v99.0.0"])

        assert result.exit_code == 3

    def test_use_network_error_exit_2(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        from esgvoc.core.db_fetcher import EsgvocNetworkError

        mock_inst = MagicMock()
        mock_inst.get_artifact.side_effect = EsgvocNetworkError("no network")

        with patch("esgvoc.core.db_fetcher.DBFetcher", return_value=mock_inst):
            result = runner.invoke(use_app, ["universe@v1.0.0"])

        assert result.exit_code == 2


class TestUseLocalVersion:
    def test_use_local_already_present(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        make_db(UserState.db_path("universe", "my-exp"))
        result = runner.invoke(use_app, ["universe@my-exp"])
        assert result.exit_code == 0, result.output
        assert UserState.load().get_active("universe") == "my-exp"

    def test_use_local_missing_exits_1(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        result = runner.invoke(use_app, ["universe@my-missing-exp"])
        assert result.exit_code == 1

    def test_use_no_name_activates_newest_installed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        for ver in ["v1.0.0", "v2.0.0"]:
            make_db(UserState.db_path("universe", ver))
        result = runner.invoke(use_app, ["universe"])
        assert result.exit_code == 0, result.output
        # Should activate the last sorted version
        assert UserState.load().get_active("universe") is not None

    def test_use_no_name_no_installed_exits_1(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        result = runner.invoke(use_app, ["universe"])
        assert result.exit_code == 1
