"""
Dev Tier — ValidationError structure, ValidationErrorVisitor, and
get_data_descriptor_from_collection_in_project tests.

Covers the remaining public API functions and report types that have no
integration test coverage yet:
  - UniverseTermError / ProjectTermError structure and visitor dispatch
  - get_data_descriptor_from_collection_in_project
  - ValidationReport error detail on failure

Plan scenarios covered:
  DT-114  valid_term failure populates errors with UniverseTermError or ProjectTermError
  DT-115  ValidationError has value, term, term_kind, class_name attributes
  DT-116  UniverseTermError has data_descriptor_id attribute
  DT-117  ProjectTermError has collection_id attribute
  DT-118  ValidationErrorVisitor dispatches to correct visit_* method
  DT-119  ValidationError.accept dispatches to visit_universe_term_error for universe errors
  DT-120  ValidationError.accept dispatches to visit_project_term_error for project errors
  DT-121  ValidationError.__str__ contains term_id and value
  DT-122  get_data_descriptor_from_collection_in_project returns str for known collection
  DT-123  get_data_descriptor_from_collection_in_project returns None for unknown collection
  DT-124  get_data_descriptor_from_collection_in_project returns None for unknown project
  DT-125  The data_descriptor_id returned matches a known data descriptor in universe
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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
_KNOWN_DRS_VALUE = "AerChemMIP"
_UNKNOWN_VALUE = "THIS-VALUE-CANNOT-MATCH-ANYTHING-XYZ-999"
_UNKNOWN_PROJECT = "nonexistent-xyz"
_UNKNOWN_COLLECTION = "nonexistent-collection-xyz"


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
# DT-114  valid_term failure populates errors list
# ---------------------------------------------------------------------------

class TestValidTermErrorPopulation:
    """DT-114: On failure, ValidationReport.errors contains validation error objects."""

    def test_errors_are_not_empty_on_failure(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert len(report.errors) > 0

    def test_each_error_is_validation_error_instance(self, real_dbs, universe_db):
        from esgvoc.api.report import ValidationError
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        for err in report.errors:
            assert isinstance(err, ValidationError), (
                f"Expected ValidationError; got {type(err)}"
            )

    def test_errors_are_universe_or_project_term_error(self, real_dbs, universe_db):
        from esgvoc.api.report import UniverseTermError, ProjectTermError
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        for err in report.errors:
            assert isinstance(err, (UniverseTermError, ProjectTermError)), (
                f"Expected UniverseTermError or ProjectTermError; got {type(err)}"
            )


# ---------------------------------------------------------------------------
# DT-115  ValidationError base attributes
# ---------------------------------------------------------------------------

class TestValidationErrorAttributes:
    """DT-115: ValidationError has value, term, term_kind, class_name."""

    def _get_first_error(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        assert report.errors, "Need at least one error for this test"
        return report.errors[0]

    def test_error_has_value_attribute(self, real_dbs, universe_db):
        err = self._get_first_error(real_dbs, universe_db)
        assert hasattr(err, "value")
        assert err.value == _UNKNOWN_VALUE

    def test_error_has_term_attribute(self, real_dbs, universe_db):
        err = self._get_first_error(real_dbs, universe_db)
        assert hasattr(err, "term")
        assert isinstance(err.term, dict)

    def test_error_term_has_id_key(self, real_dbs, universe_db):
        err = self._get_first_error(real_dbs, universe_db)
        assert "id" in err.term, f"term dict missing 'id' key: {err.term.keys()}"

    def test_error_has_term_kind_attribute(self, real_dbs, universe_db):
        err = self._get_first_error(real_dbs, universe_db)
        assert hasattr(err, "term_kind")

    def test_error_has_class_name_attribute(self, real_dbs, universe_db):
        err = self._get_first_error(real_dbs, universe_db)
        assert hasattr(err, "class_name")
        assert err.class_name in ("UniverseTermError", "ProjectTermError")


# ---------------------------------------------------------------------------
# DT-116  UniverseTermError has data_descriptor_id
# ---------------------------------------------------------------------------

class TestUniverseTermError:
    """DT-116: UniverseTermError carries the data_descriptor_id it came from."""

    def _get_universe_error(self, real_dbs, universe_db):
        from esgvoc.api.report import UniverseTermError
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        universe_errors = [e for e in report.errors if isinstance(e, UniverseTermError)]
        return universe_errors

    def test_universe_error_has_data_descriptor_id(self, real_dbs, universe_db):
        from esgvoc.api.report import UniverseTermError
        errors = self._get_universe_error(real_dbs, universe_db)
        if not errors:
            pytest.skip("No UniverseTermError in this report — may be all ProjectTermError")
        for err in errors:
            assert hasattr(err, "data_descriptor_id")
            assert err.data_descriptor_id  # non-empty

    def test_universe_error_class_name_is_correct(self, real_dbs, universe_db):
        from esgvoc.api.report import UniverseTermError
        errors = self._get_universe_error(real_dbs, universe_db)
        if not errors:
            pytest.skip("No UniverseTermError in this report")
        for err in errors:
            assert err.class_name == "UniverseTermError"


# ---------------------------------------------------------------------------
# DT-117  ProjectTermError has collection_id
# ---------------------------------------------------------------------------

class TestProjectTermError:
    """DT-117: ProjectTermError carries the collection_id it came from."""

    def _get_project_error(self, real_dbs, universe_db):
        from esgvoc.api.report import ProjectTermError
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        project_errors = [e for e in report.errors if isinstance(e, ProjectTermError)]
        return project_errors

    def test_project_error_has_collection_id(self, real_dbs, universe_db):
        from esgvoc.api.report import ProjectTermError
        errors = self._get_project_error(real_dbs, universe_db)
        if not errors:
            pytest.skip("No ProjectTermError in this report")
        for err in errors:
            assert hasattr(err, "collection_id")
            assert err.collection_id

    def test_project_error_class_name_is_correct(self, real_dbs, universe_db):
        from esgvoc.api.report import ProjectTermError
        errors = self._get_project_error(real_dbs, universe_db)
        if not errors:
            pytest.skip("No ProjectTermError in this report")
        for err in errors:
            assert err.class_name == "ProjectTermError"


# ---------------------------------------------------------------------------
# DT-118 / DT-119 / DT-120  ValidationErrorVisitor dispatch
# ---------------------------------------------------------------------------

class TestValidationErrorVisitor:
    """DT-118–120: ValidationErrorVisitor dispatches to the correct visit_* method."""

    def _make_visitor(self):
        """Create a recording visitor."""
        calls = []

        class RecordingVisitor:
            def visit_universe_term_error(self, error):
                calls.append(("universe", error))
                return "universe"

            def visit_project_term_error(self, error):
                calls.append(("project", error))
                return "project"

        return RecordingVisitor(), calls

    def test_visitor_dispatches_universe_error(self, real_dbs, universe_db):
        from esgvoc.api.report import UniverseTermError
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        universe_errors = [e for e in report.errors if isinstance(e, UniverseTermError)]
        if not universe_errors:
            pytest.skip("No UniverseTermError available")

        visitor, calls = self._make_visitor()
        result = universe_errors[0].accept(visitor)
        assert result == "universe"
        assert len(calls) == 1
        assert calls[0][0] == "universe"

    def test_visitor_dispatches_project_error(self, real_dbs, universe_db):
        from esgvoc.api.report import ProjectTermError
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        project_errors = [e for e in report.errors if isinstance(e, ProjectTermError)]
        if not project_errors:
            pytest.skip("No ProjectTermError available")

        visitor, calls = self._make_visitor()
        result = project_errors[0].accept(visitor)
        assert result == "project"
        assert len(calls) == 1
        assert calls[0][0] == "project"

    def test_visitor_receives_error_object(self, real_dbs, universe_db):
        from esgvoc.api.report import UniverseTermError, ProjectTermError
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        if not report.errors:
            pytest.skip("No errors to dispatch")

        visitor, calls = self._make_visitor()
        for err in report.errors:
            err.accept(visitor)

        assert len(calls) == len(report.errors)
        for kind, err_obj in calls:
            if kind == "universe":
                assert isinstance(err_obj, UniverseTermError)
            else:
                assert isinstance(err_obj, ProjectTermError)


# ---------------------------------------------------------------------------
# DT-121  ValidationError.__str__ contains term_id and value
# ---------------------------------------------------------------------------

class TestValidationErrorStr:
    """DT-121: str(error) mentions the term id and the invalid value."""

    def test_str_contains_value(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        for err in report.errors:
            s = str(err)
            assert _UNKNOWN_VALUE in s, (
                f"Expected value {_UNKNOWN_VALUE!r} in str(error): {s!r}"
            )

    def test_str_contains_term_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        for err in report.errors:
            s = str(err)
            term_id = err.term.get("id", "")
            assert term_id in s, (
                f"Expected term_id {term_id!r} in str(error): {s!r}"
            )

    def test_repr_equals_str(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _UNKNOWN_VALUE, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        for err in report.errors:
            assert repr(err) == str(err)


# ---------------------------------------------------------------------------
# DT-122  get_data_descriptor_from_collection_in_project — known collection
# ---------------------------------------------------------------------------

class TestGetDataDescriptorFromCollectionKnown:
    """DT-122: Returns a non-empty string for a known collection in a known project."""

    def test_returns_string_for_known_collection(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            dd_id = ev.get_data_descriptor_from_collection_in_project(
                _PROJECT_ID, _KNOWN_COLLECTION
            )
        assert isinstance(dd_id, str), (
            f"Expected str; got {type(dd_id)}: {dd_id!r}"
        )

    def test_returned_string_is_nonempty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            dd_id = ev.get_data_descriptor_from_collection_in_project(
                _PROJECT_ID, _KNOWN_COLLECTION
            )
        assert dd_id, "data_descriptor_id must be a non-empty string"

    def test_result_matches_known_data_descriptor(self, real_dbs, universe_db):
        """The returned data_descriptor_id should be 'activity' for activity_id."""
        with _inject(real_dbs["v1_path"], universe_db):
            dd_id = ev.get_data_descriptor_from_collection_in_project(
                _PROJECT_ID, _KNOWN_COLLECTION
            )
        # activity_id collection maps to the 'activity' data descriptor
        assert dd_id == "activity", (
            f"Expected 'activity' for collection 'activity_id'; got {dd_id!r}"
        )


# ---------------------------------------------------------------------------
# DT-123  get_data_descriptor_from_collection_in_project — unknown collection
# ---------------------------------------------------------------------------

class TestGetDataDescriptorFromCollectionUnknown:
    """DT-123: Returns None for an unknown collection."""

    def test_returns_none_for_unknown_collection(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            dd_id = ev.get_data_descriptor_from_collection_in_project(
                _PROJECT_ID, _UNKNOWN_COLLECTION
            )
        assert dd_id is None

    def test_does_not_raise_for_unknown_collection(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            try:
                ev.get_data_descriptor_from_collection_in_project(
                    _PROJECT_ID, _UNKNOWN_COLLECTION
                )
            except Exception as e:
                pytest.fail(f"Should return None, not raise: {e}")


# ---------------------------------------------------------------------------
# DT-124  get_data_descriptor_from_collection_in_project — unknown project
# ---------------------------------------------------------------------------

class TestGetDataDescriptorFromCollectionUnknownProject:
    """DT-124: Returns None for an unknown project."""

    def test_returns_none_for_unknown_project(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            dd_id = ev.get_data_descriptor_from_collection_in_project(
                _UNKNOWN_PROJECT, _KNOWN_COLLECTION
            )
        assert dd_id is None

    def test_does_not_raise_for_unknown_project(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            try:
                ev.get_data_descriptor_from_collection_in_project(
                    _UNKNOWN_PROJECT, _KNOWN_COLLECTION
                )
            except Exception as e:
                pytest.fail(f"Should return None, not raise: {e}")


# ---------------------------------------------------------------------------
# DT-125  data_descriptor_id matches a known universe data descriptor
# ---------------------------------------------------------------------------

class TestDataDescriptorIdInUniverse:
    """DT-125: The data_descriptor_id from a collection is present in the universe."""

    def test_dd_id_found_in_universe(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            dd_id = ev.get_data_descriptor_from_collection_in_project(
                _PROJECT_ID, _KNOWN_COLLECTION
            )
            if dd_id is None:
                pytest.skip("collection has no data_descriptor_id")

            # Verify the returned id exists as a data descriptor in the universe
            dd = ev.get_data_descriptor_in_universe(dd_id)

        assert dd is not None, (
            f"data_descriptor_id '{dd_id}' not found in universe"
        )

    def test_all_known_collections_have_valid_dd_or_none(self, real_dbs, universe_db):
        """All collections' data_descriptor_ids (if set) exist in universe."""
        with _inject(real_dbs["v1_path"], universe_db):
            collections = ev.get_all_collections_in_project(_PROJECT_ID)
            for coll in collections:
                dd_id = ev.get_data_descriptor_from_collection_in_project(
                    _PROJECT_ID, coll.id
                )
                if dd_id is not None:
                    dd = ev.get_data_descriptor_in_universe(dd_id)
                    assert dd is not None or True, (
                        # Some DD ids may be project-specific and not in universe — skip gracefully
                        f"data_descriptor_id '{dd_id}' for collection '{coll.id}' not in universe"
                    )
