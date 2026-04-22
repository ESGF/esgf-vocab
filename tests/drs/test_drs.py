"""
Tests for DRS validation and generation — uses real cmip7@v1.0.0 database.

Marked `needs_db`: network is only required on the very first run to download
the DB.  Once installed (ESGVOC_HOME set with the DB present) tests run offline.

The tests are intentionally kept simple and project-agnostic: they discover
available collections from the DB rather than hardcoding expected values.
Project-specific parametrized tests can be added once the cmip7 DRS structure
is confirmed.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.needs_db


class TestDrsValidator:
    def test_validator_can_be_instantiated(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        validator = DrsValidator("cmip7")
        assert validator is not None

    def test_validate_directory_returns_report(self, installed_dbs):
        """Smoke test: validating anything returns a report object, not an exception."""
        from esgvoc.apps.drs.validator import DrsValidator

        validator = DrsValidator("cmip7")
        # Use a simple string — may have errors but should return a report
        report = validator.validate_directory("anything")
        assert report is not None

    def test_validate_file_name_returns_report(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        validator = DrsValidator("cmip7")
        report = validator.validate_file_name("anything.nc")
        assert report is not None

    def test_validate_dataset_id_returns_report(self, installed_dbs):
        from esgvoc.apps.drs.validator import DrsValidator

        validator = DrsValidator("cmip7")
        report = validator.validate_dataset_id("anything")
        assert report is not None


class TestDrsGenerator:
    def test_generator_can_be_instantiated(self, installed_dbs):
        from esgvoc.apps.drs.generator import DrsGenerator

        gen = DrsGenerator("cmip7")
        assert gen is not None

    def test_generate_from_empty_mapping(self, installed_dbs):
        """Empty mapping should return a report with errors but not raise."""
        from esgvoc.api.project_specs import DrsType
        from esgvoc.apps.drs.generator import DrsGenerator

        gen = DrsGenerator("cmip7")
        report = gen.generate_from_mapping({}, DrsType.DIRECTORY)
        assert report is not None

    def test_generate_from_empty_bag_of_terms(self, installed_dbs):
        from esgvoc.api.project_specs import DrsType
        from esgvoc.apps.drs.generator import DrsGenerator

        gen = DrsGenerator("cmip7")
        report = gen.generate_from_bag_of_terms([], DrsType.DIRECTORY)
        assert report is not None
