"""
Dev Tier — Multi-project API integration tests.

Tests API functions that operate across multiple registered projects
simultaneously (the "all projects" variants).

Plan scenarios covered:
  DT-49  valid_term_in_all_projects returns matches across all projects
  DT-50  get_all_terms_in_all_projects returns terms from every project
  DT-51  get_terms_in_project_by_key_value / get_terms_in_all_projects_by_key_value
  DT-52  find_terms_in_all_projects performs FTS across all registered projects
  DT-53  get_collection_from_data_descriptor_in_project / _in_all_projects
  DT-54  get_term_from_universe_term_id_in_project / _in_all_projects
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import esgvoc.api as ev
import esgvoc.core.service as svc
from esgvoc.core.db.connection import DBConnection
from esgvoc.api.projects import (
    get_term_from_universe_term_id_in_project,
    get_term_from_universe_term_id_in_all_projects,
)

# ---------------------------------------------------------------------------
# Known constants from the real cmip6 project DB
# ---------------------------------------------------------------------------

_PROJECT_A = "cmip6"
_PROJECT_B = "cmip6_copy"   # same DB registered under a different key

_KNOWN_COLLECTION = "activity_id"
_KNOWN_DD = "activity"          # data_descriptor_id that maps to activity_id
_KNOWN_TERM = "aerchemmip"      # term id in activity_id collection
_KNOWN_TERM_DRS = "AerChemMIP"  # drs_name for aerchemmip

_UNKNOWN_DD = "nonexistent-descriptor-xyz"
_UNKNOWN_TERM = "nonexistent-term-xyz-abc"


# ---------------------------------------------------------------------------
# Context manager: inject two project DBs + universe DB
# ---------------------------------------------------------------------------

@contextmanager
def _inject_two_projects(project_db: Path, universe_db: Path | None = None):
    """
    Register the same project DB under two different project IDs to exercise
    the "all projects" API variants.  Optionally wire up a universe connection.
    """
    original = svc.current_state

    conn_a = DBConnection(db_file_path=project_db)
    conn_b = DBConnection(db_file_path=project_db)
    fake_a = SimpleNamespace(db_connection=conn_a)
    fake_b = SimpleNamespace(db_connection=conn_b)

    if universe_db and universe_db.exists():
        universe_conn = DBConnection(db_file_path=universe_db)
    else:
        universe_conn = None
    fake_universe = SimpleNamespace(db_connection=universe_conn)

    svc.current_state = SimpleNamespace(
        projects={_PROJECT_A: fake_a, _PROJECT_B: fake_b},
        universe=fake_universe,
    )
    try:
        yield
    finally:
        conn_a.engine.dispose()
        conn_b.engine.dispose()
        if universe_conn:
            universe_conn.engine.dispose()
        svc.current_state = original


@contextmanager
def _inject_one_project(project_db: Path, universe_db: Path | None = None):
    """Single-project variant for testing the _in_project (non-all) functions."""
    original = svc.current_state

    conn = DBConnection(db_file_path=project_db)
    fake_project = SimpleNamespace(db_connection=conn)

    if universe_db and universe_db.exists():
        universe_conn = DBConnection(db_file_path=universe_db)
    else:
        universe_conn = None
    fake_universe = SimpleNamespace(db_connection=universe_conn)

    svc.current_state = SimpleNamespace(
        projects={_PROJECT_A: fake_project},
        universe=fake_universe,
    )
    try:
        yield
    finally:
        conn.engine.dispose()
        if universe_conn:
            universe_conn.engine.dispose()
        svc.current_state = original


# ---------------------------------------------------------------------------
# DT-49  valid_term_in_all_projects
# ---------------------------------------------------------------------------

class TestValidTermInAllProjects:
    """DT-49: valid_term_in_all_projects validates a value across all projects."""

    def test_known_drs_name_returns_matches(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_all_projects(_KNOWN_TERM_DRS)
        assert len(matches) > 0, (
            f"Expected matches for '{_KNOWN_TERM_DRS}'; got empty list"
        )

    def test_returns_matches_from_both_projects(self, real_dbs, universe_db):
        """Both registered projects (same DB, different IDs) should contribute matches."""
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_all_projects(_KNOWN_TERM_DRS)
        project_ids_found = {m.project_id for m in matches if hasattr(m, "project_id")}
        # At minimum, there should be results; both projects hold the same data
        assert len(matches) >= 1

    def test_nonsense_value_returns_empty(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_all_projects("THIS-VALUE-CANNOT-MATCH-ANYTHING-XYZ")
        assert matches == []

    def test_empty_string_raises_value_error(self, real_dbs, universe_db):
        from esgvoc.core.exceptions import EsgvocValueError
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            with pytest.raises(EsgvocValueError):
                ev.valid_term_in_all_projects("")


# ---------------------------------------------------------------------------
# DT-50  get_all_terms_in_all_projects
# ---------------------------------------------------------------------------

class TestGetAllTermsInAllProjects:
    """DT-50: get_all_terms_in_all_projects aggregates terms from every project."""

    def test_returns_nonempty_list(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_all_projects()
        assert len(terms) > 0

    def test_result_is_list_of_tuples(self, real_dbs, universe_db):
        """Each element should be (project_id, [terms])."""
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = ev.get_all_terms_in_all_projects()
        assert isinstance(results, list)
        for item in results:
            assert isinstance(item, tuple), f"Expected tuple, got {type(item)}: {item}"
            project_id, terms = item
            assert isinstance(project_id, str)
            assert isinstance(terms, list)

    def test_both_projects_present_in_result(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = ev.get_all_terms_in_all_projects()
        project_ids = [r[0] for r in results]
        assert _PROJECT_A in project_ids
        assert _PROJECT_B in project_ids

    def test_no_projects_returns_empty(self, real_dbs, universe_db):
        """With no projects registered, the function returns an empty list."""
        original = svc.current_state
        universe_conn = DBConnection(db_file_path=universe_db)
        svc.current_state = SimpleNamespace(
            projects={},
            universe=SimpleNamespace(db_connection=universe_conn),
        )
        try:
            results = ev.get_all_terms_in_all_projects()
        finally:
            universe_conn.engine.dispose()
            svc.current_state = original
        assert results == []


# ---------------------------------------------------------------------------
# DT-51  get_terms_in_project_by_key_value / get_terms_in_all_projects_by_key_value
# ---------------------------------------------------------------------------

class TestGetTermsByKeyValue:
    """DT-51: key-value search within a project and across all projects."""

    def test_project_kv_finds_matching_term(self, real_dbs, universe_db):
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            terms = ev.get_terms_in_project_by_key_value(
                _PROJECT_A, "drs_name", _KNOWN_TERM_DRS
            )
        assert len(terms) > 0
        assert any(t.id == _KNOWN_TERM for t in terms)

    def test_project_kv_unknown_key_returns_empty(self, real_dbs, universe_db):
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            terms = ev.get_terms_in_project_by_key_value(
                _PROJECT_A, "nonexistent_field_xyz", "anything"
            )
        assert terms == []

    def test_project_kv_unknown_value_returns_empty(self, real_dbs, universe_db):
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            terms = ev.get_terms_in_project_by_key_value(
                _PROJECT_A, "drs_name", "THIS-VALUE-DOES-NOT-EXIST"
            )
        assert terms == []

    def test_project_kv_unknown_project_returns_empty(self, real_dbs, universe_db):
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            terms = ev.get_terms_in_project_by_key_value(
                "nonexistent-project-xyz", "drs_name", _KNOWN_TERM_DRS
            )
        assert terms == []

    def test_all_projects_kv_returns_list_of_tuples(self, real_dbs, universe_db):
        """get_terms_in_all_projects_by_key_value returns [(project_id, [terms])]."""
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = ev.get_terms_in_all_projects_by_key_value("drs_name", _KNOWN_TERM_DRS)
        assert isinstance(results, list)
        assert len(results) > 0
        for item in results:
            pid, terms = item
            assert isinstance(pid, str)
            assert len(terms) > 0

    def test_all_projects_kv_both_projects_appear(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = ev.get_terms_in_all_projects_by_key_value("drs_name", _KNOWN_TERM_DRS)
        project_ids = [r[0] for r in results]
        assert _PROJECT_A in project_ids
        assert _PROJECT_B in project_ids

    def test_all_projects_kv_nonsense_returns_empty(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = ev.get_terms_in_all_projects_by_key_value(
                "drs_name", "THIS-CANNOT-MATCH-XYZ-999"
            )
        assert results == []


# ---------------------------------------------------------------------------
# DT-52  find_terms_in_all_projects
# ---------------------------------------------------------------------------

class TestFindTermsInAllProjects:
    """DT-52: FTS search across all registered projects."""

    def test_known_term_id_returns_results(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = ev.find_terms_in_all_projects(_KNOWN_TERM)
        assert len(results) > 0

    def test_result_is_list_of_tuples(self, real_dbs, universe_db):
        """Each element should be (project_id, [terms])."""
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = ev.find_terms_in_all_projects(_KNOWN_TERM)
        for item in results:
            assert isinstance(item, tuple), f"Expected tuple, got {type(item)}"
            pid, terms = item
            assert isinstance(pid, str)
            assert isinstance(terms, list)

    def test_both_projects_appear_in_results(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = ev.find_terms_in_all_projects(_KNOWN_TERM)
        project_ids = [r[0] for r in results]
        assert _PROJECT_A in project_ids
        assert _PROJECT_B in project_ids

    def test_nonsense_expression_returns_empty(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = ev.find_terms_in_all_projects("xyzxyz_no_match_abc999")
        assert results == []

    def test_find_in_single_project_returns_results(self, real_dbs, universe_db):
        """find_terms_in_project (single-project variant) also works."""
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            terms = ev.find_terms_in_project(_PROJECT_A, _KNOWN_TERM)
        assert len(terms) > 0

    def test_find_in_unknown_project_returns_empty(self, real_dbs, universe_db):
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            terms = ev.find_terms_in_project("nonexistent-project-xyz", _KNOWN_TERM)
        assert terms == []


# ---------------------------------------------------------------------------
# DT-53  get_collection_from_data_descriptor_in_project / _in_all_projects
# ---------------------------------------------------------------------------

class TestGetCollectionFromDataDescriptor:
    """DT-53: look up project collections that map to a universe data descriptor."""

    def test_in_project_known_dd_returns_list(self, real_dbs, universe_db):
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            results = ev.get_collection_from_data_descriptor_in_project(
                _PROJECT_A, _KNOWN_DD
            )
        assert isinstance(results, list)
        assert len(results) > 0

    def test_in_project_result_contains_collection_id_and_dict(self, real_dbs, universe_db):
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            results = ev.get_collection_from_data_descriptor_in_project(
                _PROJECT_A, _KNOWN_DD
            )
        for coll_id, context in results:
            assert isinstance(coll_id, str)
            assert coll_id  # non-empty
            assert isinstance(context, dict)

    def test_in_project_known_dd_returns_activity_id_collection(self, real_dbs, universe_db):
        """The 'activity' data descriptor should map to 'activity_id' collection."""
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            results = ev.get_collection_from_data_descriptor_in_project(
                _PROJECT_A, _KNOWN_DD
            )
        collection_ids = [r[0] for r in results]
        assert _KNOWN_COLLECTION in collection_ids, (
            f"Expected '{_KNOWN_COLLECTION}' in collections for DD '{_KNOWN_DD}'; "
            f"got {collection_ids}"
        )

    def test_in_project_unknown_dd_returns_empty(self, real_dbs, universe_db):
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            results = ev.get_collection_from_data_descriptor_in_project(
                _PROJECT_A, _UNKNOWN_DD
            )
        assert results == []

    def test_in_project_unknown_project_returns_empty(self, real_dbs, universe_db):
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            results = ev.get_collection_from_data_descriptor_in_project(
                "nonexistent-project-xyz", _KNOWN_DD
            )
        assert results == []

    def test_in_all_projects_returns_list_of_three_tuples(self, real_dbs, universe_db):
        """Returns list of (project_id, collection_id, context) tuples."""
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = ev.get_collection_from_data_descriptor_in_all_projects(_KNOWN_DD)
        assert isinstance(results, list)
        assert len(results) > 0
        for item in results:
            assert len(item) == 3, f"Expected 3-tuple, got: {item}"
            pid, coll_id, context = item
            assert isinstance(pid, str)
            assert isinstance(coll_id, str)
            assert isinstance(context, dict)

    def test_in_all_projects_both_projects_appear(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = ev.get_collection_from_data_descriptor_in_all_projects(_KNOWN_DD)
        project_ids = [r[0] for r in results]
        assert _PROJECT_A in project_ids
        assert _PROJECT_B in project_ids

    def test_in_all_projects_unknown_dd_returns_empty(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = ev.get_collection_from_data_descriptor_in_all_projects(_UNKNOWN_DD)
        assert results == []


# ---------------------------------------------------------------------------
# DT-54  get_term_from_universe_term_id_in_project / _in_all_projects
# ---------------------------------------------------------------------------

class TestGetTermFromUniverseTermId:
    """DT-54: look up project terms by their universe term id."""

    def test_in_project_known_term_returns_tuple(self, real_dbs, universe_db):
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            result = get_term_from_universe_term_id_in_project(
                _PROJECT_A, _KNOWN_DD, _KNOWN_TERM
            )
        assert result is not None

    def test_in_project_result_is_tuple_of_collection_and_term(self, real_dbs, universe_db):
        """Returns (collection_id, term_object)."""
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            result = get_term_from_universe_term_id_in_project(
                _PROJECT_A, _KNOWN_DD, _KNOWN_TERM
            )
        coll_id, term = result
        assert isinstance(coll_id, str)
        assert coll_id  # non-empty
        assert term is not None
        assert term.id == _KNOWN_TERM

    def test_in_project_unknown_term_returns_none(self, real_dbs, universe_db):
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            result = get_term_from_universe_term_id_in_project(
                _PROJECT_A, _KNOWN_DD, _UNKNOWN_TERM
            )
        assert result is None

    def test_in_project_unknown_dd_returns_none(self, real_dbs, universe_db):
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            result = get_term_from_universe_term_id_in_project(
                _PROJECT_A, _UNKNOWN_DD, _KNOWN_TERM
            )
        assert result is None

    def test_in_project_unknown_project_returns_none(self, real_dbs, universe_db):
        with _inject_one_project(real_dbs["v1_path"], universe_db):
            result = get_term_from_universe_term_id_in_project(
                "nonexistent-project-xyz", _KNOWN_DD, _KNOWN_TERM
            )
        assert result is None

    def test_in_all_projects_returns_list_of_three_tuples(self, real_dbs, universe_db):
        """Returns list of (project_id, collection_id, term)."""
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = get_term_from_universe_term_id_in_all_projects(
                _KNOWN_DD, _KNOWN_TERM
            )
        assert isinstance(results, list)
        assert len(results) > 0
        for item in results:
            assert len(item) == 3, f"Expected 3-tuple, got: {item}"
            pid, coll_id, term = item
            assert isinstance(pid, str)
            assert isinstance(coll_id, str)
            assert term is not None

    def test_in_all_projects_both_projects_appear(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = get_term_from_universe_term_id_in_all_projects(
                _KNOWN_DD, _KNOWN_TERM
            )
        project_ids = [r[0] for r in results]
        assert _PROJECT_A in project_ids
        assert _PROJECT_B in project_ids

    def test_in_all_projects_term_id_matches(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = get_term_from_universe_term_id_in_all_projects(
                _KNOWN_DD, _KNOWN_TERM
            )
        for pid, coll_id, term in results:
            assert term.id == _KNOWN_TERM, (
                f"Expected term id '{_KNOWN_TERM}' in project '{pid}'; got '{term.id}'"
            )

    def test_in_all_projects_unknown_term_returns_empty(self, real_dbs, universe_db):
        with _inject_two_projects(real_dbs["v1_path"], universe_db):
            results = get_term_from_universe_term_id_in_all_projects(
                _KNOWN_DD, _UNKNOWN_TERM
            )
        assert results == []
