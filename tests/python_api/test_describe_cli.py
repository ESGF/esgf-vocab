"""
Tests for the `esgvoc describe` CLI command.
"""

import pytest
from typer.testing import CliRunner

from esgvoc.cli.describe import app

pytestmark = pytest.mark.needs_db

runner = CliRunner()


class TestDescribeUniverse:
    def test_describe_known_data_descriptor(self):
        result = runner.invoke(app, ["frequency"])
        assert result.exit_code == 0
        assert "Frequency" in result.output

    def test_describe_explicit_universe_keyword(self):
        result = runner.invoke(app, ["universe", "frequency"])
        assert result.exit_code == 0
        assert "Frequency" in result.output

    def test_describe_union_data_descriptor(self):
        result = runner.invoke(app, ["source"])
        assert result.exit_code == 0
        assert "SourceCMIP7" in result.output
        assert "SourceLegacy" in result.output
        assert "union" in result.output.lower()

    def test_describe_unknown_data_descriptor(self):
        result = runner.invoke(app, ["non_existent_xyz"])
        assert result.exit_code == 1
        assert "Unknown" in result.output


class TestDescribeProjectCollection:
    def test_describe_concrete_collection(self, installed_dbs):
        result = runner.invoke(app, ["cmip7", "experiment"])
        assert result.exit_code == 0
        assert "ExperimentCMIP7" in result.output

    def test_describe_collection_shows_fields(self, installed_dbs):
        result = runner.invoke(app, ["cmip7", "experiment"])
        assert result.exit_code == 0
        assert "Field" in result.output
        assert "Type" in result.output
        assert "Required" in result.output

    def test_describe_unknown_collection(self, installed_dbs):
        result = runner.invoke(app, ["cmip7", "non_existent_xyz"])
        assert result.exit_code == 1

    def test_describe_unknown_project(self):
        result = runner.invoke(app, ["non_existent_project", "source"])
        assert result.exit_code == 1
        assert "Unknown project" in result.output


class TestDescribeAllCollections:
    def test_list_all_models_for_project(self, installed_dbs):
        result = runner.invoke(app, ["cmip7"])
        assert result.exit_code == 0
        assert "Collection" in result.output
        assert "Model" in result.output
        assert "experiment" in result.output
        assert "ExperimentCMIP7" in result.output

    def test_list_shows_docstring_free_output(self, installed_dbs):
        """Listing mode should be a table, not individual model details."""
        result = runner.invoke(app, ["cmip7"])
        assert result.exit_code == 0
        # Should not contain field-level details (those are for single-model view)
        assert "Required" not in result.output
