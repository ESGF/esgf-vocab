"""Tests for UserState — state.json management for the User Tier."""

import json
from pathlib import Path

import pytest

from esgvoc.core.service.configuration.home import ENV_VAR
from esgvoc.core.service.user_state import UserState


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    """UserState backed by a tmp_path, isolated from any real installation."""
    monkeypatch.setenv(ENV_VAR, str(tmp_path))
    monkeypatch.delenv("ESGVOC_STATE_FILE", raising=False)
    monkeypatch.delenv("ESGVOC_DB_DIR", raising=False)
    return UserState.load()


class TestUserStateLoadSave:
    def test_load_creates_empty_state(self, isolated_state):
        assert isolated_state.dump() == {"active_versions": {}, "installed": {}}

    def test_save_and_reload(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        monkeypatch.delenv("ESGVOC_STATE_FILE", raising=False)

        state = UserState.load()
        state.set_active("cmip7", "v2.1.0")
        state.add_installed("cmip7", "v2.1.0")
        state.save()

        reloaded = UserState.load()
        assert reloaded.get_active("cmip7") == "v2.1.0"
        assert "v2.1.0" in reloaded.get_installed("cmip7")

    def test_save_is_atomic(self, tmp_path, monkeypatch):
        """save() must not leave a partial file on disk."""
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        monkeypatch.delenv("ESGVOC_STATE_FILE", raising=False)

        state = UserState.load()
        state.set_active("cmip7", "v2.1.0")
        state.save()

        state_file = tmp_path / "user" / "state.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["active_versions"]["cmip7"] == "v2.1.0"

    def test_load_tolerates_corrupted_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        monkeypatch.delenv("ESGVOC_STATE_FILE", raising=False)

        state_file = tmp_path / "user" / "state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("{not valid json")

        state = UserState.load()
        assert state.dump() == {"active_versions": {}, "installed": {}}

    def test_esgvoc_state_file_env_var(self, tmp_path, monkeypatch):
        custom = tmp_path / "custom_state.json"
        monkeypatch.setenv("ESGVOC_STATE_FILE", str(custom))
        monkeypatch.delenv(ENV_VAR, raising=False)

        state = UserState.load()
        state.set_active("cmip6", "v6.5.0")
        state.save()

        assert custom.exists()


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


class TestUserStateInstalledVersions:
    def test_add_installed(self, isolated_state):
        isolated_state.add_installed("cmip7", "v2.1.0")
        assert "v2.1.0" in isolated_state.get_installed("cmip7")

    def test_add_installed_no_duplicates(self, isolated_state):
        isolated_state.add_installed("cmip7", "v2.1.0")
        isolated_state.add_installed("cmip7", "v2.1.0")
        assert isolated_state.get_installed("cmip7").count("v2.1.0") == 1

    def test_multiple_versions_coexist(self, isolated_state):
        isolated_state.add_installed("cmip7", "v2.0.0")
        isolated_state.add_installed("cmip7", "v2.1.0")
        installed = isolated_state.get_installed("cmip7")
        assert "v2.0.0" in installed
        assert "v2.1.0" in installed

    def test_remove_installed(self, isolated_state):
        isolated_state.add_installed("cmip7", "v2.0.0")
        isolated_state.add_installed("cmip7", "v2.1.0")
        isolated_state.remove_installed("cmip7", "v2.0.0")
        assert "v2.0.0" not in isolated_state.get_installed("cmip7")
        assert "v2.1.0" in isolated_state.get_installed("cmip7")

    def test_remove_last_version_cleans_project_key(self, isolated_state):
        isolated_state.add_installed("cmip7", "v2.1.0")
        isolated_state.remove_installed("cmip7", "v2.1.0")
        assert isolated_state.get_installed("cmip7") == []
        assert "cmip7" not in isolated_state.dump().get("installed", {})

    def test_get_installed_unknown_project(self, isolated_state):
        assert isolated_state.get_installed("no-such") == []

    def test_all_project_ids(self, isolated_state):
        isolated_state.add_installed("cmip7", "v2.1.0")
        isolated_state.add_installed("cmip6", "v6.5.0")
        ids = isolated_state.all_project_ids()
        assert "cmip7" in ids
        assert "cmip6" in ids


class TestUserStateDBPath:
    def test_db_path_uses_esgvoc_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        monkeypatch.delenv("ESGVOC_DB_DIR", raising=False)

        path = UserState.db_path("cmip7", "v2.1.0")
        assert path == tmp_path / "user" / "dbs" / "cmip7-v2.1.0.db"

    def test_db_path_uses_esgvoc_db_dir_env(self, tmp_path, monkeypatch):
        custom_db_dir = tmp_path / "shared_dbs"
        monkeypatch.setenv("ESGVOC_DB_DIR", str(custom_db_dir))

        path = UserState.db_path("cmip7", "v2.1.0")
        assert path == custom_db_dir / "cmip7-v2.1.0.db"

    def test_db_path_filename_convention(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        monkeypatch.delenv("ESGVOC_DB_DIR", raising=False)

        path = UserState.db_path("cmip6", "v6.5.0")
        assert path.name == "cmip6-v6.5.0.db"
