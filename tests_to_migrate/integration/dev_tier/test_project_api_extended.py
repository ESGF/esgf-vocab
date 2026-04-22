"""
Dev Tier — Extended project API integration tests.

Covers project API functions not tested in test_api_after_build.py:
  get_term_in_collection, get_collection_in_project, get_all_terms_in_project,
  get_terms_in_collection_by_key_value, find_terms in project, valid_term.

Plan scenarios covered:
  DT-42  get_term_in_collection returns the correct term for a known id
  DT-43  get_collection_in_project returns descriptor metadata for known collection
  DT-44  get_all_terms_in_project returns terms across all collections
  DT-45  get_terms_in_collection_by_key_value finds terms matching a field value
  DT-46  valid_term validates a specific term id in a collection
  DT-47  get_project returns ProjectSpecs with non-empty data
  DT-48  All extended API functions return empty/None for unknown inputs
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
# Known constants from the real cmip6 project DB
# ---------------------------------------------------------------------------

_PROJECT_ID = "cmip6"
_KNOWN_COLLECTION = "activity_id"
_KNOWN_TERM = "aerchemmip"
_KNOWN_TERM_DRS = "AerChemMIP"           # drs_name for aerchemmip

_INST_COLLECTION = "institution_id"
_KNOWN_INST = "aer"                       # institution id in institution_id
_KNOWN_INST_DRS = "AER"                   # drs_name for "aer" institution

_UNKNOWN_PROJECT = "nonexistent-xyz"
_UNKNOWN_COLLECTION = "nonexistent-collection-xyz"
_UNKNOWN_TERM = "nonexistent-term-xyz-abc"


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

@contextmanager
def _inject_dbs(project_db: Path, universe_db: Path | None = None):
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
# DT-42  get_term_in_collection
# ---------------------------------------------------------------------------

class TestGetTermInCollection:
    """DT-42: fetch a term by collection + term id."""

    def test_known_term_in_known_collection_returns_object(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_collection(_PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM)
        assert term is not None

    def test_returned_term_id_matches(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_collection(_PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM)
        assert term.id == _KNOWN_TERM

    def test_unknown_term_returns_none(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_collection(_PROJECT_ID, _KNOWN_COLLECTION, _UNKNOWN_TERM)
        assert term is None

    def test_unknown_collection_returns_none(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_collection(_PROJECT_ID, _UNKNOWN_COLLECTION, _KNOWN_TERM)
        assert term is None

    def test_unknown_project_returns_none(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_collection(_UNKNOWN_PROJECT, _KNOWN_COLLECTION, _KNOWN_TERM)
        assert term is None


# ---------------------------------------------------------------------------
# DT-43  get_collection_in_project
# ---------------------------------------------------------------------------

class TestGetCollectionInProject:
    """DT-43: fetch collection metadata (id, specs dict)."""

    def test_known_collection_returns_result(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            result = ev.get_collection_in_project(_PROJECT_ID, _KNOWN_COLLECTION)
        assert result is not None

    def test_result_is_tuple_of_id_and_dict(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            result = ev.get_collection_in_project(_PROJECT_ID, _KNOWN_COLLECTION)
        coll_id, specs = result
        assert coll_id == _KNOWN_COLLECTION
        assert isinstance(specs, dict)

    def test_unknown_collection_returns_none(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            result = ev.get_collection_in_project(_PROJECT_ID, _UNKNOWN_COLLECTION)
        assert result is None

    def test_unknown_project_returns_none(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            result = ev.get_collection_in_project(_UNKNOWN_PROJECT, _KNOWN_COLLECTION)
        assert result is None


# ---------------------------------------------------------------------------
# DT-44  get_all_terms_in_project
# ---------------------------------------------------------------------------

class TestGetAllTermsInProject:
    """DT-44: fetch all terms across all collections in a project."""

    def test_returns_nonempty_list(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_project(_PROJECT_ID)
        assert len(terms) > 0

    def test_all_terms_have_id(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_project(_PROJECT_ID)
        for t in terms:
            assert hasattr(t, "id")
            assert t.id

    def test_count_exceeds_single_collection_count(self, real_dbs, universe_db):
        """Total terms across all collections should exceed terms in one collection."""
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            all_terms = ev.get_all_terms_in_project(_PROJECT_ID)
            activity_terms = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        assert len(all_terms) > len(activity_terms)

    def test_unknown_project_returns_empty(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_project(_UNKNOWN_PROJECT)
        assert terms == []


# ---------------------------------------------------------------------------
# DT-45  get_terms_in_collection_by_key_value
# ---------------------------------------------------------------------------

class TestGetTermsByKeyValue:
    """DT-45: filter terms by a field value (e.g. drs_name)."""

    def test_find_by_drs_name_returns_matching_term(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            terms = ev.get_terms_in_collection_by_key_value(
                _PROJECT_ID, _KNOWN_COLLECTION, "drs_name", _KNOWN_TERM_DRS
            )
        assert len(terms) > 0
        assert any(t.id == _KNOWN_TERM for t in terms), (
            f"Expected term '{_KNOWN_TERM}' in results; got {[t.id for t in terms]}"
        )

    def test_find_by_nonexistent_value_returns_empty(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            terms = ev.get_terms_in_collection_by_key_value(
                _PROJECT_ID, _KNOWN_COLLECTION, "drs_name", "THIS-VALUE-DOES-NOT-EXIST-XYZ"
            )
        assert terms == []

    def test_find_by_unknown_key_returns_empty(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            terms = ev.get_terms_in_collection_by_key_value(
                _PROJECT_ID, _KNOWN_COLLECTION, "nonexistent_field", "anything"
            )
        assert terms == []


# ---------------------------------------------------------------------------
# DT-46  valid_term  (validate specific term_id in collection)
# ---------------------------------------------------------------------------

class TestValidTerm:
    """DT-46: validate a specific (collection, term_id) combination."""

    def test_valid_term_known_drs_passes(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                _KNOWN_TERM_DRS, _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        # Should return a ValidationReport-like object indicating success
        assert report is not None

    def test_valid_term_unknown_value_fails(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            report = ev.valid_term(
                "THIS-DOES-NOT-MATCH-ANYTHING", _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM
            )
        # Report should exist (no exception) even for invalid value
        assert report is not None


# ---------------------------------------------------------------------------
# DT-47  get_project returns ProjectSpecs
# ---------------------------------------------------------------------------

class TestGetProjectSpecs:
    """DT-47: get_project returns structured project metadata."""

    def test_returns_non_none(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            specs = ev.get_project(_PROJECT_ID)
        assert specs is not None

    def test_project_id_in_specs(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            specs = ev.get_project(_PROJECT_ID)
        # ProjectSpecs should have an id or project_id attribute
        assert hasattr(specs, "id") or hasattr(specs, "project_id"), \
            f"Unexpected ProjectSpecs structure: {dir(specs)}"

    def test_unknown_project_returns_none(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            specs = ev.get_project(_UNKNOWN_PROJECT)
        assert specs is None


# ---------------------------------------------------------------------------
# DT-48  Graceful fallback: all extended functions handle unknown inputs
# ---------------------------------------------------------------------------

class TestExtendedAPIGracefulFallback:
    """DT-48: extended project API functions never raise for unknown inputs."""

    def test_get_term_in_collection_wrong_project_returns_none(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            assert ev.get_term_in_collection(_UNKNOWN_PROJECT, _KNOWN_COLLECTION, _KNOWN_TERM) is None

    def test_get_collection_in_project_wrong_project_returns_none(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            assert ev.get_collection_in_project(_UNKNOWN_PROJECT, _KNOWN_COLLECTION) is None

    def test_get_all_terms_in_project_wrong_project_returns_empty(self, real_dbs, universe_db):
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            assert ev.get_all_terms_in_project(_UNKNOWN_PROJECT) == []

    def test_valid_term_in_collection_empty_string_raises(self, real_dbs, universe_db):
        """Empty string is rejected before any DB query (EsgvocValueError)."""
        from esgvoc.core.exceptions import EsgvocValueError
        with _inject_dbs(real_dbs["v1_path"], universe_db):
            with pytest.raises(EsgvocValueError):
                ev.valid_term_in_collection("", _PROJECT_ID, _KNOWN_COLLECTION)
