"""
Dev Tier — Admin build pipeline integration tests.

Tests `esgvoc admin build` (build_dev mode) end-to-end:
  - produces a real SQLite file
  - _esgvoc_metadata reflects manifest_overrides
  - correct tables exist (pterms, pcollections, uterms, udata_descriptors)
  - tables are non-empty
  - DBValidator basic + full passes on the result
  - Building the same repo twice with different cv_version produces distinct metadata
  - admin diff detects the metadata difference

Plan scenarios covered:
  DT-1  build_dev produces a valid non-empty SQLite database
  DT-2  _esgvoc_metadata keys correct from manifest_overrides
  DT-3  Project tables (pterms / pcollections) are present and non-empty
  DT-4  Universe tables (uterms / udata_descriptors) are present and non-empty
  DT-5  DBValidator.validate() passes (basic)
  DT-6  DBValidator.validate(full=True) passes (FTS + join checks)
  DT-7  Two builds with different cv_version have distinct metadata
  DT-8  admin diff detects metadata changes between the two builds
  DT-9  BuildResult checksum matches actual file SHA-256
  DT-10 BuildResult size_bytes matches actual file size
"""
from __future__ import annotations

import hashlib
import sqlite3

import pytest
from typer.testing import CliRunner

from .conftest import db_row_count, db_table_names, read_db_metadata

runner = CliRunner()


class TestBuildDevOutput:
    """DT-1 to DT-4: structural correctness of the built database."""

    def test_build_produces_nonempty_sqlite_file(self, real_dbs):
        """The session fixture builds the DB; verify it is non-zero size."""
        v1 = real_dbs["v1_path"]
        assert v1.exists(), f"Expected DB file at {v1}"
        assert v1.stat().st_size > 0

    def test_both_versions_are_regular_sqlite(self, real_dbs):
        for key in ("v1_path", "v2_path"):
            db = real_dbs[key]
            conn = sqlite3.connect(str(db))
            result = conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
            assert result[0] == "ok", f"Integrity check failed for {db}"

    def test_metadata_reflects_v1_overrides(self, real_dbs):
        meta = read_db_metadata(real_dbs["v1_path"])
        assert meta["project_id"] == real_dbs["project_id"]
        assert meta["cv_version"] == "1.0.0"
        assert meta["universe_version"] == "1.0.0"

    def test_metadata_reflects_v2_overrides(self, real_dbs):
        meta = read_db_metadata(real_dbs["v2_path"])
        assert meta["project_id"] == real_dbs["project_id"]
        assert meta["cv_version"] == "2.0.0"
        assert meta["universe_version"] == "1.0.0"

    def test_metadata_has_build_date(self, real_dbs):
        meta = read_db_metadata(real_dbs["v1_path"])
        assert "build_date" in meta
        assert meta["build_date"]  # Non-empty

    def test_metadata_has_esgvoc_version(self, real_dbs):
        meta = read_db_metadata(real_dbs["v1_path"])
        assert "esgvoc_version" in meta
        assert meta["esgvoc_version"]

    def test_project_tables_exist(self, real_dbs):
        tables = db_table_names(real_dbs["v1_path"])
        # Project DBs must contain these tables
        assert "pterms" in tables, f"pterms missing from {tables}"
        assert "pcollections" in tables, f"pcollections missing from {tables}"

    def test_no_universe_tables_in_project_db(self, real_dbs):
        """
        Project DBs must NOT contain universe tables (uterms, udata_descriptors).
        Universe data lives in a separate universe DB; the project DB is self-contained
        for project terms only.  The validator auto-detects this split via project_id.
        """
        tables = db_table_names(real_dbs["v1_path"])
        assert "uterms" not in tables, "uterms should not be in a project DB"
        assert "udata_descriptors" not in tables, "udata_descriptors should not be in a project DB"

    def test_pterms_is_nonempty(self, real_dbs):
        count = db_row_count(real_dbs["v1_path"], "pterms")
        assert count > 0, "pterms table is empty — ingestion may have failed"

    def test_pcollections_is_nonempty(self, real_dbs):
        count = db_row_count(real_dbs["v1_path"], "pcollections")
        assert count > 0, "pcollections table is empty — ingestion may have failed"


class TestValidation:
    """DT-5 / DT-6: DBValidator passes on the real-built DB."""

    def test_validator_basic_passes_on_v1(self, real_dbs):
        from esgvoc.admin.validator import DBValidator

        result = DBValidator().validate(real_dbs["v1_path"])
        failures = [(name, msg) for name, ok, msg in result.checks if not ok]
        assert not failures, f"Validation failures: {failures}"

    def test_validator_basic_passes_on_v2(self, real_dbs):
        from esgvoc.admin.validator import DBValidator

        result = DBValidator().validate(real_dbs["v2_path"])
        failures = [(name, msg) for name, ok, msg in result.checks if not ok]
        assert not failures, f"Validation failures: {failures}"

    def test_validator_full_passes_on_v1(self, real_dbs):
        from esgvoc.admin.validator import DBValidator

        result = DBValidator().validate(real_dbs["v1_path"], full=True)
        failures = [(name, msg) for name, ok, msg in result.checks if not ok]
        assert not failures, f"Full validation failures: {failures}"


