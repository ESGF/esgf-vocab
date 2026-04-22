"""Tests for backward-compatible ProjectSettings alias and SourceProjectSettings."""

import pytest

from esgvoc.core.service.configuration.setting import (
    ProjectSettings,
    SourceProjectSettings,
    resolve_path_to_absolute,
)
from esgvoc.core.service.configuration.home import ENV_VAR


class TestProjectSettingsAlias:
    def test_alias_is_same_class(self):
        assert ProjectSettings is SourceProjectSettings

    def test_create_via_old_name(self):
        p = ProjectSettings(
            project_name="cmip7",
            github_repo="https://github.com/WCRP-CMIP/CMIP7-CVs",
        )
        assert p.project_name == "cmip7"
        assert p.branch == "main"
        assert p.offline_mode is False

    def test_create_via_new_name(self):
        p = SourceProjectSettings(
            project_name="cmip6",
            github_repo="https://github.com/WCRP-CMIP/CMIP6_CVs",
            branch="esgvoc",
        )
        assert p.project_name == "cmip6"
        assert p.branch == "esgvoc"

    def test_optional_fields_default_none(self):
        p = ProjectSettings(
            project_name="x",
            github_repo="https://github.com/org/repo",
        )
        assert p.local_path is None
        assert p.db_path is None

    def test_config_name_affects_path_resolution(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        p = ProjectSettings(
            project_name="cmip7",
            github_repo="https://github.com/WCRP-CMIP/CMIP7-CVs",
            local_path="repos/CMIP7-CVs",
            db_path="dbs/cmip7.db",
        )
        p.set_config_name("my_config")

        local = p.get_absolute_local_path()
        assert local is not None
        assert "my_config" in local
        assert local.endswith("repos/CMIP7-CVs")

        db = p.get_absolute_db_path()
        assert db is not None
        assert "my_config" in db
        assert db.endswith("dbs/cmip7.db")


class TestResolvePathToAbsolute:
    def test_none_returns_none(self):
        assert resolve_path_to_absolute(None) is None

    def test_absolute_path_unchanged(self, tmp_path):
        p = str(tmp_path / "foo")
        assert resolve_path_to_absolute(p) == p

    def test_dot_relative_uses_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = resolve_path_to_absolute("./my_dir")
        assert result == str((tmp_path / "my_dir").resolve())

    def test_plain_relative_uses_esgvoc_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        result = resolve_path_to_absolute("repos/CMIP7-CVs")
        assert result is not None
        assert result.startswith(str(tmp_path))
        assert result.endswith("repos/CMIP7-CVs")

    def test_plain_relative_with_config_name(self, tmp_path, monkeypatch):
        monkeypatch.setenv(ENV_VAR, str(tmp_path))
        result = resolve_path_to_absolute("repos/CMIP7-CVs", config_name="all_dev")
        assert result is not None
        assert "all_dev" in result
