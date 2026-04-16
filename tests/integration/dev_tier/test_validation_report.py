"""
Dev Tier — ValidationReport and MatchingTerm structure tests.

Tests the full structure of the validation API return types:
  - ValidationReport from valid_term
  - MatchingTerm from valid_term_in_collection / valid_term_in_project
  - Error content when validation fails

Plan scenarios covered:
  DT-79  valid_term with matching value → validated=True, nb_errors=0
  DT-80  valid_term with non-matching value → validated=False, errors populated
  DT-81  ValidationReport attributes: expression, errors, nb_errors, validated
  DT-82  ValidationReport.__bool__ is True on pass, False on fail
  DT-83  valid_term_in_collection with matching value → non-empty MatchingTerm list
  DT-84  MatchingTerm has project_id, collection_id, term_id attributes
  DT-85  valid_term_in_collection with non-matching value → empty list
  DT-86  valid_term raises EsgvocNotFoundError for unknown project/collection/term
  DT-87  valid_term_in_project returns matches for a known drs_name value
  DT-88  valid_term_in_collection with empty string raises EsgvocValueError
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import esgvoc.api as ev
import esgvoc.core.service as svc
from esgvoc.core.db.connection import DBConnection

# ---------------------------------------------------------------------------
# Known constants from real cmip6 DB
# ---------------------------------------------------------------------------

_PROJECT_ID = "cmip6"
_KNOWN_COLLECTION = "activity_id"
_KNOWN_TERM = "aerchemmip"
_KNOWN_DRS_VALUE = "AerChemMIP"       # drs_name for aerchemmip
_UNKNOWN_VALUE = "THIS-VALUE-CANNOT-MATCH-ANYTHING-XYZ-999"
_UNKNOWN_PROJECT = "nonexistent-xyz"
_UNKNOWN_COLLECTION = "nonexistent-collection-xyz"
_UNKNOWN_TERM = "nonexistent-term-xyz-abc"


# ---------------------------------------------------------------------------
# Context manager
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
    fake_universe = SimpleNamespace(db_connection=universe_conn)

    svc.current_state = SimpleNamespace(
        projects={_PROJECT_ID: fake_project},
        universe=fake_universe,
    )
    try:
        yield
    finally:
        project_conn.engine.dispose()
        if universe_conn:
            universe_conn.engine.dispose()
        svc.current_state = original


# ---------------------------------------------------------------------------
# DT-79  valid_term with matching value → validated=True
# ---------------------------------------------------------------------------

class TestValidTermPass:
    """DT-79: valid_term with a correct drs_name value passes validation."""

    def test_returns_validation_report(self, real_dbs, universe_db):
        from esgvoc.api.report import ValidationReport
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert isinstance(report, ValidationReport)

    def test_validated_is_true_on_match(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert report.validated is True

    def test_nb_errors_is_zero_on_match(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert report.nb_errors == 0

    def test_errors_list_is_empty_on_match(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert report.errors == []


# ---------------------------------------------------------------------------
# DT-80  valid_term with non-matching value → validated=False
# ---------------------------------------------------------------------------

class TestValidTermFail:
    """DT-80: valid_term with a wrong value returns errors."""

    def test_validated_is_false_on_mismatch(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert report.validated is False

    def test_nb_errors_nonzero_on_mismatch(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert report.nb_errors > 0

    def test_errors_list_populated_on_mismatch(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert len(report.errors) > 0


# ---------------------------------------------------------------------------
# DT-81  ValidationReport attributes
# ---------------------------------------------------------------------------

class TestValidationReportAttributes:
    """DT-81: ValidationReport exposes all documented attributes."""

    def test_report_has_expression_attribute(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert hasattr(report, "expression")
        assert report.expression == _KNOWN_DRS_VALUE

    def test_report_has_errors_attribute(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert hasattr(report, "errors")
        assert isinstance(report.errors, list)

    def test_report_has_nb_errors_attribute(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert hasattr(report, "nb_errors")
        assert isinstance(report.nb_errors, int)

    def test_report_has_validated_attribute(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert hasattr(report, "validated")
        assert isinstance(report.validated, bool)

    def test_nb_errors_equals_len_errors(self, real_dbs, universe_db):
        """nb_errors should equal len(errors) at all times."""
        with _inject(real_dbs["v1_path"], universe_db):
            pass_report = ev.valid_term(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
            fail_report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert pass_report.nb_errors == len(pass_report.errors)
        assert fail_report.nb_errors == len(fail_report.errors)


# ---------------------------------------------------------------------------
# DT-82  ValidationReport.__bool__
# ---------------------------------------------------------------------------

class TestValidationReportBool:
    """DT-82: ValidationReport is truthy on pass, falsy on fail."""

    def test_bool_true_on_pass(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert bool(report) is True

    def test_bool_false_on_fail(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert bool(report) is False

    def test_len_is_nb_errors(self, real_dbs, universe_db):
        """len(report) should equal report.nb_errors."""
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert len(report) == report.nb_errors


# ---------------------------------------------------------------------------
# DT-83 / DT-84  valid_term_in_collection returns MatchingTerm list
# ---------------------------------------------------------------------------

class TestValidTermInCollectionMatchingTerm:
    """DT-83 / DT-84: valid_term_in_collection returns MatchingTerm objects."""

    def test_known_value_returns_nonempty_list(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_collection(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION
            )
        assert len(matches) > 0

    def test_matching_term_has_project_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_collection(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION
            )
        for m in matches:
            assert hasattr(m, "project_id")
            assert m.project_id == _PROJECT_ID

    def test_matching_term_has_collection_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_collection(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION
            )
        for m in matches:
            assert hasattr(m, "collection_id")
            assert m.collection_id == _KNOWN_COLLECTION

    def test_matching_term_has_term_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_collection(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION
            )
        for m in matches:
            assert hasattr(m, "term_id")
            assert m.term_id  # non-empty

    def test_known_term_id_in_matches(self, real_dbs, universe_db):
        """The known term should appear in the matches for its drs_name."""
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_collection(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION
            )
        term_ids = [m.term_id for m in matches]
        assert _KNOWN_TERM in term_ids, (
            f"Expected '{_KNOWN_TERM}' in matches; got {term_ids}"
        )


# ---------------------------------------------------------------------------
# DT-85  valid_term_in_collection with non-matching value → empty list
# ---------------------------------------------------------------------------

class TestValidTermInCollectionNoMatch:
    """DT-85: valid_term_in_collection with a non-matching value returns empty list."""

    def test_unknown_value_returns_empty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_collection(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION
            )
        assert matches == []

    def test_unknown_collection_returns_empty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_collection(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _UNKNOWN_COLLECTION
            )
        assert matches == []

    def test_unknown_project_returns_empty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_collection(
                _KNOWN_DRS_VALUE, _UNKNOWN_PROJECT, _KNOWN_COLLECTION
            )
        assert matches == []


# ---------------------------------------------------------------------------
# DT-86  valid_term raises EsgvocNotFoundError for unknown ids
# ---------------------------------------------------------------------------

class TestValidTermNotFound:
    """DT-86: valid_term raises EsgvocNotFoundError when project/collection/term not found."""

    def test_unknown_project_raises_not_found(self, real_dbs, universe_db):
        from esgvoc.core.exceptions import EsgvocNotFoundError
        with _inject(real_dbs["v1_path"], universe_db):
            with pytest.raises(EsgvocNotFoundError):
                ev.valid_term(
                    _KNOWN_DRS_VALUE, _UNKNOWN_PROJECT, _KNOWN_COLLECTION, _KNOWN_TERM
                )

    def test_unknown_collection_raises_not_found(self, real_dbs, universe_db):
        from esgvoc.core.exceptions import EsgvocNotFoundError
        with _inject(real_dbs["v1_path"], universe_db):
            with pytest.raises(EsgvocNotFoundError):
                ev.valid_term(
                    _KNOWN_DRS_VALUE, _PROJECT_ID, _UNKNOWN_COLLECTION, _KNOWN_TERM
                )

    def test_unknown_term_raises_not_found(self, real_dbs, universe_db):
        from esgvoc.core.exceptions import EsgvocNotFoundError
        with _inject(real_dbs["v1_path"], universe_db):
            with pytest.raises(EsgvocNotFoundError):
                ev.valid_term(
                    _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _UNKNOWN_TERM
                )


# ---------------------------------------------------------------------------
# DT-87  valid_term_in_project returns matches for a known value
# ---------------------------------------------------------------------------

class TestValidTermInProject:
    """DT-87: valid_term_in_project returns MatchingTerm for a known drs_name."""

    def test_known_value_returns_matches(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_project(_KNOWN_DRS_VALUE, _PROJECT_ID)
        assert len(matches) > 0

    def test_matches_are_matching_term_instances(self, real_dbs, universe_db):
        from esgvoc.api.search import MatchingTerm
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_project(_KNOWN_DRS_VALUE, _PROJECT_ID)
        for m in matches:
            assert isinstance(m, MatchingTerm)

    def test_all_matches_have_correct_project_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_project(_KNOWN_DRS_VALUE, _PROJECT_ID)
        for m in matches:
            assert m.project_id == _PROJECT_ID

    def test_unknown_value_returns_empty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_project(_UNKNOWN_VALUE, _PROJECT_ID)
        assert matches == []


# ---------------------------------------------------------------------------
# DT-88  valid_term_in_collection with empty string raises EsgvocValueError
# ---------------------------------------------------------------------------

class TestValidTermEmptyString:
    """DT-88: empty string value raises EsgvocValueError before any DB query."""

    def test_empty_value_raises_value_error_in_collection(self, real_dbs, universe_db):
        from esgvoc.core.exceptions import EsgvocValueError
        with _inject(real_dbs["v1_path"], universe_db):
            with pytest.raises(EsgvocValueError):
                ev.valid_term_in_collection("", _PROJECT_ID, _KNOWN_COLLECTION)

    def test_empty_value_raises_value_error_in_project(self, real_dbs, universe_db):
        from esgvoc.core.exceptions import EsgvocValueError
        with _inject(real_dbs["v1_path"], universe_db):
            with pytest.raises(EsgvocValueError):
                ev.valid_term_in_project("", _PROJECT_ID)

    def test_empty_value_raises_value_error_in_all_projects(self, real_dbs, universe_db):
        from esgvoc.core.exceptions import EsgvocValueError
        with _inject(real_dbs["v1_path"], universe_db):
            with pytest.raises(EsgvocValueError):
                ev.valid_term_in_all_projects("")
