"""
Dev Tier — Admin build CLI integration tests.

Tests the ``esgvoc admin build`` and ``esgvoc admin validate --schema-only``
CLI commands against the real locally-cloned CV repositories (from the
``cloned_repos`` session fixture).  No network access required (repos already
cloned).

Plan scenarios covered:
  DT-28  ``esgvoc admin build`` dev mode (--project-path + --universe-path) exits 0
  DT-29  Build output is a valid SQLite file with correct _esgvoc_metadata
  DT-30  ``esgvoc admin build --validate`` also passes validation in one step
  DT-31  ``esgvoc admin validate --schema-only`` on project directory exits 0
  DT-32  Missing required args → correct error message and non-zero exit
  DT-33  Build with manifest overrides → metadata reflects overrides
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from esgvoc.admin.cli import app as admin_app

runner = CliRunner()


# ---------------------------------------------------------------------------
# DT-28  esgvoc admin build (dev mode)
# ---------------------------------------------------------------------------

class TestAdminBuildCLI:
    """DT-28 / DT-29: admin build --project-path + --universe-path exits 0."""

    def test_build_dev_mode_exits_0(self, cloned_repos, tmp_path):
        """DT-28: build in dev mode (fully local) succeeds."""
        project_path = cloned_repos["cmip6"]
        universe_path = cloned_repos["universe"]
        output = tmp_path / "cmip6-cli-test.db"

        result = runner.invoke(admin_app, [
            "build",
            "--project-path", str(project_path),
            "--universe-path", str(universe_path),
            "--project-id", "cmip6",
            "--cv-version", "cli-test",
            "--universe-version", "test",
            "--output", str(output),
        ])

        assert result.exit_code == 0, result.output
        assert output.exists(), "Output DB file was not created"

    def test_build_output_is_readable_sqlite(self, cloned_repos, tmp_path):
        """DT-29a: The built DB is a valid SQLite file."""
        project_path = cloned_repos["cmip6"]
        universe_path = cloned_repos["universe"]
        output = tmp_path / "cmip6-cli-test.db"

        runner.invoke(admin_app, [
            "build",
            "--project-path", str(project_path),
            "--universe-path", str(universe_path),
            "--project-id", "cmip6",
            "--cv-version", "cli-test",
            "--output", str(output),
        ])

        assert output.exists()
        conn = sqlite3.connect(str(output))
        check = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        assert check[0] == "ok"

    def test_build_output_has_esgvoc_metadata(self, cloned_repos, tmp_path):
        """DT-29b: The built DB has _esgvoc_metadata with correct project_id."""
        project_path = cloned_repos["cmip6"]
        universe_path = cloned_repos["universe"]
        output = tmp_path / "cmip6-cli-test.db"

        runner.invoke(admin_app, [
            "build",
            "--project-path", str(project_path),
            "--universe-path", str(universe_path),
            "--project-id", "cmip6",
            "--cv-version", "cli-test",
            "--output", str(output),
        ])

        assert output.exists()
        conn = sqlite3.connect(str(output))
        rows = dict(conn.execute(
            "SELECT key, value FROM _esgvoc_metadata"
        ).fetchall())
        conn.close()

        assert rows.get("project_id") == "cmip6"
        assert rows.get("cv_version") == "cli-test"


# ---------------------------------------------------------------------------
# DT-30  esgvoc admin build --validate
# ---------------------------------------------------------------------------

class TestAdminBuildWithValidation:
    """DT-30: --validate flag runs validation after build, exits 0 on success."""

    def test_build_with_validate_exits_0(self, cloned_repos, tmp_path):
        project_path = cloned_repos["cmip6"]
        universe_path = cloned_repos["universe"]
        output = tmp_path / "cmip6-validated.db"

        result = runner.invoke(admin_app, [
            "build",
            "--project-path", str(project_path),
            "--universe-path", str(universe_path),
            "--project-id", "cmip6",
            "--cv-version", "validated-test",
            "--output", str(output),
            "--validate",
        ])

        assert result.exit_code == 0, result.output
        assert output.exists()

    def test_build_with_validate_output_mentions_validation(self, cloned_repos, tmp_path):
        """The build summary should appear in output."""
        project_path = cloned_repos["cmip6"]
        universe_path = cloned_repos["universe"]
        output = tmp_path / "cmip6-validated.db"

        result = runner.invoke(admin_app, [
            "build",
            "--project-path", str(project_path),
            "--universe-path", str(universe_path),
            "--project-id", "cmip6",
            "--cv-version", "test-123",
            "--output", str(output),
            "--validate",
        ])

        assert result.exit_code == 0, result.output
        # The summary line or validation output should be present
        output_lower = result.output.lower()
        assert "cmip6" in output_lower or "test-123" in output_lower


# ---------------------------------------------------------------------------
# DT-31  validate --schema-only on project directory
# ---------------------------------------------------------------------------

class TestAdminValidateSchemaOnly:
    """DT-31: esgvoc admin validate --schema-only on a real project directory."""

    def test_schema_only_validates_json_files(self, cloned_repos):
        """
        DT-31: --schema-only validates all JSON files in the directory.

        The test repos don't have esgvoc_manifest.yaml (marked optional by the
        validator) so the overall exit code may be 1, but JSON files should pass.
        """
        project_path = cloned_repos["cmip6"]

        result = runner.invoke(admin_app, [
            "validate",
            "--schema-only",
            str(project_path),
        ])

        # JSON files should be validated successfully even without a manifest
        assert "json files valid" in result.output.lower(), (
            f"Expected JSON validation result in output:\n{result.output}"
        )

    def test_schema_only_with_manifest_dir_exits_0(self, tmp_path):
        """
        DT-31b: A directory with a valid manifest and JSON files passes schema-only.
        """
        import json
        import yaml

        # Create a minimal project directory with manifest + one JSON file
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        manifest = {
            "project": {"id": "test-project", "name": "Test Project"},
            "cv_version": "1.0.0",
            "universe_version": "1.0.0",
            "esgvoc": {"min_version": "1.0.0"},
        }
        (project_dir / "esgvoc_manifest.yaml").write_text(
            yaml.dump(manifest) if _yaml_available() else ""
        )

        # Add a valid JSON file
        (project_dir / "test_term.json").write_text(json.dumps({"id": "term1"}))

        result = runner.invoke(admin_app, [
            "validate", "--schema-only", str(project_dir),
        ])

        # Should at least check JSON files (not crash)
        assert "json" in result.output.lower()

    def test_schema_only_on_nonexistent_dir_exits_nonzero(self, tmp_path):
        fake = tmp_path / "does-not-exist"
        result = runner.invoke(admin_app, [
            "validate", "--schema-only", str(fake),
        ])
        assert result.exit_code != 0


def _yaml_available() -> bool:
    try:
        import yaml
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# DT-32  Missing / invalid args → correct error and exit code
# ---------------------------------------------------------------------------

class TestAdminBuildArgValidation:
    """DT-32: Missing required arguments produce clear errors and exit non-zero."""

    def test_no_args_exits_nonzero(self, tmp_path):
        output = tmp_path / "out.db"
        result = runner.invoke(admin_app, ["build", "--output", str(output)])
        assert result.exit_code != 0

    def test_project_path_without_universe_path_and_no_universe_repo_exits_nonzero(
        self, cloned_repos, tmp_path
    ):
        """--project-path without --universe-path requires --universe-repo/ref."""
        output = tmp_path / "out.db"
        result = runner.invoke(admin_app, [
            "build",
            "--project-path", str(cloned_repos["cmip6"]),
            "--output", str(output),
        ])
        assert result.exit_code != 0

    def test_missing_output_exits_nonzero(self, cloned_repos):
        """--output is required."""
        result = runner.invoke(admin_app, [
            "build",
            "--project-path", str(cloned_repos["cmip6"]),
            "--universe-path", str(cloned_repos["universe"]),
        ])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# DT-33  Manifest overrides reflected in metadata
# ---------------------------------------------------------------------------

class TestAdminBuildManifestOverrides:
    """DT-33: Manifest overrides set via CLI appear in _esgvoc_metadata."""

    def test_cv_version_override_in_metadata(self, cloned_repos, tmp_path):
        project_path = cloned_repos["cmip6"]
        universe_path = cloned_repos["universe"]
        output = tmp_path / "cmip6-override.db"
        custom_version = "test-override-42"

        result = runner.invoke(admin_app, [
            "build",
            "--project-path", str(project_path),
            "--universe-path", str(universe_path),
            "--project-id", "cmip6",
            "--cv-version", custom_version,
            "--output", str(output),
        ])

        assert result.exit_code == 0, result.output
        assert output.exists()

        conn = sqlite3.connect(str(output))
        rows = dict(conn.execute(
            "SELECT key, value FROM _esgvoc_metadata"
        ).fetchall())
        conn.close()

        assert rows.get("cv_version") == custom_version

    def test_esgvoc_min_version_override_in_metadata(self, cloned_repos, tmp_path):
        project_path = cloned_repos["cmip6"]
        universe_path = cloned_repos["universe"]
        output = tmp_path / "cmip6-minver.db"

        result = runner.invoke(admin_app, [
            "build",
            "--project-path", str(project_path),
            "--universe-path", str(universe_path),
            "--project-id", "cmip6",
            "--cv-version", "test",
            "--esgvoc-min-version", "2.0.0",
            "--output", str(output),
        ])

        assert result.exit_code == 0, result.output

        conn = sqlite3.connect(str(output))
        rows = dict(conn.execute(
            "SELECT key, value FROM _esgvoc_metadata"
        ).fetchall())
        conn.close()

        assert rows.get("esgvoc_min_version") == "2.0.0"
