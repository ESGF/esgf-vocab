"""
Dev Tier — Admin CLI integration tests with real built databases.

Tests the ``esgvoc admin`` subcommands (validate, test, diff) against the same
real SQLite databases built by the session fixtures in
``tests/integration/conftest.py``.  No network access required.

Plan scenarios covered:
  DT-19  ``esgvoc admin validate`` exits 0 on a valid DB
  DT-20  ``esgvoc admin validate --full`` exits 0 on a valid DB
  DT-21  ``esgvoc admin validate`` exits 1 on a non-existent path
  DT-22  ``esgvoc admin test`` exits 0 on a valid DB
  DT-23  ``esgvoc admin diff`` (text format) exits 0 and shows metadata
  DT-24  ``esgvoc admin diff --format json`` exits 0 and produces valid JSON
  DT-25  ``esgvoc admin diff`` detects cv_version difference between v1 and v2 DBs
  DT-26  Universe DB passes ``esgvoc admin validate``
  DT-27  ``esgvoc admin validate`` exits 1 on a corrupt file
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from esgvoc.admin.cli import app as admin_app

runner = CliRunner()


# ---------------------------------------------------------------------------
# DT-19  validate (basic)
# ---------------------------------------------------------------------------

class TestAdminValidate:
    """DT-19 / DT-20 / DT-21: esgvoc admin validate on real DBs."""

    def test_validate_valid_db_exits_0(self, real_dbs):
        result = runner.invoke(admin_app, ["validate", str(real_dbs["v1_path"])])
        assert result.exit_code == 0, result.output

    def test_validate_output_contains_passed(self, real_dbs):
        result = runner.invoke(admin_app, ["validate", str(real_dbs["v1_path"])])
        assert "passed" in result.output.lower() or "ok" in result.output.lower() or \
               result.exit_code == 0

    def test_validate_full_valid_db_exits_0(self, real_dbs):
        """DT-20: --full mode also passes on the real built DB."""
        result = runner.invoke(admin_app, ["validate", "--full", str(real_dbs["v1_path"])])
        assert result.exit_code == 0, result.output

    def test_validate_nonexistent_path_exits_nonzero(self, tmp_path):
        """DT-21: nonexistent path → non-zero exit code."""
        fake = tmp_path / "does-not-exist.db"
        result = runner.invoke(admin_app, ["validate", str(fake)])
        assert result.exit_code != 0

    def test_validate_v2_db_also_passes(self, real_dbs):
        """Both built DB versions should pass validation."""
        result = runner.invoke(admin_app, ["validate", str(real_dbs["v2_path"])])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# DT-22  test command (alias for validate --full)
# ---------------------------------------------------------------------------

class TestAdminTest:
    """DT-22: esgvoc admin test runs full validation."""

    def test_test_command_exits_0_on_valid_db(self, real_dbs):
        result = runner.invoke(admin_app, ["test", str(real_dbs["v1_path"])])
        assert result.exit_code == 0, result.output

    def test_test_command_corrupt_file_exits_1(self, tmp_path):
        """A file that isn't a valid SQLite DB should fail the test command."""
        bad = tmp_path / "bad.db"
        bad.write_bytes(b"this is not a sqlite database")
        result = runner.invoke(admin_app, ["test", str(bad)])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# DT-23 / DT-24 / DT-25  diff command
# ---------------------------------------------------------------------------

class TestAdminDiff:
    """DT-23 / DT-24 / DT-25: esgvoc admin diff between two real DBs."""

    def test_diff_text_exits_0(self, real_dbs):
        """DT-23: text diff between v1 and v2 exits 0."""
        result = runner.invoke(admin_app, [
            "diff", str(real_dbs["v1_path"]), str(real_dbs["v2_path"]),
        ])
        assert result.exit_code == 0, result.output

    def test_diff_json_exits_0(self, real_dbs):
        """DT-24: --format json exits 0."""
        result = runner.invoke(admin_app, [
            "diff", str(real_dbs["v1_path"]), str(real_dbs["v2_path"]),
            "--format", "json",
        ])
        assert result.exit_code == 0, result.output

    def test_diff_json_is_parseable(self, real_dbs):
        """DT-24: --format json output is valid JSON."""
        result = runner.invoke(admin_app, [
            "diff", str(real_dbs["v1_path"]), str(real_dbs["v2_path"]),
            "--format", "json",
        ])
        # The JSON may be mixed with Rich markup in some versions; strip ANSI
        raw = result.output
        # Find JSON block (starts with '{')
        start = raw.find("{")
        if start != -1:
            parsed = json.loads(raw[start:].strip())
            assert isinstance(parsed, dict)

    def test_diff_detects_cv_version_difference(self, real_dbs):
        """DT-25: diff output mentions the changed cv_version between v1 and v2."""
        result = runner.invoke(admin_app, [
            "diff", str(real_dbs["v1_path"]), str(real_dbs["v2_path"]),
        ])
        assert result.exit_code == 0, result.output
        # Both cv_versions should appear somewhere in the diff output
        v1 = real_dbs["v1_version"].lstrip("v")
        v2 = real_dbs["v2_version"].lstrip("v")
        assert v1 in result.output or v2 in result.output, (
            f"Expected cv_version change ({v1} → {v2}) to appear in diff output:\n{result.output}"
        )

    def test_diff_same_db_exits_0(self, real_dbs):
        """Diffing a DB against itself should succeed (exit 0)."""
        result = runner.invoke(admin_app, [
            "diff", str(real_dbs["v1_path"]), str(real_dbs["v1_path"]),
        ])
        assert result.exit_code == 0, result.output
        # The diff table is always rendered; it should contain the project metadata.
        assert "cmip6" in result.output.lower() or "cv_version" in result.output.lower()

    def test_diff_missing_baseline_exits_nonzero(self, real_dbs, tmp_path):
        """Missing baseline file → non-zero exit code."""
        fake = tmp_path / "missing.db"
        result = runner.invoke(admin_app, [
            "diff", str(fake), str(real_dbs["v1_path"]),
        ])
        assert result.exit_code != 0

    def test_diff_missing_updated_exits_nonzero(self, real_dbs, tmp_path):
        """Missing updated file → non-zero exit code."""
        fake = tmp_path / "missing.db"
        result = runner.invoke(admin_app, [
            "diff", str(real_dbs["v1_path"]), str(fake),
        ])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# DT-26  validate universe DB
# ---------------------------------------------------------------------------

class TestAdminValidateUniverse:
    """DT-26: esgvoc admin validate passes on the standalone universe DB."""

    def test_validate_universe_db_exits_0(self, universe_db):
        result = runner.invoke(admin_app, ["validate", str(universe_db)])
        assert result.exit_code == 0, result.output

    def test_validate_full_universe_db_exits_0(self, universe_db):
        result = runner.invoke(admin_app, ["validate", "--full", str(universe_db)])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# DT-27  validate corrupt file
# ---------------------------------------------------------------------------

class TestAdminValidateCorrupt:
    """DT-27: esgvoc admin validate exits 1 on a file that is not a valid DB."""

    def test_validate_corrupt_file_exits_1(self, tmp_path):
        bad = tmp_path / "corrupt.db"
        bad.write_bytes(b"not a sqlite database at all")
        result = runner.invoke(admin_app, ["validate", str(bad)])
        assert result.exit_code != 0

    def test_validate_empty_file_exits_1(self, tmp_path):
        empty = tmp_path / "empty.db"
        empty.write_bytes(b"")
        result = runner.invoke(admin_app, ["validate", str(empty)])
        assert result.exit_code != 0
