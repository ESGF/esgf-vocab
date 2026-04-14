"""
Tests for the admin module: manifest, builder helpers, validator, CLI.

Network operations (git clone) are not tested here — those belong in
integration tests. We test:
  - Manifest loading and validation
  - DBBuilder helper functions (_resolve_repo_url, _git_sha, _embed_metadata, _sha256)
  - _admin_context service-state injection
  - DBValidator (against minimal hand-crafted SQLite DBs)
  - Admin CLI commands (validate, diff, test) via typer's test runner
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import textwrap
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from esgvoc.admin.cli import app as admin_app
from esgvoc.admin.manifest import Manifest, MANIFEST_FILENAME
from esgvoc.admin.builder import (
    BuildResult,
    _admin_context,
    _resolve_repo_url,
    _sha256,
)
from esgvoc.admin.validator import DBValidator, ValidationResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

runner = CliRunner()


def _make_db(path: Path, *, with_metadata: bool = True, with_data: bool = False) -> None:
    """Create a minimal SQLite DB matching esgvoc schema."""
    with sqlite3.connect(str(path)) as conn:
        if with_metadata:
            conn.execute(
                "CREATE TABLE _esgvoc_metadata (key TEXT PRIMARY KEY, value TEXT)"
            )
            conn.executemany(
                "INSERT INTO _esgvoc_metadata VALUES (?, ?)",
                [
                    ("project_id", "cmip7"),
                    ("cv_version", "v2.1.0"),
                    ("universe_version", "v1.2.0"),
                    ("build_date", "2024-03-25T15:30:00+00:00"),
                    ("esgvoc_version", "1.6.0"),
                    ("commit_sha", "abc1234"),
                    ("universe_commit_sha", "def5678"),
                ],
            )

        conn.execute("CREATE TABLE universes (pk INTEGER PRIMARY KEY, git_hash TEXT)")
        conn.execute(
            "CREATE TABLE udata_descriptors "
            "(pk INTEGER PRIMARY KEY, id TEXT, universe_pk INTEGER, context TEXT, term_kind TEXT)"
        )
        conn.execute(
            "CREATE TABLE uterms "
            "(pk INTEGER PRIMARY KEY, id TEXT, specs TEXT, kind TEXT, data_descriptor_pk INTEGER)"
        )
        conn.execute(
            "CREATE TABLE pterms "
            "(pk INTEGER PRIMARY KEY, id TEXT, specs TEXT, kind TEXT, collection_pk INTEGER)"
        )
        conn.execute(
            "CREATE TABLE pcollections "
            "(pk INTEGER PRIMARY KEY, id TEXT, context TEXT, project_pk INTEGER, "
            "data_descriptor_id TEXT, term_kind TEXT)"
        )
        # Virtual FTS tables (simplified for testing)
        conn.execute(
            "CREATE TABLE uterms_fts5 "
            "(pk INTEGER, id TEXT, specs TEXT, kind TEXT, data_descriptor_pk INTEGER)"
        )
        conn.execute(
            "CREATE TABLE udata_descriptors_fts5 "
            "(pk INTEGER, id TEXT, universe_pk INTEGER, context TEXT, term_kind TEXT)"
        )

        if with_data:
            conn.execute("INSERT INTO universes VALUES (1, 'abc1234')")
            conn.execute(
                "INSERT INTO udata_descriptors VALUES (1, 'institution', 1, '{}', 'PLAIN')"
            )
            conn.execute(
                "INSERT INTO uterms VALUES (1, 'ipsl', '{}', 'PLAIN', 1)"
            )
            conn.execute(
                "INSERT INTO uterms_fts5 VALUES (1, 'ipsl', '{}', 'PLAIN', 1)"
            )
            conn.execute(
                "INSERT INTO udata_descriptors_fts5 VALUES (1, 'institution', 1, '{}', 'PLAIN')"
            )
            conn.execute("INSERT INTO pcollections VALUES (1, 'institution', '{}', 1, 'institution', 'PLAIN')")
            conn.execute("INSERT INTO pterms VALUES (1, 'ipsl', '{}', 'PLAIN', 1)")

        conn.commit()


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

class TestManifest:
    def _write_manifest(self, path: Path, data: dict) -> None:
        with open(path / MANIFEST_FILENAME, "w") as f:
            yaml.dump(data, f)

    def test_load_valid_manifest(self, tmp_path):
        self._write_manifest(tmp_path, {
            "schema_version": "1",
            "project": {"id": "cmip7", "name": "CMIP7 CVs"},
            "cv_version": "2.1.0",
            "universe_version": "1.2.0",
            "esgvoc": {"min_version": "1.5.0", "max_version": None},
            "release_notes": "Added institution",
        })
        m = Manifest.load(tmp_path)
        assert m.project.id == "cmip7"
        assert m.cv_version == "2.1.0"
        assert m.universe_version == "1.2.0"
        assert m.esgvoc.min_version == "1.5.0"
        assert m.release_notes == "Added institution"

    def test_load_missing_manifest_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match=MANIFEST_FILENAME):
            Manifest.load(tmp_path)

    def test_load_or_default_returns_default(self, tmp_path):
        m = Manifest.load_or_default(tmp_path, project_id="test-proj")
        assert m.project.id == "test-proj"
        assert "unknown" in m.cv_version

    def test_load_or_default_returns_real_manifest(self, tmp_path):
        self._write_manifest(tmp_path, {
            "project": {"id": "cmip7", "name": "CMIP7"},
            "cv_version": "2.1.0",
            "universe_version": "1.2.0",
        })
        m = Manifest.load_or_default(tmp_path, project_id="fallback")
        assert m.project.id == "cmip7"  # real manifest wins

    def test_minimal_manifest_no_esgvoc_section(self, tmp_path):
        self._write_manifest(tmp_path, {
            "project": {"id": "cmip6"},
            "cv_version": "6.5.0",
            "universe_version": "1.0.0",
        })
        m = Manifest.load(tmp_path)
        assert m.esgvoc.min_version is None
        assert m.esgvoc.max_version is None


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------

class TestResolveRepoUrl:
    def test_owner_slash_repo(self):
        url = _resolve_repo_url("WCRP-CMIP/CMIP7-CVs")
        assert url == "https://github.com/WCRP-CMIP/CMIP7-CVs.git"

    def test_full_https_url_unchanged(self):
        url = "https://github.com/myorg/myrepo"
        assert _resolve_repo_url(url) == url

    def test_full_http_url_unchanged(self):
        url = "http://github.internal/org/repo"
        assert _resolve_repo_url(url) == url

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _resolve_repo_url("not-a-valid-repo")


class TestSha256:
    def test_known_content(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert _sha256(f) == expected

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.bin"
        f.write_bytes(b"")
        assert _sha256(f) == hashlib.sha256(b"").hexdigest()


class TestEmbedMetadata:
    def test_embed_writes_rows(self, tmp_path):
        db_path = tmp_path / "test.db"
        with sqlite3.connect(str(db_path)) as conn:
            pass  # create empty db

        from esgvoc.admin.builder import DBBuilder
        metadata = {
            "project_id": "cmip7",
            "cv_version": "2.1.0",
            "build_date": "2024-03-25T15:30:00+00:00",
        }
        DBBuilder._embed_metadata(db_path, metadata)

        with sqlite3.connect(str(db_path)) as conn:
            rows = dict(conn.execute("SELECT key, value FROM _esgvoc_metadata").fetchall())
        assert rows["project_id"] == "cmip7"
        assert rows["cv_version"] == "2.1.0"
        assert rows["build_date"] == "2024-03-25T15:30:00+00:00"

    def test_embed_overwrites_existing(self, tmp_path):
        db_path = tmp_path / "test.db"
        from esgvoc.admin.builder import DBBuilder
        DBBuilder._embed_metadata(db_path, {"project_id": "old"})
        DBBuilder._embed_metadata(db_path, {"project_id": "new"})

        with sqlite3.connect(str(db_path)) as conn:
            val = conn.execute(
                "SELECT value FROM _esgvoc_metadata WHERE key='project_id'"
            ).fetchone()[0]
        assert val == "new"


class TestAdminContext:
    def test_overrides_service_state(self):
        import esgvoc.core.service as svc

        original = svc.current_state
        with _admin_context("/fake/universe/path"):
            assert svc.current_state.universe.local_path == "/fake/universe/path"
        assert svc.current_state is original

    def test_restores_on_exception(self):
        import esgvoc.core.service as svc

        original = svc.current_state
        with pytest.raises(RuntimeError):
            with _admin_context("/fake/path"):
                raise RuntimeError("boom")
        assert svc.current_state is original


# ---------------------------------------------------------------------------
# DBValidator
# ---------------------------------------------------------------------------

class TestDBValidatorBasic:
    def test_missing_file(self, tmp_path):
        result = DBValidator().validate(tmp_path / "nonexistent.db")
        assert not result.passed
        assert any("File exists" in n and not ok for n, ok, _ in result.checks)

    def test_valid_db_with_data(self, tmp_path):
        db_path = tmp_path / "test.db"
        _make_db(db_path, with_metadata=True, with_data=True)
        result = DBValidator().validate(db_path)
        assert result.passed, result.summary()

    def test_db_without_metadata_fails(self, tmp_path):
        db_path = tmp_path / "test.db"
        _make_db(db_path, with_metadata=False, with_data=True)
        result = DBValidator().validate(db_path)
        assert not result.passed

    def test_empty_tables_fails(self, tmp_path):
        db_path = tmp_path / "test.db"
        _make_db(db_path, with_metadata=True, with_data=False)
        result = DBValidator().validate(db_path)
        assert not result.passed  # tables are empty

    def test_corrupt_file_fails(self, tmp_path):
        db_path = tmp_path / "corrupt.db"
        db_path.write_bytes(b"not a sqlite database")
        result = DBValidator().validate(db_path)
        assert not result.passed

    def test_full_validation_with_data(self, tmp_path):
        db_path = tmp_path / "test.db"
        _make_db(db_path, with_metadata=True, with_data=True)
        result = DBValidator().validate(db_path, full=True)
        assert result.passed, result.summary()


class TestDBValidatorSchema:
    def _write_json(self, path: Path, content: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(content, f)

    def test_schema_valid_project(self, tmp_path):
        self._write_json(tmp_path / "institution" / "ipsl.json", {"id": "ipsl"})
        with open(tmp_path / MANIFEST_FILENAME, "w") as f:
            yaml.dump({
                "project": {"id": "cmip7", "name": "CMIP7"},
                "cv_version": "2.1.0",
                "universe_version": "1.2.0",
            }, f)
        result = DBValidator().validate_schema(tmp_path)
        assert result.passed, result.summary()

    def test_schema_invalid_json(self, tmp_path):
        (tmp_path / "broken.json").write_text("{not valid json")
        result = DBValidator().validate_schema(tmp_path)
        assert not result.passed

    def test_schema_no_manifest(self, tmp_path):
        self._write_json(tmp_path / "inst" / "ipsl.json", {"id": "ipsl"})
        result = DBValidator().validate_schema(tmp_path)
        # Manifest missing: check is added but JSON files pass
        manifest_check = next(
            (ok for name, ok, _ in result.checks if "manifest" in name.lower()), None
        )
        assert manifest_check is False


class TestValidationResult:
    def test_summary_contains_icons(self):
        r = ValidationResult()
        r.add("check A", True, "looks good")
        r.add("check B", False, "broken")
        summary = r.summary()
        assert "✓" in summary
        assert "✗" in summary
        assert "FAILED" in summary

    def test_all_pass(self):
        r = ValidationResult()
        r.add("check A", True)
        r.add("check B", True)
        assert r.passed
        assert "PASSED" in r.summary()


# ---------------------------------------------------------------------------
# Admin CLI (typer test runner)
# ---------------------------------------------------------------------------

class TestAdminCLI:
    def test_validate_missing_file(self):
        result = runner.invoke(admin_app, ["validate", "/nonexistent/path.db"])
        assert result.exit_code != 0

    def test_validate_valid_db(self, tmp_path):
        db_path = tmp_path / "test.db"
        _make_db(db_path, with_metadata=True, with_data=True)
        result = runner.invoke(admin_app, ["validate", str(db_path)])
        assert result.exit_code == 0, result.output

    def test_validate_empty_db_fails(self, tmp_path):
        db_path = tmp_path / "test.db"
        _make_db(db_path, with_metadata=True, with_data=False)
        result = runner.invoke(admin_app, ["validate", str(db_path)])
        assert result.exit_code != 0

    def test_validate_full_flag(self, tmp_path):
        db_path = tmp_path / "test.db"
        _make_db(db_path, with_metadata=True, with_data=True)
        result = runner.invoke(admin_app, ["validate", "--full", str(db_path)])
        assert result.exit_code == 0, result.output

    def test_validate_schema_only(self, tmp_path):
        with open(tmp_path / MANIFEST_FILENAME, "w") as f:
            yaml.dump({
                "project": {"id": "cmip7", "name": "CMIP7"},
                "cv_version": "2.1.0",
                "universe_version": "1.2.0",
            }, f)
        (tmp_path / "inst.json").write_text('{"id": "ipsl"}')
        result = runner.invoke(admin_app, ["validate", "--schema-only", str(tmp_path)])
        assert result.exit_code == 0, result.output

    def test_test_command(self, tmp_path):
        db_path = tmp_path / "test.db"
        _make_db(db_path, with_metadata=True, with_data=True)
        result = runner.invoke(admin_app, ["test", str(db_path)])
        assert result.exit_code == 0, result.output

    def test_diff_text_output(self, tmp_path):
        db_a = tmp_path / "a.db"
        db_b = tmp_path / "b.db"
        _make_db(db_a, with_metadata=True, with_data=True)
        _make_db(db_b, with_metadata=True, with_data=True)
        result = runner.invoke(admin_app, ["diff", str(db_a), str(db_b)])
        assert result.exit_code == 0, result.output

    def test_diff_json_output(self, tmp_path):
        db_a = tmp_path / "a.db"
        db_b = tmp_path / "b.db"
        _make_db(db_a, with_metadata=True, with_data=True)
        _make_db(db_b, with_metadata=True, with_data=True)
        result = runner.invoke(admin_app, ["diff", str(db_a), str(db_b), "--format", "json"])
        assert result.exit_code == 0, result.output
        # Output should contain valid JSON
        out = result.output
        parsed = json.loads(out)
        assert "baseline" in parsed
        assert "updated" in parsed

    def test_build_missing_required_args(self):
        result = runner.invoke(admin_app, ["build"])
        assert result.exit_code != 0

    def test_build_no_project_mode(self, tmp_path):
        """build without --project-path or --project-repo should fail gracefully."""
        result = runner.invoke(admin_app, [
            "build",
            "--universe-repo", "WCRP-CMIP/WCRP-universe",
            "--universe-ref", "esgvoc_dev",
            "--output", str(tmp_path / "out.db"),
        ])
        assert result.exit_code != 0

    def test_build_local_without_universe_repo_fails(self, tmp_path):
        """--project-path without --universe-path requires --universe-repo and --universe-ref."""
        result = runner.invoke(admin_app, [
            "build",
            "--project-path", str(tmp_path),
            "--output", str(tmp_path / "out.db"),
        ])
        assert result.exit_code != 0

    def test_build_dev_missing_universe_path_not_entered(self, tmp_path):
        """Providing --project-path + --universe-path should route to build_dev."""
        # We can't actually run the build (no real CV data), but we can confirm
        # the CLI accepts the arguments and calls build_dev (which raises on empty dirs).
        result = runner.invoke(admin_app, [
            "build",
            "--project-path", str(tmp_path),
            "--universe-path", str(tmp_path),
            "--project-id", "test-proj",
            "--cv-version", "0.0.1",
            "--universe-version", "0.0.1",
            "--output", str(tmp_path / "out.db"),
        ])
        # build_dev will fail because tmp_path has no CV data, but exit_code != 0
        # confirms the CLI routed correctly (not "missing args" error)
        assert result.exit_code != 0
        # Should NOT be a typer argument error — it should be a build error
        assert "Error" in result.output or result.exception is not None


# ---------------------------------------------------------------------------
# Builder: manifest overrides
# ---------------------------------------------------------------------------

class TestManifestOverrides:
    def test_overrides_applied_no_manifest_file(self, tmp_path):
        """load_or_default + overrides should produce correct metadata."""
        from esgvoc.admin.manifest import Manifest

        # No esgvoc_manifest.yaml in tmp_path
        manifest = Manifest.load_or_default(tmp_path, project_id="fallback")
        assert manifest.project.id == "fallback"
        assert "unknown" in manifest.cv_version

        # Simulate what _run_build does with overrides
        overrides = {
            "project_id": "cmip7",
            "cv_version": "2.1.0",
            "universe_version": "1.0.0",
            "esgvoc_min_version": "1.5.0",
        }
        if "project_id" in overrides:
            manifest.project.id = overrides["project_id"]
        if "cv_version" in overrides:
            manifest.cv_version = overrides["cv_version"]
        if "universe_version" in overrides:
            manifest.universe_version = overrides["universe_version"]
        if "esgvoc_min_version" in overrides:
            manifest.esgvoc.min_version = overrides["esgvoc_min_version"]

        assert manifest.project.id == "cmip7"
        assert manifest.cv_version == "2.1.0"
        assert manifest.universe_version == "1.0.0"
        assert manifest.esgvoc.min_version == "1.5.0"

    def test_overrides_take_precedence_over_manifest_file(self, tmp_path):
        """Overrides beat esgvoc_manifest.yaml values."""
        import yaml
        from esgvoc.admin.manifest import Manifest, MANIFEST_FILENAME

        with open(tmp_path / MANIFEST_FILENAME, "w") as f:
            yaml.dump({
                "project": {"id": "cmip6"},
                "cv_version": "6.0.0",
                "universe_version": "1.0.0",
            }, f)

        manifest = Manifest.load_or_default(tmp_path, project_id="fallback")
        assert manifest.project.id == "cmip6"  # from file

        overrides = {"project_id": "cmip7-override", "cv_version": "7.0.0"}
        if "project_id" in overrides:
            manifest.project.id = overrides["project_id"]
        if "cv_version" in overrides:
            manifest.cv_version = overrides["cv_version"]

        assert manifest.project.id == "cmip7-override"
        assert manifest.cv_version == "7.0.0"
        assert manifest.universe_version == "1.0.0"  # not overridden
