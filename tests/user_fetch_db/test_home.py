"""Tests for EsgvocHome — root directory resolution and path layout."""
from pathlib import Path

import pytest

from esgvoc.core.service.configuration.home import EsgvocHome, ENV_VAR


class TestResolution:
    def test_default_uses_platformdirs(self, monkeypatch):
        monkeypatch.delenv(ENV_VAR, raising=False)
        home = EsgvocHome.resolve()
        assert home.root.is_absolute()
        assert "esgvoc" in str(home.root)

    def test_env_var_absolute(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        home = EsgvocHome.resolve()
        assert home.root == tmp_path.resolve()

    def test_env_var_relative(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv(ENV_VAR, "my_esgvoc_home")
        home = EsgvocHome.resolve()
        assert home.root == (tmp_path / "my_esgvoc_home").resolve()

    def test_repr(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        home = EsgvocHome.resolve()
        assert "EsgvocHome" in repr(home)
        assert str(tmp_path.resolve()) in repr(home)


class TestPaths:
    @pytest.fixture
    def home(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        return EsgvocHome.resolve()

    def test_dbs_dir_created(self, home):
        assert home.dbs_dir.exists()
        assert home.dbs_dir == home.root / "dbs"

    def test_dbs_project_dir_created(self, home):
        p = home.dbs_project_dir("cmip7")
        assert p.exists()
        assert p == home.root / "dbs" / "cmip7"

    def test_dbs_pointer_file_path(self, home):
        pf = home.dbs_pointer_file("cmip7")
        assert pf == home.root / "dbs" / "cmip7.active.json"
        assert not pf.exists()  # pointer written by UserState, not by EsgvocHome

    def test_registry_cache_dir_created(self, home):
        assert home.registry_cache_dir.exists()

    def test_admin_dir_created(self, home):
        assert home.admin_dir.exists()
        assert home.admin_dir == home.root / "admin"

    def test_admin_builds_dir_created(self, home):
        assert home.admin_builds_dir.exists()

    def test_dev_dir_created(self, home):
        assert home.dev_dir.exists()
        assert home.dev_dir == home.root / "dev"

    def test_dev_config_dir(self, home):
        p = home.dev_config_dir("my_config")
        assert p.exists()
        assert p == home.root / "dev" / "my_config"

    # Backward-compat aliases
    def test_user_dbs_dir_alias(self, home):
        assert home.user_dbs_dir == home.dbs_dir

    def test_user_cache_dir_alias(self, home):
        assert home.user_cache_dir == home.registry_cache_dir

    def test_user_dir_alias(self, home):
        assert home.user_dir == home.root

    def test_user_state_file_not_written(self, home):
        # The legacy state file must NOT be created automatically
        assert not home.user_state_file.exists()
