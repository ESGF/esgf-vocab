"""
Tests for esgvoc status command.

The status command reads from UserState (pointer files + filesystem scan).
All tests use an isolated ESGVOC_HOME so they don't touch the real installation.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from esgvoc.cli.status import app as status_app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
    monkeypatch.delenv("ESGVOC_DB_DIR", raising=False)
    yield tmp_path


def _install_fake(tmp_path, project_id="cmip7", version="v2.1.0"):
    from esgvoc.core.service.user_state import UserState
    state = UserState.load()
    db = UserState.db_path(project_id, version)
    db.parent.mkdir(parents=True, exist_ok=True)
    db.write_bytes(b"fake")
    state.set_active(project_id, version)
    state.save()


class TestStatusNoInstalls:
    def test_no_projects_installed(self):
        result = runner.invoke(status_app, [])
        assert result.exit_code == 0
        assert "no projects installed" in result.output.lower()


class TestStatusWithInstalls:
    def test_shows_installed_project(self, tmp_path):
        _install_fake(tmp_path, "cmip7", "v2.1.0")
        result = runner.invoke(status_app, [])
        assert result.exit_code == 0
        assert "cmip7" in result.output
        assert "v2.1.0" in result.output

    def test_shows_active_version(self, tmp_path):
        _install_fake(tmp_path, "cmip7", "v2.0.0")
        _install_fake(tmp_path, "cmip7", "v2.1.0")
        result = runner.invoke(status_app, [])
        assert result.exit_code == 0
        assert "v2.1.0" in result.output

    def test_shows_source(self, tmp_path):
        _install_fake(tmp_path, "cmip7", "v2.1.0")
        result = runner.invoke(status_app, [])
        assert result.exit_code == 0
        # source column should appear (registry or local)
        assert "registry" in result.output

    def test_multiple_projects(self, tmp_path):
        _install_fake(tmp_path, "cmip7", "v2.1.0")
        _install_fake(tmp_path, "cmip6", "v6.5.0")
        result = runner.invoke(status_app, [])
        assert result.exit_code == 0
        assert "cmip7" in result.output
        assert "cmip6" in result.output

    def test_paths_flag_shows_db_path(self, tmp_path):
        _install_fake(tmp_path, "cmip7", "v2.1.0")
        result = runner.invoke(status_app, ["--paths"])
        assert result.exit_code == 0
        assert "cmip7" in result.output
        # Rich may truncate long paths; check for the existence marker instead
        assert "✓" in result.output or "dbs" in result.output
