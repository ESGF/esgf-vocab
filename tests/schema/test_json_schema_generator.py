"""
Tests for esgvoc.apps.jsg.json_schema_generator — uses real project DBs.

Covers all three term kinds (PLAIN, PATTERN, COMPOSITE) to prevent
regressions like the stale universe_session bug that broke cmip6/cmip6plus
schema generation.

Marked `needs_db`: network is only required on the very first run to download
the DBs.
"""

import json

import pytest

from esgvoc.apps.jsg.json_schema_generator import generate_json_schema
from esgvoc.core.exceptions import EsgvocNotFoundError

pytestmark = pytest.mark.needs_db


class TestGenerateJsonSchema:
    """End-to-end tests: generate_json_schema must return valid JSON schema dicts."""

    def test_cmip7_schema(self, installed_schema_dbs):
        """cmip7 has PLAIN + PATTERN terms."""
        schema = generate_json_schema("cmip7")
        assert isinstance(schema, dict)
        assert "$schema" in schema or "type" in schema
        assert "properties" in schema or "allOf" in schema or "oneOf" in schema

    def test_cmip6plus_schema(self, installed_schema_dbs):
        """cmip6plus has COMPOSITE terms — the exact path that was broken."""
        schema = generate_json_schema("cmip6plus")
        assert isinstance(schema, dict)
        assert "properties" in schema or "allOf" in schema or "oneOf" in schema

    def test_cordex_cmip5_schema(self, installed_schema_dbs):
        """cordex-cmip5 has PLAIN terms."""
        schema = generate_json_schema("cordex-cmip5")
        assert isinstance(schema, dict)

    def test_input4mips_schema(self, installed_schema_dbs):
        """input4mips has PLAIN terms."""
        schema = generate_json_schema("input4mips")
        assert isinstance(schema, dict)

    def test_schema_is_valid_json(self, installed_schema_dbs):
        """The generated schema must round-trip through JSON serialization."""
        schema = generate_json_schema("cmip7")
        raw = json.dumps(schema, indent=2)
        reparsed = json.loads(raw)
        assert reparsed == schema

    def test_unknown_project_raises(self, installed_schema_dbs):
        with pytest.raises(EsgvocNotFoundError):
            generate_json_schema("nonexistent_project_xyz")

    def test_project_without_catalog_specs_raises(self, installed_schema_dbs):
        """emd has no catalog_specs — should raise EsgvocNotFoundError."""
        # Only test if emd is installed; skip otherwise.
        from esgvoc.api import projects
        if projects.get_project("emd") is None:
            pytest.skip("emd not installed")
        with pytest.raises(EsgvocNotFoundError, match="catalog properties"):
            generate_json_schema("emd")


class TestSchemaStructure:
    """Validate structural properties of generated schemas."""

    def test_cmip7_has_dataset_properties(self, installed_schema_dbs):
        schema = generate_json_schema("cmip7")
        schema_str = json.dumps(schema)
        # Schema should reference cmip7 properties
        assert "cmip7" in schema_str

    def test_cmip6plus_composite_produces_enum_or_anyof(self, installed_schema_dbs):
        """Composite terms should produce enum or anyOf entries in the schema."""
        schema = generate_json_schema("cmip6plus")
        schema_str = json.dumps(schema)
        assert "enum" in schema_str or "anyOf" in schema_str

    def test_all_projects_produce_consistent_structure(self, installed_schema_dbs):
        """All projects with catalog_specs should produce schemas with the same top-level shape."""
        projects_to_test = ["cmip7", "cmip6plus", "cordex-cmip5", "input4mips"]
        for project_id in projects_to_test:
            schema = generate_json_schema(project_id)
            assert isinstance(schema, dict), f"{project_id}: schema is not a dict"
            # All schemas should be JSON Schema documents
            raw = json.dumps(schema)
            assert len(raw) > 100, f"{project_id}: schema suspiciously small"
