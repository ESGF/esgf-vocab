"""
Dev Tier — Python API integration tests with real built databases.

After building real project and universe DBs (via the session fixtures in
tests/integration/conftest.py), this module temporarily injects them into
``service.current_state`` and verifies the ``esgvoc.api`` module returns
correct data end-to-end.

The injection uses a context manager that replaces the global service state
with a minimal ``SimpleNamespace`` carrying the real ``DBConnection`` objects,
then restores the original state on exit — the same pattern used internally by
``_admin_context`` in ``esgvoc.admin.builder``.

Plan scenarios covered:
  DT-11  get_all_projects returns the injected project id
  DT-12  get_all_collections_in_project returns a non-empty list
  DT-13  get_all_terms_in_collection returns terms from a known collection
  DT-14  get_term_in_project returns the correct term for a known id
  DT-15  get_project returns project specs from the built DB
  DT-16  API functions return None/empty gracefully for unknown project
  DT-17  Universe API functions work when universe DB is injected
  DT-18  valid_term_in_collection validates a known value correctly
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
# Constants for the CMIP6 test project
# ---------------------------------------------------------------------------

_PROJECT_ID = "cmip6"
_KNOWN_COLLECTION = "activity_id"     # plain-term collection, no universe needed
_KNOWN_TERM = "aerchemmip"            # term id in activity_id
_KNOWN_TERM_DRS_NAME = "AerChemMIP"  # drs_name for aerchemmip (used for validation)
_UNKNOWN_PROJECT = "nonexistent-xyz"


# ---------------------------------------------------------------------------
# Context manager: inject real DBs into service.current_state
# ---------------------------------------------------------------------------

@contextmanager
def _inject_dbs(
    project_id: str,
    project_db: Path,
    universe_db: Path | None = None,
):
    """
    Temporarily override ``service.current_state`` to point at real DB files.

    The injected state carries the minimal structure the API needs:
      - ``current_state.projects[project_id].db_connection``
      - ``current_state.universe.db_connection``

    Both connections are properly disposed when the context exits.
    """
    original = svc.current_state

    project_conn = DBConnection(db_file_path=project_db)
    fake_project = SimpleNamespace(db_connection=project_conn)

    if universe_db and universe_db.exists():
        universe_conn = DBConnection(db_file_path=universe_db)
    else:
        universe_conn = None
    fake_universe = SimpleNamespace(db_connection=universe_conn)

    svc.current_state = SimpleNamespace(
        projects={project_id: fake_project},
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
# DT-11  get_all_projects
# ---------------------------------------------------------------------------

class TestGetProjectsAPI:
    """DT-11 / DT-15: project-level API functions work with injected DB."""

    def test_get_all_projects_includes_injected_project(self, real_dbs):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            projects = ev.get_all_projects()
        assert _PROJECT_ID in projects

    def test_get_all_projects_does_not_include_other_project(self, real_dbs):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            projects = ev.get_all_projects()
        assert _UNKNOWN_PROJECT not in projects

    def test_get_project_returns_specs_object(self, real_dbs):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            specs = ev.get_project(_PROJECT_ID)
        assert specs is not None

    def test_get_project_unknown_returns_none(self, real_dbs):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            specs = ev.get_project(_UNKNOWN_PROJECT)
        assert specs is None


# ---------------------------------------------------------------------------
# DT-12  get_all_collections_in_project
# ---------------------------------------------------------------------------

class TestGetCollectionsAPI:
    """DT-12: collections list from real built project DB."""

    def test_collections_list_is_nonempty(self, real_dbs):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            collections = ev.get_all_collections_in_project(_PROJECT_ID)
        assert len(collections) > 0

    def test_known_collection_is_present(self, real_dbs):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            collections = ev.get_all_collections_in_project(_PROJECT_ID)
        assert _KNOWN_COLLECTION in collections

    def test_unknown_project_returns_empty_list(self, real_dbs):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            collections = ev.get_all_collections_in_project(_UNKNOWN_PROJECT)
        assert collections == []

    def test_both_db_versions_return_same_collections(self, real_dbs):
        """Same repo HEAD → identical collection lists in both built DBs."""
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            cols_v1 = ev.get_all_collections_in_project(_PROJECT_ID)
        with _inject_dbs(_PROJECT_ID, real_dbs["v2_path"]):
            cols_v2 = ev.get_all_collections_in_project(_PROJECT_ID)
        assert sorted(cols_v1) == sorted(cols_v2)


# ---------------------------------------------------------------------------
# DT-13  get_all_terms_in_collection
# ---------------------------------------------------------------------------

class TestGetTermsInCollectionAPI:
    """DT-13: term retrieval from a real collection."""

    def test_get_all_terms_in_known_collection_is_nonempty(self, real_dbs):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        assert len(terms) > 0

    def test_all_terms_have_non_empty_id(self, real_dbs):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        for term in terms:
            assert hasattr(term, "id")
            assert term.id

    def test_unknown_collection_returns_empty_list(self, real_dbs):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, "nonexistent-collection")
        assert terms == []

    def test_term_count_same_across_db_versions(self, real_dbs):
        """Same repo HEAD → same number of terms in both built DB versions."""
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            terms_v1 = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        with _inject_dbs(_PROJECT_ID, real_dbs["v2_path"]):
            terms_v2 = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        assert len(terms_v1) == len(terms_v2)


# ---------------------------------------------------------------------------
# DT-14  get_term_in_project
# ---------------------------------------------------------------------------

class TestGetTermInProjectAPI:
    """DT-14: individual term retrieval from real built DB."""

    def test_get_known_term_returns_object(self, real_dbs):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            term = ev.get_term_in_project(_PROJECT_ID, _KNOWN_TERM)
        assert term is not None

    def test_term_id_matches_requested_id(self, real_dbs):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            term = ev.get_term_in_project(_PROJECT_ID, _KNOWN_TERM)
        assert term.id == _KNOWN_TERM

    def test_unknown_term_returns_none(self, real_dbs):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            term = ev.get_term_in_project(_PROJECT_ID, "nonexistent-term-xyz-abc")
        assert term is None

    def test_unknown_project_returns_none(self, real_dbs):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"]):
            term = ev.get_term_in_project(_UNKNOWN_PROJECT, _KNOWN_TERM)
        assert term is None

    def test_same_term_accessible_from_v2_db(self, real_dbs):
        """Same git content → same term present in both v1 and v2 builds."""
        with _inject_dbs(_PROJECT_ID, real_dbs["v2_path"]):
            term = ev.get_term_in_project(_PROJECT_ID, _KNOWN_TERM)
        assert term is not None
        assert term.id == _KNOWN_TERM


# ---------------------------------------------------------------------------
# DT-17  Universe API (requires universe_db fixture)
# ---------------------------------------------------------------------------

class TestUniverseAPI:
    """DT-17: Universe API functions work when a real universe DB is injected."""

    def test_get_all_terms_in_universe_is_nonempty(self, real_dbs, universe_db):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_universe()
        assert len(terms) > 0

    def test_get_all_data_descriptors_is_nonempty(self, real_dbs, universe_db):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"], universe_db):
            dds = ev.get_all_data_descriptors_in_universe()
        assert len(dds) > 0

    def test_universe_terms_have_ids(self, real_dbs, universe_db):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_universe()
        for term in terms:
            assert hasattr(term, "id")
            assert term.id


# ---------------------------------------------------------------------------
# DT-18  valid_term_in_collection (requires universe_db for non-plain terms;
#         activity_id is PLAIN so only project DB needed at runtime, but the
#         API still opens a universe session — must not be None)
# ---------------------------------------------------------------------------

class TestValidationAPI:
    """DT-18: validation API functions with real DBs."""

    def test_valid_term_in_collection_known_drs_name_matches(self, real_dbs, universe_db):
        # Validation matches on drs_name (not term id): aerchemmip → drs_name "AerChemMIP"
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_collection(
                _KNOWN_TERM_DRS_NAME, _PROJECT_ID, _KNOWN_COLLECTION
            )
        assert len(matches) > 0
        assert any(m.term_id == _KNOWN_TERM for m in matches)

    def test_valid_term_in_collection_unknown_value_is_empty(self, real_dbs, universe_db):
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_collection(
                "totally-unknown-value-xyz", _PROJECT_ID, _KNOWN_COLLECTION
            )
        assert matches == []

    def test_valid_term_in_project_known_drs_name_returns_matches(self, real_dbs, universe_db):
        # valid_term_in_project searches all collections; drs_name "AerChemMIP" → aerchemmip
        with _inject_dbs(_PROJECT_ID, real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_project(_KNOWN_TERM_DRS_NAME, _PROJECT_ID)
        assert isinstance(matches, list)
        assert len(matches) > 0
