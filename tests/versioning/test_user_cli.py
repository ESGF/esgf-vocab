"""
Tests for User Tier CLI commands: install, use, list, remove, update.

Network operations (GitHub Releases API) are fully mocked.
All tests use a fresh ESGVOC_HOME via tmp_path so they don't touch the real
user home directory.

Note on Typer test invocation:
  Apps with a single command don't need the command name as the first arg.
  e.g. runner.invoke(install_app, ["cmip7"])  — NOT ["install", "cmip7"]

Note on mock patch paths:
  CLI functions use lazy imports (inside the function body), so DBFetcher must be
  patched at its source: "esgvoc.core.db_fetcher.DBFetcher".
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from esgvoc.cli.install import app as install_app
from esgvoc.cli.use import app as use_app
from esgvoc.cli.versions import app as versions_app
from esgvoc.cli.remove import app as remove_app
from esgvoc.cli.update import app as update_app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Route all UserState and EsgvocHome operations to a temp directory."""
    monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
    yield tmp_path


def _make_fake_artifact(project_id="cmip7", version="v2.1.0", size=1_048_576):
    from esgvoc.core.db_artifact import DBArtifact
    return DBArtifact(
        project_id=project_id,
        version=version,
        download_url=f"https://example.com/{project_id}-{version}.db",
        checksum_sha256="abc123",
        size_bytes=size,
        is_prerelease=False,
    )


def _install_fake_db(tmp_path, project_id="cmip7", version="v2.1.0") -> Path:
    """Write a fake DB file and register it in state.json."""
    from esgvoc.core.service.user_state import UserState

    state = UserState.load()
    db = UserState.db_path(project_id, version)
    db.parent.mkdir(parents=True, exist_ok=True)
    db.write_bytes(b"fake-db-content")
    state.add_installed(project_id, version)
    state.set_active(project_id, version)
    state.save()
    return db


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

class TestInstallUserTier:
    def test_install_unknown_project(self):
        result = runner.invoke(install_app, ["not-a-real-project"])
        assert result.exit_code != 0
        assert "Unknown project" in result.output

    def test_install_downloads_and_activates(self):
        artifact = _make_fake_artifact()

        def fake_download(art, target, show_progress=True):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"fake-db")

        with patch("esgvoc.core.db_fetcher.DBFetcher") as MockFetcher:
            instance = MockFetcher.return_value
            instance.get_artifact.return_value = artifact
            instance.download_db.side_effect = fake_download

            result = runner.invoke(install_app, ["cmip7"])

        assert result.exit_code == 0, result.output
        assert "Installed and activated" in result.output
        assert "cmip7" in result.output
        assert "v2.1.0" in result.output

    def test_install_no_activate_flag(self):
        artifact = _make_fake_artifact()

        def fake_download(art, target, show_progress=True):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"fake-db")

        with patch("esgvoc.core.db_fetcher.DBFetcher") as MockFetcher:
            instance = MockFetcher.return_value
            instance.get_artifact.return_value = artifact
            instance.download_db.side_effect = fake_download

            result = runner.invoke(install_app, ["cmip7", "--no-activate"])

        assert result.exit_code == 0, result.output
        assert "not activated" in result.output

        from esgvoc.core.service.user_state import UserState
        state = UserState.load()
        assert state.get_active("cmip7") is None
        assert "v2.1.0" in state.get_installed("cmip7")

    def test_install_version_not_found(self):
        from esgvoc.core.db_fetcher import EsgvocVersionNotFoundError

        with patch("esgvoc.core.db_fetcher.DBFetcher") as MockFetcher:
            instance = MockFetcher.return_value
            instance.get_artifact.side_effect = EsgvocVersionNotFoundError("not found")

            result = runner.invoke(install_app, ["cmip7@v99.0.0"])

        assert result.exit_code == 3

    def test_install_with_version_spec(self):
        artifact = _make_fake_artifact(version="v2.0.0")

        def fake_download(art, target, show_progress=True):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"fake-db")

        with patch("esgvoc.core.db_fetcher.DBFetcher") as MockFetcher:
            instance = MockFetcher.return_value
            instance.get_artifact.return_value = artifact
            instance.download_db.side_effect = fake_download

            result = runner.invoke(install_app, ["cmip7@v2.0.0"])

        assert result.exit_code == 0, result.output
        instance.get_artifact.assert_called_once_with("cmip7", version="v2.0.0")

    def test_install_skips_download_if_checksum_matches(self, tmp_path):
        content = b"already-downloaded"
        sha = hashlib.sha256(content).hexdigest()

        from esgvoc.core.db_artifact import DBArtifact
        artifact = DBArtifact(
            project_id="cmip7", version="v2.1.0",
            download_url="https://example.com/cmip7-v2.1.0.db",
            checksum_sha256=sha, size_bytes=len(content),
        )

        from esgvoc.core.service.user_state import UserState
        target = UserState.db_path("cmip7", "v2.1.0")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

        with patch("esgvoc.core.db_fetcher.DBFetcher") as MockFetcher:
            instance = MockFetcher.return_value
            instance.get_artifact.return_value = artifact

            result = runner.invoke(install_app, ["cmip7"])

        assert result.exit_code == 0, result.output
        instance.download_db.assert_not_called()
        assert "already on disk" in result.output


