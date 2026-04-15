"""
Tests for the enhanced esgvoc status command.

Dev Tier output relies on service.current_state which requires a real install,
so we mock it. User Tier output is driven by UserState which we control via
the ESGVOC_HOME fixture.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from esgvoc.cli.status import app as status_app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
    yield tmp_path


def _fake_service_state():
    """Return a SimpleNamespace that mimics service.current_state."""
    universe = SimpleNamespace(
        github_repo="https://github.com/WCRP-CMIP/WCRP-universe",
        local_path="/fake/universe",
        db_path="/fake/universe.db",
        github_version="v1.0.0",
        local_version="v1.0.0",
        db_version="v1.0.0",
        offline_mode=False,
    )
    project = SimpleNamespace(
        github_repo="https://github.com/WCRP-CMIP/CMIP7_CVs",
        local_path="/fake/cmip7",
        db_path="/fake/cmip7.db",
        github_version="v2.1.0",
        local_version="v2.1.0",
        db_version="v2.1.0",
        offline_mode=False,
    )
    return SimpleNamespace(
        universe=universe,
        projects={"cmip7": project},
        get_state_summary=lambda: None,
    )


def _install_fake(tmp_path, project_id="cmip7", version="v2.1.0"):
    from esgvoc.core.service.user_state import UserState
    state = UserState.load()
    db = UserState.db_path(project_id, version)
    db.parent.mkdir(parents=True, exist_ok=True)
    db.write_bytes(b"fake")
    state.add_installed(project_id, version)
    state.set_active(project_id, version)
    state.save()


class TestStatusUserTier:
    def test_no_user_tier_installed(self):
        with patch("esgvoc.cli.status.service") as mock_svc:
            mock_svc.current_state = _fake_service_state()
            result = runner.invoke(status_app, [])
        assert result.exit_code == 0
        assert "no projects installed" in result.output.lower()

    def test_user_tier_shows_installed(self, tmp_path):
        _install_fake(tmp_path, "cmip7", "v2.1.0")
        with patch("esgvoc.cli.status.service") as mock_svc:
            mock_svc.current_state = _fake_service_state()
            result = runner.invoke(status_app, [])
        assert result.exit_code == 0
        assert "cmip7" in result.output
        assert "v2.1.0" in result.output
        assert "User Tier" in result.output

    def test_user_flag_hides_dev_tier(self, tmp_path):
        _install_fake(tmp_path, "cmip7", "v2.1.0")
        with patch("esgvoc.cli.status.service") as mock_svc:
            mock_svc.current_state = _fake_service_state()
            result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0
        assert "User Tier" in result.output
        assert "Dev Tier" not in result.output

    def test_dev_flag_hides_user_tier(self):
        with patch("esgvoc.cli.status.service") as mock_svc:
            mock_svc.current_state = _fake_service_state()
            result = runner.invoke(status_app, ["--dev"])
        assert result.exit_code == 0
        assert "Dev Tier" in result.output
        assert "User Tier" not in result.output


class TestStatusDevTier:
    def test_dev_tier_shows_projects(self):
        with patch("esgvoc.cli.status.service") as mock_svc:
            mock_svc.current_state = _fake_service_state()
            result = runner.invoke(status_app, ["--dev"])
        assert result.exit_code == 0
        assert "cmip7" in result.output
        assert "v2.1.0" in result.output

    def test_paths_flag_shows_full_path(self):
        with patch("esgvoc.cli.status.service") as mock_svc:
            mock_svc.current_state = _fake_service_state()
            result = runner.invoke(status_app, ["--dev", "--paths"])
        assert result.exit_code == 0
        assert "/fake/universe" in result.output
        assert "/fake/cmip7.db" in result.output

    def test_offline_warning_shown(self):
        state = _fake_service_state()
        state.universe.offline_mode = True

        with patch("esgvoc.cli.status.service") as mock_svc:
            mock_svc.current_state = state
            result = runner.invoke(status_app, ["--dev"])
        assert result.exit_code == 0
        assert "offline" in result.output.lower()
