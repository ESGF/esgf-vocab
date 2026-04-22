"""Tests for `esgvoc status` command."""
import pytest
from esgvoc.cli.status import app as status_app
from esgvoc.core.service.user_state import UserState
from tests.user_fetch_db.conftest import make_db
from .conftest import runner


class TestStatusCommand:
    def test_status_no_projects(self):
        result = runner.invoke(status_app, [])
        assert result.exit_code == 0
        assert "No projects" in result.output

    def test_status_shows_installed_project(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        make_db(UserState.db_path("universe", "v1.0.0"), "universe", "1.0.0")
        state = UserState.load()
        state.set_active("universe", "v1.0.0", source="registry")

        result = runner.invoke(status_app, [])
        assert result.exit_code == 0
        assert "universe" in result.output
        assert "v1.0.0" in result.output

    def test_status_shows_active_version(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        for ver in ["v1.0.0", "v2.0.0"]:
            make_db(UserState.db_path("cmip7", ver))
        state = UserState.load()
        state.set_active("cmip7", "v2.0.0")

        result = runner.invoke(status_app, [])
        assert "v2.0.0" in result.output

    def test_status_paths_flag(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        make_db(UserState.db_path("universe", "v1.0.0"))
        state = UserState.load()
        state.set_active("universe", "v1.0.0")

        result = runner.invoke(status_app, ["--paths"])
        assert result.exit_code == 0
        # Rich may truncate the path but the DB path column header should be present
        assert "DB path" in result.output