# ---------------------------------------------------------------------------
# use
# ---------------------------------------------------------------------------

class TestUseCommand:
    def test_use_sets_active_version(self, tmp_path):
        _install_fake_db(tmp_path, "cmip7", "v2.0.0")
        _install_fake_db(tmp_path, "cmip7", "v2.1.0")

        result = runner.invoke(use_app, ["cmip7@v2.0.0"])
        assert result.exit_code == 0, result.output

        from esgvoc.core.service.user_state import UserState
        assert UserState.load().get_active("cmip7") == "v2.0.0"

    def test_use_no_version_defaults_to_last_installed(self, tmp_path):
        _install_fake_db(tmp_path, "cmip7", "v2.0.0")
        _install_fake_db(tmp_path, "cmip7", "v2.1.0")

        result = runner.invoke(use_app, ["cmip7"])
        assert result.exit_code == 0, result.output

        from esgvoc.core.service.user_state import UserState
        assert UserState.load().get_active("cmip7") == "v2.1.0"

    def test_use_not_installed_fails(self, tmp_path):
        _install_fake_db(tmp_path, "cmip7", "v2.1.0")

        result = runner.invoke(use_app, ["cmip7@v9.9.9"])
        assert result.exit_code != 0
        assert "not installed" in result.output

    def test_use_project_not_installed_at_all(self):
        result = runner.invoke(use_app, ["cmip7"])
        assert result.exit_code != 0
        assert "No versions installed" in result.output

    def test_use_missing_db_file_fails(self):
        from esgvoc.core.service.user_state import UserState

        state = UserState.load()
        state.add_installed("cmip7", "v2.1.0")
        state.set_active("cmip7", "v2.1.0")
        state.save()
        # File NOT created on disk

        result = runner.invoke(use_app, ["cmip7@v2.1.0"])
        assert result.exit_code != 0
        assert "missing" in result.output


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

class TestListCommand:
    def test_list_no_projects_installed(self):
        result = runner.invoke(versions_app, [])
        assert result.exit_code == 0
        assert "No projects installed" in result.output

    def test_list_shows_installed(self, tmp_path):
        _install_fake_db(tmp_path, "cmip7", "v2.0.0")
        _install_fake_db(tmp_path, "cmip7", "v2.1.0")

        result = runner.invoke(versions_app, [])
        assert result.exit_code == 0
        assert "v2.0.0" in result.output
        assert "v2.1.0" in result.output
        assert "active" in result.output

    def test_list_specific_project(self, tmp_path):
        _install_fake_db(tmp_path, "cmip7", "v2.1.0")
        _install_fake_db(tmp_path, "cmip6", "v6.5.0")

        result = runner.invoke(versions_app, ["cmip7"])
        assert result.exit_code == 0
        assert "v2.1.0" in result.output
        assert "v6.5.0" not in result.output


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------