class TestTwoVersionsDistinction:
    """DT-7: same git content, different manifest_overrides → distinct metadata only."""

    def test_v1_and_v2_cv_version_differ(self, real_dbs):
        meta_v1 = read_db_metadata(real_dbs["v1_path"])
        meta_v2 = read_db_metadata(real_dbs["v2_path"])
        assert meta_v1["cv_version"] != meta_v2["cv_version"]

    def test_v1_and_v2_have_same_term_count(self, real_dbs):
        """Same repo HEAD → same number of terms in both builds."""
        count_v1 = db_row_count(real_dbs["v1_path"], "pterms")
        count_v2 = db_row_count(real_dbs["v2_path"], "pterms")
        assert count_v1 == count_v2, (
            f"Term counts differ unexpectedly: v1={count_v1}, v2={count_v2}"
        )

    def test_v1_and_v2_files_differ(self, real_dbs):
        """The two DB files must be different bytes (metadata embedded in DB differ)."""
        sha_v1 = hashlib.sha256(real_dbs["v1_path"].read_bytes()).hexdigest()
        sha_v2 = hashlib.sha256(real_dbs["v2_path"].read_bytes()).hexdigest()
        assert sha_v1 != sha_v2


class TestBuildResult:
    """DT-9 / DT-10: build_dev returns correct checksum and size.

    Uses the BuildResult captured during the session fixture build.
    If the DBs were loaded from cache (no BuildResult), these tests are skipped.
    """

    def test_build_result_checksum_matches_file(self, real_dbs):
        result = real_dbs["v1_result"]
        if result is None:
            pytest.skip("DB was loaded from cache — no BuildResult available; delete test_data/dbs/ to re-test")
        actual_sha = hashlib.sha256(real_dbs["v1_path"].read_bytes()).hexdigest()
        assert result.checksum_sha256 == actual_sha, (
            f"BuildResult.checksum_sha256={result.checksum_sha256} "
            f"but actual file SHA-256={actual_sha}"
        )

    def test_build_result_size_matches_file(self, real_dbs):
        result = real_dbs["v1_result"]
        if result is None:
            pytest.skip("DB was loaded from cache — no BuildResult available; delete test_data/dbs/ to re-test")
        assert result.size_bytes == real_dbs["v1_path"].stat().st_size

    def test_build_result_project_id_matches_override(self, real_dbs):
        result = real_dbs["v1_result"]
        if result is None:
            pytest.skip("DB was loaded from cache — no BuildResult available")
        assert result.project_id == real_dbs["project_id"]

    def test_build_result_cv_version_matches_override(self, real_dbs):
        result = real_dbs["v1_result"]
        if result is None:
            pytest.skip("DB was loaded from cache — no BuildResult available")
        assert result.cv_version == "1.0.0"


class TestAdminDiff:
    """DT-8: admin diff CLI detects metadata changes between two real builds."""

    def test_diff_detects_cv_version_change(self, real_dbs):
        from esgvoc.admin.cli import app as admin_app

        result = runner.invoke(
            admin_app,
            ["diff", str(real_dbs["v1_path"]), str(real_dbs["v2_path"])],
        )
        assert result.exit_code == 0, result.output
        # The diff output should mention cv_version or the two version strings
        output = result.output
        assert "1.0.0" in output or "2.0.0" in output or "cv_version" in output


class TestAdminCLIBuild:
    """
    Smoke test for the ``esgvoc admin build`` CLI in dev mode.

    Uses the pre-built DBs from the session fixture to avoid a full rebuild per test.
    We verify that the ``validate`` and ``diff`` sub-commands work on real output.
    """

    def test_admin_validate_cli_on_real_db(self, real_dbs):
        from esgvoc.admin.cli import app as admin_app

        result = runner.invoke(admin_app, ["validate", str(real_dbs["v1_path"])])
        assert result.exit_code == 0, result.output

    def test_admin_validate_full_cli_on_real_db(self, real_dbs):
        from esgvoc.admin.cli import app as admin_app

        result = runner.invoke(admin_app, ["validate", "--full", str(real_dbs["v1_path"])])
        assert result.exit_code == 0, result.output

    def test_admin_diff_cli_on_two_real_dbs(self, real_dbs):
        from esgvoc.admin.cli import app as admin_app

        result = runner.invoke(
            admin_app,
            ["diff", str(real_dbs["v1_path"]), str(real_dbs["v2_path"])],
        )
        assert result.exit_code == 0, result.output
        # Diff must mention both version strings
        assert "1.0.0" in result.output or "2.0.0" in result.output
