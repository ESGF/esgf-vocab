"""Tests for EsgvocHome — root directory resolution."""

import os
from pathlib import Path

import pytest

from esgvoc.core.service.configuration.home import EsgvocHome, ENV_VAR


class TestEsgvocHomeResolution:
    def test_default_uses_platformdirs(self, monkeypatch):
        monkeypatch.delenv(ENV_VAR, raising=False)
        home = EsgvocHome.resolve()
        # Should be an absolute path containing 'esgvoc'
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
        assert str(tmp_path) in repr(home)


class TestEsgvocHomePaths:
    @pytest.fixture
    def home(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        return EsgvocHome.resolve()

    def test_user_dir_created(self, home):
        assert home.user_dir.exists()
        assert home.user_dir == home.root / "user"

    def test_user_dbs_dir_created(self, home):
        assert home.user_dbs_dir.exists()
        assert home.user_dbs_dir == home.root / "user" / "dbs"

    def test_user_state_file_path(self, home):
        assert home.user_state_file == home.root / "user" / "state.json"
        assert not home.user_state_file.exists()  # not created until written

    def test_user_cache_dir_created(self, home):
        assert home.user_cache_dir.exists()
        assert home.user_cache_dir == home.root / "user" / "cache"

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

    def test_dev_config_dir_default(self, home):
        p = home.dev_config_dir("default")
        assert p.exists()
        assert p.name == "default"
