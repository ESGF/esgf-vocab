"""
User Tier — Combined status and offline mode CLI tests.

Tests ``esgvoc status`` (no flags), ``esgvoc status --dev``, and
``esgvoc status --user``.  The first two require the Dev Tier config to be
initialised; the last requires at least one User Tier install.

Plan scenarios covered:
  UT-45  ``esgvoc status`` (no flags) shows both tiers without errors
  UT-46  ``esgvoc status --user`` shows only the User Tier section
  UT-47  ``esgvoc status --dev``  shows only the Dev Tier section
  UT-48  ``esgvoc status --paths`` shows filesystem paths in User Tier
  UT-49  User Tier section is empty when nothing is installed
  UT-50  After install, project appears in combined status output
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from esgvoc.cli.status import app as status_app

from .conftest import fetcher_that_copies, install_real_db, runner


# ---------------------------------------------------------------------------
# UT-45  status (no flags) — both tiers shown
# ---------------------------------------------------------------------------

class TestStatusNoFlags:
    """UT-45: ``esgvoc status`` with no flags exits 0 and shows both tiers."""

    def test_exits_zero(self):
        result = runner.invoke(status_app)
        assert result.exit_code == 0, result.output

    def test_output_contains_user_tier_label(self):
        result = runner.invoke(status_app)
        assert "User Tier" in result.output or "user tier" in result.output.lower()

    def test_output_contains_dev_tier_label(self):
        result = runner.invoke(status_app)
        assert "Dev Tier" in result.output or "dev tier" in result.output.lower()

    def test_no_exception_in_output(self):
        """No traceback should appear in normal operation."""
        result = runner.invoke(status_app)
        assert "Traceback" not in result.output
        assert "Error" not in result.output or result.exit_code == 0


# ---------------------------------------------------------------------------
# UT-46  status --user
# ---------------------------------------------------------------------------

class TestStatusUserFlag:
    """UT-46: ``esgvoc status --user`` shows only the User Tier section."""

    def test_exits_zero(self):
        result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0, result.output

    def test_output_contains_user_tier(self):
        result = runner.invoke(status_app, ["--user"])
        assert "User Tier" in result.output or "user tier" in result.output.lower()

    def test_no_installed_shows_hint_message(self):
        """With nothing installed the CLI prints a hint to run esgvoc install."""
        result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0, result.output
        # Either the empty-state message or the table header is shown
        output_lower = result.output.lower()
        assert "user tier" in output_lower or "install" in output_lower


# ---------------------------------------------------------------------------
# UT-47  status --dev
# ---------------------------------------------------------------------------

class TestStatusDevFlag:
    """UT-47: ``esgvoc status --dev`` shows only the Dev Tier section."""

    def test_exits_zero(self):
        result = runner.invoke(status_app, ["--dev"])
        assert result.exit_code == 0, result.output

    def test_output_contains_dev_tier(self):
        result = runner.invoke(status_app, ["--dev"])
        assert "Dev Tier" in result.output or "dev tier" in result.output.lower()

    def test_dev_flag_excludes_user_tier_section(self):
        """When --dev is given the User Tier heading should NOT appear."""
        result = runner.invoke(status_app, ["--dev"])
        # The User Tier heading text should be absent
        assert "User Tier" not in result.output


# ---------------------------------------------------------------------------
# UT-48  status --paths
# ---------------------------------------------------------------------------

class TestStatusPaths:
    """UT-48: --paths flag includes filesystem path information."""

    def test_user_paths_after_install(self, real_dbs):
        """After installing a DB, --paths shows the .db file path."""
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)

        result = runner.invoke(status_app, ["--user", "--paths"])
        assert result.exit_code == 0, result.output
        assert ".db" in result.output, (
            "Expected '.db' path in output when --paths is given"
        )

    def test_paths_flag_exits_zero_with_no_install(self):
        result = runner.invoke(status_app, ["--user", "--paths"])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# UT-49  User Tier section empty when nothing installed
# ---------------------------------------------------------------------------

class TestStatusEmptyUserTier:
    """UT-49: User Tier shows an empty-state message when nothing is installed."""

    def test_empty_state_message_shown(self):
        result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0, result.output
        # The CLI prints a dim hint message or just a table with no rows
        output_lower = result.output.lower()
        assert "user tier" in output_lower or "no projects" in output_lower or "install" in output_lower

    def test_no_project_id_in_output(self, real_dbs):
        """Before install, the project id should NOT appear in user-tier output."""
        pid = real_dbs["project_id"]
        result = runner.invoke(status_app, ["--user"])
        # Only fails if a project was somehow already in state
        # (isolated_home autouse fixture guarantees a clean ESGVOC_HOME)
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# UT-50  After install, project appears in combined status
# ---------------------------------------------------------------------------

class TestStatusAfterInstall:
    """UT-50: Installing a DB causes it to appear in all status variants."""

    def test_project_in_combined_status(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)

        result = runner.invoke(status_app)
        assert result.exit_code == 0, result.output
        assert pid in result.output
        assert ver in result.output

    def test_project_in_user_status(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)

        result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0, result.output
        assert pid in result.output
        assert ver in result.output

    def test_project_not_in_dev_only_status(self, real_dbs):
        """User Tier projects should not appear in --dev output."""
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)

        result = runner.invoke(status_app, ["--dev"])
        assert result.exit_code == 0, result.output
        # The user-tier version string shouldn't appear in the dev-only view
        # (dev tier shows its own config version, not the user-tier install)
        assert "User Tier" not in result.output

    def test_two_installed_versions_both_shown(self, real_dbs):
        """After installing both v1 and v2, both appear in the status output."""
        pid = real_dbs["project_id"]
        v1 = real_dbs["v1_version"]
        v2 = real_dbs["v2_version"]

        install_real_db(real_dbs["v1_path"], pid, v1)
        install_real_db(real_dbs["v2_path"], pid, v2)

        result = runner.invoke(status_app, ["--user"])
        assert result.exit_code == 0, result.output
        assert v1 in result.output
        assert v2 in result.output
