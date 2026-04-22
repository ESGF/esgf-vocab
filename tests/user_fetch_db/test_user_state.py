"""Tests for UserState — per-project pointer-file state management."""
import json
from pathlib import Path

import pytest

from esgvoc.core.service.user_state import UserState
from .conftest import make_db


class TestActivePointer:
    def test_get_active_none_when_no_pointer(self):
        state = UserState.load()
        assert state.get_active("cmip7") is None

    def test_set_and_get_active(self):
        state = UserState.load()
        state.set_active("cmip7", "v1.0.0")
        assert state.get_active("cmip7") == "v1.0.0"

    def test_pointer_file_written_to_disk(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        state = UserState.load()
        state.set_active("cmip7", "v1.0.0")
        pointer = tmp_path / "dbs" / "cmip7.active.json"
        assert pointer.exists()
        data = json.loads(pointer.read_text())
        assert data["active"] == "v1.0.0"

    def test_set_active_includes_source(self):
        state = UserState.load()
        state.set_active("cmip7", "v1.0.0", source="registry")
        assert state.get_active_source("cmip7") == "registry"

    def test_set_active_local_source(self):
        state = UserState.load()
        state.set_active("cmip7", "my-exp", source="local")
        assert state.get_active_source("cmip7") == "local"

    def test_set_active_with_checksum(self):
        state = UserState.load()
        state.set_active("cmip7", "v1.0.0", checksum="abc123")
        assert state.get_active_checksum("cmip7") == "abc123"

    def test_remove_active(self):
        state = UserState.load()
        state.set_active("cmip7", "v1.0.0")
        state.remove_active("cmip7")
        assert state.get_active("cmip7") is None

    def test_remove_active_noop_if_no_pointer(self):
        state = UserState.load()
        state.remove_active("doesnotexist")  # must not raise

    def test_save_is_noop(self):
        state = UserState.load()
        state.set_active("cmip7", "v1.0.0")
        state.save()  # must not raise, pointer already written
        assert state.get_active("cmip7") == "v1.0.0"


class TestInstalledVersions:
    def test_get_installed_empty(self):
        state = UserState.load()
        assert state.get_installed("cmip7") == []

    def test_get_installed_reflects_db_files(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        state = UserState.load()
        db = UserState.db_path("cmip7", "v1.0.0")
        make_db(db, "cmip7", "1.0.0")
        installed = state.get_installed("cmip7")
        assert "v1.0.0" in installed

    def test_multiple_versions_listed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        for ver in ["v1.0.0", "v1.1.0", "v2.0.0"]:
            make_db(UserState.db_path("cmip7", ver))
        installed = UserState.load().get_installed("cmip7")
        assert set(installed) == {"v1.0.0", "v1.1.0", "v2.0.0"}

    def test_add_installed_is_noop_but_creates_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        state = UserState.load()
        state.add_installed("cmip7", "v1.0.0")
        proj_dir = tmp_path / "dbs" / "cmip7"
        assert proj_dir.exists()
        assert state.get_installed("cmip7") == []  # no .db file yet

    def test_remove_installed_deletes_db_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        db = UserState.db_path("cmip7", "v1.0.0")
        make_db(db)
        state = UserState.load()
        state.remove_installed("cmip7", "v1.0.0")
        assert not db.exists()
        assert state.get_installed("cmip7") == []

    def test_remove_installed_clears_pointer_if_active(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        db = UserState.db_path("cmip7", "v1.0.0")
        make_db(db)
        state = UserState.load()
        state.set_active("cmip7", "v1.0.0")
        state.remove_installed("cmip7", "v1.0.0")
        assert state.get_active("cmip7") is None

    def test_remove_installed_does_not_clear_pointer_for_other_version(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        for ver in ["v1.0.0", "v2.0.0"]:
            make_db(UserState.db_path("cmip7", ver))
        state = UserState.load()
        state.set_active("cmip7", "v2.0.0")
        state.remove_installed("cmip7", "v1.0.0")
        assert state.get_active("cmip7") == "v2.0.0"


class TestAllProjectIds:
    def test_empty_when_no_dbs(self):
        assert UserState.load().all_project_ids() == []

    def test_returns_projects_with_db_files(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        for pid in ["cmip7", "universe"]:
            make_db(UserState.db_path(pid, "v1.0.0"), pid)
        pids = UserState.load().all_project_ids()
        assert set(pids) == {"cmip7", "universe"}

    def test_ignores_dirs_without_db_files(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        empty = tmp_path / "dbs" / "empty_project"
        empty.mkdir(parents=True)
        assert UserState.load().all_project_ids() == []


class TestDbPath:
    def test_db_path_structure(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        p = UserState.db_path("cmip7", "v1.0.0")
        assert p == tmp_path / "dbs" / "cmip7" / "v1.0.0.db"

    def test_esgvoc_db_dir_override(self, tmp_path, monkeypatch):
        db_dir = tmp_path / "custom_dbs"
        monkeypatch.setenv("ESGVOC_DB_DIR", str(db_dir))
        p = UserState.db_path("cmip7", "v1.0.0")
        assert p == db_dir / "cmip7" / "v1.0.0.db"


class TestDump:
    def test_dump_empty(self):
        result = UserState.load().dump()
        assert result == {"active_versions": {}, "installed": {}}

    def test_dump_reflects_state(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        make_db(UserState.db_path("cmip7", "v1.0.0"))
        state = UserState.load()
        state.set_active("cmip7", "v1.0.0")
        d = state.dump()
        assert "cmip7" in d["installed"]
        assert d["active_versions"]["cmip7"] == "v1.0.0"