class TestRemoveCommand:
    def test_remove_specific_version(self, tmp_path):
        _install_fake_db(tmp_path, "cmip7", "v2.0.0")
        _install_fake_db(tmp_path, "cmip7", "v2.1.0")

        result = runner.invoke(remove_app, ["cmip7@v2.0.0", "--yes"])
        assert result.exit_code == 0, result.output

        from esgvoc.core.service.user_state import UserState
        state = UserState.load()
        assert "v2.0.0" not in state.get_installed("cmip7")
        assert "v2.1.0" in state.get_installed("cmip7")

    def test_remove_all_versions(self, tmp_path):
        _install_fake_db(tmp_path, "cmip7", "v2.0.0")
        _install_fake_db(tmp_path, "cmip7", "v2.1.0")

        result = runner.invoke(remove_app, ["cmip7", "--all", "--yes"])
        assert result.exit_code == 0, result.output

        from esgvoc.core.service.user_state import UserState
        assert UserState.load().get_installed("cmip7") == []

    def test_remove_clears_active_if_active_removed(self, tmp_path):
        _install_fake_db(tmp_path, "cmip7", "v2.1.0")

        result = runner.invoke(remove_app, ["cmip7@v2.1.0", "--yes"])
        assert result.exit_code == 0

        from esgvoc.core.service.user_state import UserState
        assert UserState.load().get_active("cmip7") is None

    def test_remove_not_installed_fails(self, tmp_path):
        _install_fake_db(tmp_path, "cmip7", "v2.1.0")

        result = runner.invoke(remove_app, ["cmip7@v9.9.9", "--yes"])
        assert result.exit_code != 0

    def test_remove_nothing_installed(self):
        result = runner.invoke(remove_app, ["cmip7", "--yes"])
        assert result.exit_code == 0  # graceful

    def test_remove_deletes_db_file(self, tmp_path):
        db = _install_fake_db(tmp_path, "cmip7", "v2.1.0")
        assert db.exists()

        runner.invoke(remove_app, ["cmip7@v2.1.0", "--yes"])
        assert not db.exists()


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestUpdateCommand:
    def test_update_already_latest(self, tmp_path):
        _install_fake_db(tmp_path, "cmip7", "v2.1.0")
        artifact = _make_fake_artifact(version="v2.1.0")

        with patch("esgvoc.core.db_fetcher.DBFetcher") as MockFetcher:
            instance = MockFetcher.return_value
            instance.get_artifact.return_value = artifact

            result = runner.invoke(update_app, ["cmip7"])

        assert result.exit_code == 0
        assert "already at" in result.output

    def test_update_downloads_new_version(self, tmp_path):
        _install_fake_db(tmp_path, "cmip7", "v2.0.0")
        artifact = _make_fake_artifact(version="v2.1.0")

        def fake_download(art, target, **kw):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"new-db")

        with patch("esgvoc.core.db_fetcher.DBFetcher") as MockFetcher:
            instance = MockFetcher.return_value
            instance.get_artifact.return_value = artifact
            instance.download_db.side_effect = fake_download

            result = runner.invoke(update_app, ["cmip7"])

        assert result.exit_code == 0, result.output
        assert "v2.1.0" in result.output

        from esgvoc.core.service.user_state import UserState
        assert UserState.load().get_active("cmip7") == "v2.1.0"

    def test_update_check_flag_no_download(self, tmp_path):
        _install_fake_db(tmp_path, "cmip7", "v2.0.0")
        artifact = _make_fake_artifact(version="v2.1.0")

        with patch("esgvoc.core.db_fetcher.DBFetcher") as MockFetcher:
            instance = MockFetcher.return_value
            instance.get_artifact.return_value = artifact

            result = runner.invoke(update_app, ["cmip7", "--check"])

        assert result.exit_code == 0, result.output
        assert "v2.1.0" in result.output
        instance.download_db.assert_not_called()

        from esgvoc.core.service.user_state import UserState
        assert UserState.load().get_active("cmip7") == "v2.0.0"

    def test_update_no_projects_installed(self):
        result = runner.invoke(update_app, [])
        assert result.exit_code == 0
        assert "No projects installed" in result.output
