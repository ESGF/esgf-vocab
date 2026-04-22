"""
Dev Tier — Schema CLI (Scenario 36) tests.

Tests the ``esgvoc schema <project_id>`` command which generates a JSON-STAC
schema from a project's catalog_specs.yaml configuration.  Corresponds to the
"Schema CLI Version-Specific Generation" scenario described in the plan.

Plan scenarios covered:
  DT-174  esgvoc schema <known_project> exits 0
  DT-175  esgvoc schema output is valid JSON
  DT-176  esgvoc schema JSON output is a dict (object), not a list
  DT-177  esgvoc schema JSON has expected top-level keys
  DT-178  esgvoc schema --output writes to file
  DT-179  esgvoc schema --output file contains valid JSON
  DT-180  esgvoc schema unknown_project exits 1
  DT-181  esgvoc schema unknown_project error message mentions project name
  DT-182  generate_json_schema API returns a dict for known project
  DT-183  generate_json_schema raises for unknown project
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import esgvoc.core.service as svc
from esgvoc.cli.main import app as main_app
from esgvoc.core.db.connection import DBConnection

_PROJECT_ID = "cmip6"
_UNKNOWN_PROJECT = "nonexistent_project_xyz_999"

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixture / context-manager helpers
# ---------------------------------------------------------------------------

@contextmanager
def _inject(project_db: Path, universe_db: Path | None = None):
    original = svc.current_state
    project_conn = DBConnection(db_file_path=project_db)
    fake_project = SimpleNamespace(db_connection=project_conn)
    if universe_db and universe_db.exists():
        universe_conn = DBConnection(db_file_path=universe_db)
    else:
        universe_conn = None
    svc.current_state = SimpleNamespace(
        projects={_PROJECT_ID: fake_project},
        universe=SimpleNamespace(db_connection=universe_conn),
    )
    try:
        yield
    finally:
        project_conn.engine.dispose()
        if universe_conn:
            universe_conn.engine.dispose()
        svc.current_state = original


# ---------------------------------------------------------------------------
# DT-174  esgvoc schema exits 0 for known project
# ---------------------------------------------------------------------------

class TestSchemaExitsOK:
    """DT-174: esgvoc schema <project_id> exits 0 when project exists (Scenario 36)."""

    def test_exits_0_for_known_project(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            result = runner.invoke(main_app, ["schema", _PROJECT_ID])
        assert result.exit_code == 0, (
            f"Expected exit code 0, got {result.exit_code}.\nOutput:\n{result.output}"
        )

    def test_produces_output_for_known_project(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            result = runner.invoke(main_app, ["schema", _PROJECT_ID])
        assert result.output.strip(), "Expected non-empty output"


# ---------------------------------------------------------------------------
# DT-175/176/177  JSON output validity
# ---------------------------------------------------------------------------

class TestSchemaOutputIsValidJSON:
    """DT-175/176/177: esgvoc schema outputs a valid JSON object (Scenario 36)."""

    def test_output_is_valid_json(self, real_dbs, universe_db):
        """DT-175: Output can be parsed as JSON."""
        with _inject(real_dbs["v1_path"], universe_db):
            result = runner.invoke(main_app, ["schema", _PROJECT_ID])
        assert result.exit_code == 0, result.output
        try:
            parsed = json.loads(result.output)
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON: {e}\nOutput:\n{result.output[:500]}")

    def test_output_is_a_dict(self, real_dbs, universe_db):
        """DT-176: Top-level JSON value is an object (dict), not a list."""
        with _inject(real_dbs["v1_path"], universe_db):
            result = runner.invoke(main_app, ["schema", _PROJECT_ID])
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert isinstance(parsed, dict), (
            f"Expected dict at top level, got {type(parsed).__name__}"
        )

    def test_schema_has_type_key(self, real_dbs, universe_db):
        """DT-177: JSON schema has a '$schema' or 'type' or similar structural key."""
        with _inject(real_dbs["v1_path"], universe_db):
            result = runner.invoke(main_app, ["schema", _PROJECT_ID])
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        # JSON schemas typically have '$schema', 'type', or 'properties'
        structural_keys = {"$schema", "type", "properties", "title", "description"}
        found = structural_keys & set(parsed.keys())
        assert found, (
            f"Expected at least one structural key in {structural_keys}, "
            f"got keys: {list(parsed.keys())[:10]}"
        )


# ---------------------------------------------------------------------------
# DT-178/179  --output writes to file
# ---------------------------------------------------------------------------

class TestSchemaOutputToFile:
    """DT-178/179: esgvoc schema --output writes valid JSON to a file (Scenario 36)."""

    def test_output_flag_writes_file(self, real_dbs, universe_db, tmp_path):
        """DT-178: --output creates the specified file."""
        out_file = tmp_path / "schema.json"
        with _inject(real_dbs["v1_path"], universe_db):
            result = runner.invoke(main_app, ["schema", _PROJECT_ID, "--output", str(out_file)])
        assert result.exit_code == 0, result.output
        assert out_file.exists(), f"Expected {out_file} to be created"

    def test_output_file_contains_valid_json(self, real_dbs, universe_db, tmp_path):
        """DT-179: Written file contains valid JSON."""
        out_file = tmp_path / "schema.json"
        with _inject(real_dbs["v1_path"], universe_db):
            result = runner.invoke(main_app, ["schema", _PROJECT_ID, "--output", str(out_file)])
        assert result.exit_code == 0, result.output
        content = out_file.read_text()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            pytest.fail(f"Output file is not valid JSON: {e}")
        assert isinstance(parsed, dict)

    def test_output_file_and_stdout_content_match(self, real_dbs, universe_db, tmp_path):
        """File output and stdout output contain the same schema data."""
        out_file = tmp_path / "schema_cmp.json"
        with _inject(real_dbs["v1_path"], universe_db):
            stdout_result = runner.invoke(main_app, ["schema", _PROJECT_ID])
            file_result = runner.invoke(main_app, ["schema", _PROJECT_ID, "--output", str(out_file)])

        assert stdout_result.exit_code == 0
        assert file_result.exit_code == 0

        from_stdout = json.loads(stdout_result.output)
        from_file = json.loads(out_file.read_text())
        assert from_stdout == from_file


# ---------------------------------------------------------------------------
# DT-180/181  unknown project exits 1
# ---------------------------------------------------------------------------

class TestSchemaUnknownProject:
    """DT-180/181: esgvoc schema <unknown_project> exits non-zero (Scenario 36)."""

    def test_unknown_project_exits_nonzero(self, real_dbs, universe_db):
        """DT-180: Unknown project causes non-zero exit code."""
        with _inject(real_dbs["v1_path"], universe_db):
            result = runner.invoke(main_app, ["schema", _UNKNOWN_PROJECT])
        assert result.exit_code != 0, (
            f"Expected non-zero exit for unknown project, got {result.exit_code}"
        )

    def test_unknown_project_error_mentions_name(self, real_dbs, universe_db):
        """DT-181: Error message contains the unknown project name."""
        with _inject(real_dbs["v1_path"], universe_db):
            result = runner.invoke(main_app, ["schema", _UNKNOWN_PROJECT])
        assert _UNKNOWN_PROJECT in result.output, (
            f"Expected {_UNKNOWN_PROJECT!r} in output, got:\n{result.output}"
        )


# ---------------------------------------------------------------------------
# DT-182/183  generate_json_schema API
# ---------------------------------------------------------------------------

class TestGenerateJsonSchemaAPI:
    """DT-182/183: generate_json_schema() API (used by the CLI command, Scenario 36)."""

    def test_known_project_returns_dict(self, real_dbs, universe_db):
        """DT-182: generate_json_schema returns a dict for a known project."""
        from esgvoc.apps.jsg.json_schema_generator import generate_json_schema
        with _inject(real_dbs["v1_path"], universe_db):
            schema = generate_json_schema(_PROJECT_ID)
        assert isinstance(schema, dict), (
            f"Expected dict from generate_json_schema, got {type(schema).__name__}"
        )

    def test_schema_is_nonempty(self, real_dbs, universe_db):
        from esgvoc.apps.jsg.json_schema_generator import generate_json_schema
        with _inject(real_dbs["v1_path"], universe_db):
            schema = generate_json_schema(_PROJECT_ID)
        assert schema, "Schema dict should not be empty"

    def test_unknown_project_raises(self, real_dbs, universe_db):
        """DT-183: generate_json_schema raises for unknown project."""
        from esgvoc.apps.jsg.json_schema_generator import generate_json_schema
        from esgvoc.core.exceptions import EsgvocException
        with _inject(real_dbs["v1_path"], universe_db):
            with pytest.raises(EsgvocException):
                generate_json_schema(_UNKNOWN_PROJECT)

    def test_schema_json_serializable(self, real_dbs, universe_db):
        """The returned dict must be JSON-serializable (no non-JSON types)."""
        from esgvoc.apps.jsg.json_schema_generator import generate_json_schema
        with _inject(real_dbs["v1_path"], universe_db):
            schema = generate_json_schema(_PROJECT_ID)
        try:
            json.dumps(schema)
        except (TypeError, ValueError) as e:
            pytest.fail(f"Schema is not JSON-serializable: {e}")
