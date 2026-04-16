"""
Dev Tier — Offline mode CLI integration tests.

Tests the ``esgvoc offline`` subcommands against the dev-tier config system.
Each test uses the ``default_config_test`` fixture so that config modifications
are isolated and the config is restored after every test.

Plan scenarios covered:
  DT-61  ``esgvoc offline show`` exits 0 and lists components with their status
  DT-62  ``esgvoc offline enable universe`` enables offline mode for universe
  DT-63  ``esgvoc offline disable universe`` disables offline mode for universe
  DT-64  ``esgvoc offline enable`` (no arg) enables all components
  DT-65  ``esgvoc offline disable`` (no arg) disables all components
  DT-66  ``esgvoc offline enable_all`` enables all components
  DT-67  ``esgvoc offline disable_all`` disables all components
  DT-68  ``esgvoc offline show nonexistent`` exits non-zero with an error
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from esgvoc.cli.offline import app as offline_app

runner = CliRunner()


# ---------------------------------------------------------------------------
# DT-61  offline show — lists all components
# ---------------------------------------------------------------------------

class TestOfflineShow:
    """DT-61: ``esgvoc offline show`` exits 0 and displays component status."""

    def test_exits_zero(self, default_config_test):
        result = runner.invoke(offline_app, ["show"])
        assert result.exit_code == 0, result.output

    def test_output_mentions_universe(self, default_config_test):
        result = runner.invoke(offline_app, ["show"])
        assert "Universe" in result.output or "universe" in result.output.lower()

    def test_output_contains_offline_status(self, default_config_test):
        """Output should contain some indicator of enabled/disabled status."""
        result = runner.invoke(offline_app, ["show"])
        output_lower = result.output.lower()
        assert "enabled" in output_lower or "disabled" in output_lower or "offline" in output_lower

    def test_show_universe_component_exits_zero(self, default_config_test):
        result = runner.invoke(offline_app, ["show", "universe"])
        assert result.exit_code == 0, result.output

    def test_show_universe_mentions_mode(self, default_config_test):
        result = runner.invoke(offline_app, ["show", "universe"])
        output_lower = result.output.lower()
        assert "online" in output_lower or "offline" in output_lower


# ---------------------------------------------------------------------------
# DT-62  offline enable universe
# ---------------------------------------------------------------------------

class TestOfflineEnableUniverse:
    """DT-62: ``esgvoc offline enable universe`` enables offline for universe."""

    def test_enable_universe_exits_zero(self, default_config_test):
        result = runner.invoke(offline_app, ["enable", "universe"])
        assert result.exit_code == 0, result.output

    def test_enable_universe_confirms_in_output(self, default_config_test):
        result = runner.invoke(offline_app, ["enable", "universe"])
        output_lower = result.output.lower()
        assert "enabled" in output_lower or "offline" in output_lower

    def test_enable_universe_persists_in_show(self, default_config_test):
        """After enabling, ``show universe`` should reflect enabled state."""
        runner.invoke(offline_app, ["enable", "universe"])
        result = runner.invoke(offline_app, ["show", "universe"])
        assert result.exit_code == 0, result.output
        assert "offline" in result.output.lower()

    def test_enable_universe_reflected_in_config(self, default_config_test):
        """After enabling, the config object itself should have offline_mode=True."""
        runner.invoke(offline_app, ["enable", "universe"])
        from esgvoc.core import service
        settings = service.config_manager.get_active_config()
        assert settings.universe.offline_mode is True


# ---------------------------------------------------------------------------
# DT-63  offline disable universe
# ---------------------------------------------------------------------------

class TestOfflineDisableUniverse:
    """DT-63: ``esgvoc offline disable universe`` disables offline for universe."""

    def test_disable_universe_exits_zero(self, default_config_test):
        # First enable so we have something to disable
        runner.invoke(offline_app, ["enable", "universe"])
        result = runner.invoke(offline_app, ["disable", "universe"])
        assert result.exit_code == 0, result.output

    def test_disable_universe_reflects_in_config(self, default_config_test):
        runner.invoke(offline_app, ["enable", "universe"])
        runner.invoke(offline_app, ["disable", "universe"])
        from esgvoc.core import service
        settings = service.config_manager.get_active_config()
        assert settings.universe.offline_mode is False

    def test_disable_universe_output_mentions_online(self, default_config_test):
        runner.invoke(offline_app, ["enable", "universe"])
        result = runner.invoke(offline_app, ["disable", "universe"])
        output_lower = result.output.lower()
        assert "disabled" in output_lower or "online" in output_lower


# ---------------------------------------------------------------------------
# DT-64  offline enable (no arg) — all components
# ---------------------------------------------------------------------------

class TestOfflineEnableAll:
    """DT-64: ``esgvoc offline enable`` with no argument enables all components."""

    def test_enable_all_no_arg_exits_zero(self, default_config_test):
        result = runner.invoke(offline_app, ["enable"])
        assert result.exit_code == 0, result.output

    def test_enable_all_enables_universe(self, default_config_test):
        runner.invoke(offline_app, ["enable"])
        from esgvoc.core import service
        settings = service.config_manager.get_active_config()
        assert settings.universe.offline_mode is True

    def test_enable_all_enables_all_projects(self, default_config_test):
        runner.invoke(offline_app, ["enable"])
        from esgvoc.core import service
        settings = service.config_manager.get_active_config()
        for name, proj in settings.projects.items():
            assert proj.offline_mode is True, (
                f"Project '{name}' should have offline_mode=True after enable all"
            )


# ---------------------------------------------------------------------------
# DT-65  offline disable (no arg) — all components
# ---------------------------------------------------------------------------

class TestOfflineDisableAll:
    """DT-65: ``esgvoc offline disable`` with no argument disables all components."""

    def test_disable_all_no_arg_exits_zero(self, default_config_test):
        runner.invoke(offline_app, ["enable"])   # enable first
        result = runner.invoke(offline_app, ["disable"])
        assert result.exit_code == 0, result.output

    def test_disable_all_disables_universe(self, default_config_test):
        runner.invoke(offline_app, ["enable"])
        runner.invoke(offline_app, ["disable"])
        from esgvoc.core import service
        settings = service.config_manager.get_active_config()
        assert settings.universe.offline_mode is False

    def test_disable_all_disables_all_projects(self, default_config_test):
        runner.invoke(offline_app, ["enable"])
        runner.invoke(offline_app, ["disable"])
        from esgvoc.core import service
        settings = service.config_manager.get_active_config()
        for name, proj in settings.projects.items():
            assert proj.offline_mode is False, (
                f"Project '{name}' should have offline_mode=False after disable all"
            )


# ---------------------------------------------------------------------------
# DT-66  offline enable_all command
# ---------------------------------------------------------------------------

class TestOfflineEnableAllCommand:
    """DT-66: ``esgvoc offline enable_all`` enables offline for all components."""

    def test_enable_all_command_exits_zero(self, default_config_test):
        result = runner.invoke(offline_app, ["enable-all"])
        assert result.exit_code == 0, result.output

    def test_enable_all_command_enables_universe(self, default_config_test):
        runner.invoke(offline_app, ["enable-all"])
        from esgvoc.core import service
        settings = service.config_manager.get_active_config()
        assert settings.universe.offline_mode is True

    def test_enable_all_command_output_confirms(self, default_config_test):
        result = runner.invoke(offline_app, ["enable-all"])
        output_lower = result.output.lower()
        assert "enabled" in output_lower or "all" in output_lower


# ---------------------------------------------------------------------------
# DT-67  offline disable_all command
# ---------------------------------------------------------------------------

class TestOfflineDisableAllCommand:
    """DT-67: ``esgvoc offline disable_all`` disables offline for all components."""

    def test_disable_all_command_exits_zero(self, default_config_test):
        runner.invoke(offline_app, ["enable-all"])
        result = runner.invoke(offline_app, ["disable-all"])
        assert result.exit_code == 0, result.output

    def test_disable_all_command_disables_universe(self, default_config_test):
        runner.invoke(offline_app, ["enable-all"])
        runner.invoke(offline_app, ["disable-all"])
        from esgvoc.core import service
        settings = service.config_manager.get_active_config()
        assert settings.universe.offline_mode is False

    def test_disable_all_command_output_confirms(self, default_config_test):
        runner.invoke(offline_app, ["enable-all"])
        result = runner.invoke(offline_app, ["disable-all"])
        output_lower = result.output.lower()
        assert "disabled" in output_lower or "all" in output_lower


# ---------------------------------------------------------------------------
# DT-68  offline show <nonexistent> exits non-zero
# ---------------------------------------------------------------------------

class TestOfflineShowErrors:
    """DT-68: ``esgvoc offline show <nonexistent>`` exits non-zero."""

    def test_show_unknown_component_exits_nonzero(self, default_config_test):
        result = runner.invoke(offline_app, ["show", "nonexistent-component-xyz"])
        assert result.exit_code != 0

    def test_show_unknown_component_output_mentions_not_found(self, default_config_test):
        result = runner.invoke(offline_app, ["show", "nonexistent-component-xyz"])
        output_lower = result.output.lower()
        assert "not found" in output_lower or "nonexistent" in output_lower or "error" in output_lower
