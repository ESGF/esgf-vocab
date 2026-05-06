"""Tests for `esgvoc list` command."""
from unittest.mock import MagicMock, patch

from esgvoc.cli.versions import app as list_app
from esgvoc.core.service.user_state import UserState
from tests.user_fetch_db.conftest import make_db

from .conftest import runner


class TestListCommand:
    def test_list_no_projects(self):
        result = runner.invoke(list_app, ["list"])
        assert result.exit_code == 0
        assert "No projects installed" in result.output

    def test_list_shows_installed_version(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        make_db(UserState.db_path("universe", "v1.0.0"))
        state = UserState.load()
        state.set_active("universe", "v1.0.0")

        result = runner.invoke(list_app, ["list", "universe"])
        assert result.exit_code == 0
        assert "v1.0.0" in result.output

    def test_list_marks_active_version(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        for ver in ["v1.0.0", "v2.0.0"]:
            make_db(UserState.db_path("cmip7", ver))
        state = UserState.load()
        state.set_active("cmip7", "v2.0.0")

        result = runner.invoke(list_app, ["list", "cmip7"])
        assert result.exit_code == 0
        assert "active" in result.output.lower()

    def test_list_available_shows_remote_versions(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        make_db(UserState.db_path("universe", "v1.0.0"))
        state = UserState.load()
        state.set_active("universe", "v1.0.0")

        mock_fetcher = MagicMock()
        mock_fetcher.list_versions.return_value = ["v2.0.0", "v1.0.0"]

        with patch("esgvoc.core.db_fetcher.DBFetcher", return_value=mock_fetcher):
            result = runner.invoke(list_app, ["list", "universe", "--available"])

        assert result.exit_code == 0
        assert "v2.0.0" in result.output

    def test_list_all_projects_when_no_arg(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        for pid in ["universe", "cmip7"]:
            make_db(UserState.db_path(pid, "v1.0.0"), pid)
            UserState.load().set_active(pid, "v1.0.0")

        result = runner.invoke(list_app, ["list"])
        assert result.exit_code == 0
        assert "universe" in result.output
        assert "cmip7" in result.output
