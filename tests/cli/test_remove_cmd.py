"""Tests for `esgvoc remove` command."""

from esgvoc.cli.remove import app as remove_app
from esgvoc.core.service.user_state import UserState
from tests.user_fetch_db.conftest import make_db

from .conftest import runner


class TestRemoveCommand:
    def test_remove_not_installed_exits_0(self):
        result = runner.invoke(remove_app, ["universe", "--yes"])
        assert result.exit_code == 0
        assert "No versions installed" in result.output

    def test_remove_specific_version(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        db = UserState.db_path("universe", "v1.0.0")
        make_db(db)
        state = UserState.load()
        state.set_active("universe", "v1.0.0")

        result = runner.invoke(remove_app, ["universe@v1.0.0", "--yes"])
        assert result.exit_code == 0, result.output
        assert not db.exists()

    def test_remove_all_versions(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        for ver in ["v1.0.0", "v2.0.0"]:
            make_db(UserState.db_path("universe", ver))
        state = UserState.load()
        state.set_active("universe", "v2.0.0")

        result = runner.invoke(remove_app, ["universe", "--all", "--yes"])
        assert result.exit_code == 0, result.output
        assert UserState.load().get_installed("universe") == []

    def test_remove_active_version_clears_pointer(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        make_db(UserState.db_path("cmip7", "v1.0.0"))
        state = UserState.load()
        state.set_active("cmip7", "v1.0.0")

        runner.invoke(remove_app, ["cmip7@v1.0.0", "--yes"])
        assert UserState.load().get_active("cmip7") is None

    def test_remove_nonexistent_version_exits_1(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        make_db(UserState.db_path("universe", "v1.0.0"))

        result = runner.invoke(remove_app, ["universe@v99.0.0", "--yes"])
        assert result.exit_code == 1

    def test_remove_output_mentions_project(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
        make_db(UserState.db_path("universe", "v1.0.0"))

        result = runner.invoke(remove_app, ["universe@v1.0.0", "--yes"])
        assert "universe" in result.output
