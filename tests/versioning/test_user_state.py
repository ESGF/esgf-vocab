"""Tests for UserState — per-project pointer files and filesystem-driven installs."""

import json
from pathlib import Path

import pytest

from esgvoc.core.service.configuration.home import ENV_VAR
from esgvoc.core.service.user_state import UserState


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    """UserState backed by tmp_path, isolated from any real installation."""
    monkeypatch.setenv(ENV_VAR, str(tmp_path))
    monkeypatch.delenv("ESGVOC_DB_DIR", raising=False)
    return UserState.load()


def _make_db(project_id: str, version: str) -> Path:
    """Create a fake DB file at the expected location and return its path."""
    db = UserState.db_path(project_id, version)
    db.parent.mkdir(parents=True, exist_ok=True)
    db.write_bytes(b"fake-db")
    return db


class TestUserStateLoadSave:
    def test_load_creates_empty_state(self, isolated_state):
        assert isolated_state.dump() == {"active_versions": {}, "installed": {}}

    def test_save_and_reload(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        monkeypatch.delenv("ESGVOC_DB_DIR", raising=False)

        state = UserState.load()
        state.set_active("cmip7", "v2.1.0")
        _make_db("cmip7", "v2.1.0")
        state.save()  # no-op in new model

        reloaded = UserState.load()
        assert reloaded.get_active("cmip7") == "v2.1.0"
        assert "v2.1.0" in reloaded.get_installed("cmip7")

    def test_set_active_writes_pointer_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        monkeypatch.delenv("ESGVOC_DB_DIR", raising=False)

        state = UserState.load()
        state.set_active("cmip7", "v2.1.0")
        state.save()

        pointer = tmp_path / "dbs" / "cmip7.active.json"
        assert pointer.exists()
        data = json.loads(pointer.read_text())
        assert data["active"] == "v2.1.0"

    def test_load_tolerates_corrupted_pointer(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        monkeypatch.delenv("ESGVOC_DB_DIR", raising=False)

        pointer = tmp_path / "dbs" / "cmip7.active.json"
        pointer.parent.mkdir(parents=True, exist_ok=True)
        pointer.write_text("{not valid json")

        state = UserState.load()
        assert state.get_active("cmip7") is None
        assert state.dump() == {"active_versions": {}, "installed": {}}


class TestUserStateActiveVersions:
    def test_set_and_get_active(self, isolated_state):
        isolated_state.set_active("cmip7", "v2.1.0")
        assert isolated_state.get_active("cmip7") == "v2.1.0"

    def test_get_active_unknown_project(self, isolated_state):
        assert isolated_state.get_active("unknown") is None

    def test_remove_active(self, isolated_state):
        isolated_state.set_active("cmip7", "v2.1.0")
        isolated_state.remove_active("cmip7")
        assert isolated_state.get_active("cmip7") is None

    def test_remove_active_missing_is_noop(self, isolated_state):
        isolated_state.remove_active("no-such-project")  # must not raise

    def test_overwrite_active(self, isolated_state):
        isolated_state.set_active("cmip7", "v2.0.0")
        isolated_state.set_active("cmip7", "v2.1.0")
        assert isolated_state.get_active("cmip7") == "v2.1.0"

    def test_get_active_source(self, isolated_state):
        isolated_state.set_active("cmip7", "v2.1.0", source="registry")
        assert isolated_state.get_active_source("cmip7") == "registry"

    def test_get_active_checksum(self, isolated_state):
        isolated_state.set_active("cmip7", "v2.1.0", checksum="abc123")
        assert isolated_state.get_active_checksum("cmip7") == "abc123"


class TestUserStateInstalledVersions:
    def test_add_installed_creates_dir(self, isolated_state):
        # add_installed is a no-op; file presence is what matters
        isolated_state.add_installed("cmip7", "v2.1.0")
        # Directory should exist even if no file was created
        assert UserState.db_path("cmip7", "v2.1.0").parent.exists()

    def test_get_installed_scans_db_files(self, isolated_state):
        _make_db("cmip7", "v2.1.0")
        assert "v2.1.0" in isolated_state.get_installed("cmip7")

    def test_get_installed_no_duplicates(self, isolated_state):
        _make_db("cmip7", "v2.1.0")
        assert isolated_state.get_installed("cmip7").count("v2.1.0") == 1

    def test_multiple_versions_coexist(self, isolated_state):
        _make_db("cmip7", "v2.0.0")
        _make_db("cmip7", "v2.1.0")
        installed = isolated_state.get_installed("cmip7")
        assert "v2.0.0" in installed
        assert "v2.1.0" in installed

    def test_remove_installed(self, isolated_state):
        _make_db("cmip7", "v2.0.0")
        _make_db("cmip7", "v2.1.0")
        isolated_state.remove_installed("cmip7", "v2.0.0")
        assert "v2.0.0" not in isolated_state.get_installed("cmip7")
        assert "v2.1.0" in isolated_state.get_installed("cmip7")

    def test_remove_installed_deletes_file(self, isolated_state):
        db = _make_db("cmip7", "v2.1.0")
        isolated_state.remove_installed("cmip7", "v2.1.0")
        assert not db.exists()

    def test_remove_last_version_leaves_empty(self, isolated_state):
        _make_db("cmip7", "v2.1.0")
        isolated_state.remove_installed("cmip7", "v2.1.0")
        assert isolated_state.get_installed("cmip7") == []
        assert "cmip7" not in isolated_state.dump().get("installed", {})

    def test_remove_installed_clears_active_pointer(self, isolated_state):
        _make_db("cmip7", "v2.1.0")
        isolated_state.set_active("cmip7", "v2.1.0")
        isolated_state.remove_installed("cmip7", "v2.1.0")
        assert isolated_state.get_active("cmip7") is None

    def test_get_installed_unknown_project(self, isolated_state):
        assert isolated_state.get_installed("no-such") == []

    def test_all_project_ids(self, isolated_state):
        _make_db("cmip7", "v2.1.0")
        _make_db("cmip6", "v6.5.0")
        ids = isolated_state.all_project_ids()
        assert "cmip7" in ids
        assert "cmip6" in ids

    def test_all_project_ids_empty_when_no_dbs(self, isolated_state):
        assert isolated_state.all_project_ids() == []


class TestUserStateDBPath:
    def test_db_path_uses_esgvoc_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        monkeypatch.delenv("ESGVOC_DB_DIR", raising=False)

        path = UserState.db_path("cmip7", "v2.1.0")
        assert path == tmp_path / "dbs" / "cmip7" / "v2.1.0.db"

    def test_db_path_uses_esgvoc_db_dir_env(self, tmp_path, monkeypatch):
        custom_db_dir = tmp_path / "shared_dbs"
        monkeypatch.setenv("ESGVOC_DB_DIR", str(custom_db_dir))

        path = UserState.db_path("cmip7", "v2.1.0")
        assert path == custom_db_dir / "cmip7" / "v2.1.0.db"

    def test_db_path_filename_convention(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        monkeypatch.delenv("ESGVOC_DB_DIR", raising=False)

        path = UserState.db_path("cmip6", "v6.5.0")
        assert path.name == "v6.5.0.db"
        assert path.parent.name == "cmip6"
