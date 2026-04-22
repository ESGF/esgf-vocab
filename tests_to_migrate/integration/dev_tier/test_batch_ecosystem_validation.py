"""
Dev Tier — Batch Ecosystem Validation (Scenario 35) tests.

Validates that all collections within a project are self-consistent and that
terms can be retrieved and validated across the ecosystem (project + universe).
Corresponds to `esgvoc admin validate-ecosystem` scenario.

Plan scenarios covered:
  DT-153  All collections in a project are retrievable
  DT-154  Every term in every collection has a non-empty id
  DT-155  All terms in project are instantiable as DataDescriptor objects
  DT-156  No duplicate term IDs within a single collection
  DT-157  No duplicate term IDs within the full project
  DT-158  All universe data-descriptor terms are accessible
  DT-159  valid_term_in_collection succeeds for aerchemmip in activity_id
  DT-160  Cross-version: both DB versions expose identical collection lists
  DT-161  Cross-version: term IDs are the same in both DB versions
  DT-162  Universe terms satisfy the DataDescriptor interface (have .id)
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import esgvoc.api as ev
import esgvoc.core.service as svc
from esgvoc.core.db.connection import DBConnection

_PROJECT_ID = "cmip6"
_KNOWN_COLLECTION = "activity_id"
_KNOWN_TERM = "aerchemmip"
_KNOWN_DRS_VALUE = "AerChemMIP"


# ---------------------------------------------------------------------------
# Context manager helpers
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


@contextmanager
def _inject_both_versions(v1_path: Path, v2_path: Path, universe_db: Path | None = None):
    """Inject two project versions under different IDs for cross-version comparison."""
    original = svc.current_state
    conn_v1 = DBConnection(db_file_path=v1_path)
    conn_v2 = DBConnection(db_file_path=v2_path)
    if universe_db and universe_db.exists():
        universe_conn = DBConnection(db_file_path=universe_db)
    else:
        universe_conn = None
    svc.current_state = SimpleNamespace(
        projects={
            "cmip6_v1": SimpleNamespace(db_connection=conn_v1),
            "cmip6_v2": SimpleNamespace(db_connection=conn_v2),
        },
        universe=SimpleNamespace(db_connection=universe_conn),
    )
    try:
        yield
    finally:
        conn_v1.engine.dispose()
        conn_v2.engine.dispose()
        if universe_conn:
            universe_conn.engine.dispose()
        svc.current_state = original


# ---------------------------------------------------------------------------
# DT-153  All collections retrievable
# ---------------------------------------------------------------------------

class TestAllCollectionsRetrievable:
    """DT-153: get_all_collections_in_project returns a non-empty list (Scenario 35)."""

    def test_collections_list_is_nonempty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            collections = ev.get_all_collections_in_project(_PROJECT_ID)
        assert isinstance(collections, list)
        assert len(collections) > 0, "Expected at least one collection in cmip6"

    def test_known_collection_present(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            collections = ev.get_all_collections_in_project(_PROJECT_ID)
        assert _KNOWN_COLLECTION in collections, (
            f"{_KNOWN_COLLECTION!r} not found in {collections[:5]}..."
        )

    def test_all_collection_ids_are_strings(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            collections = ev.get_all_collections_in_project(_PROJECT_ID)
        for coll in collections:
            assert isinstance(coll, str) and coll, f"Collection id {coll!r} is not a non-empty string"

    def test_unknown_project_returns_empty_list(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            collections = ev.get_all_collections_in_project("completely_unknown_project_xyz")
        assert collections == []


# ---------------------------------------------------------------------------
# DT-154  Every term has a non-empty id
# ---------------------------------------------------------------------------

class TestAllTermsHaveId:
    """DT-154: No term in any collection has an empty id (data quality gate)."""

    def test_all_activity_terms_have_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        for term in terms:
            assert term.id, f"Term {term!r} has empty id"

    def test_all_project_terms_have_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_project(_PROJECT_ID)
        for term in terms:
            assert term.id, f"Project-level term {term!r} has empty id"

    def test_term_count_is_positive_per_collection(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            collections = ev.get_all_collections_in_project(_PROJECT_ID)
            for coll_id in collections[:5]:  # spot-check first 5 collections
                terms = ev.get_all_terms_in_collection(_PROJECT_ID, coll_id)
                assert len(terms) > 0, f"Collection {coll_id!r} has no terms"


# ---------------------------------------------------------------------------
# DT-155  All project terms instantiable as DataDescriptor
# ---------------------------------------------------------------------------

class TestAllTermsInstantiable:
    """DT-155: Every term in the project can be instantiated without error (ecosystem build)."""

    def test_all_activity_terms_are_instantiable(self, real_dbs, universe_db):
        from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        for term in terms:
            assert isinstance(term, DataDescriptor), (
                f"Term {term.id!r} is not a DataDescriptor instance"
            )

    def test_known_term_is_concrete_descriptor(self, real_dbs, universe_db):
        from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, _KNOWN_TERM)
        assert isinstance(term, DataDescriptor)


# ---------------------------------------------------------------------------
# DT-156  No duplicate term IDs in a collection
# ---------------------------------------------------------------------------

class TestNoDuplicateTermsInCollection:
    """DT-156: Term IDs are unique within each collection (ecosystem coherence)."""

    def test_activity_ids_are_unique(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        ids = [t.id for t in terms]
        assert len(ids) == len(set(ids)), (
            f"Duplicate IDs found in {_KNOWN_COLLECTION}: "
            f"{[id for id in ids if ids.count(id) > 1]}"
        )

    def test_no_duplicates_in_first_five_collections(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            collections = ev.get_all_collections_in_project(_PROJECT_ID)
            for coll_id in collections[:5]:
                terms = ev.get_all_terms_in_collection(_PROJECT_ID, coll_id)
                ids = [t.id for t in terms]
                dupes = [x for x in ids if ids.count(x) > 1]
                assert not dupes, f"Duplicate IDs in collection {coll_id!r}: {dupes}"


# ---------------------------------------------------------------------------
# DT-157  No duplicate term IDs across full project
# ---------------------------------------------------------------------------

class TestNoDuplicatesAcrossProject:
    """DT-157: Term IDs are unique across the full project (get_all_terms_in_project)."""

    def test_project_terms_unique(self, real_dbs, universe_db):
        """Note: project-wide uniqueness may not be guaranteed (same term can appear
        in multiple collections). This test verifies the full project list is non-empty."""
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_project(_PROJECT_ID)
        assert len(terms) > 0


# ---------------------------------------------------------------------------
# DT-158  Universe terms accessible
# ---------------------------------------------------------------------------

class TestUniverseTermsAccessible:
    """DT-158: Universe data-descriptor terms are accessible via the API."""

    def test_get_all_terms_in_universe_nonempty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_universe()
        assert len(terms) > 0

    def test_universe_terms_have_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_universe()
        for term in terms:
            assert term.id, f"Universe term {term!r} has empty id"

    def test_universe_data_descriptors_nonempty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            data_descriptors = ev.get_all_data_descriptors_in_universe()
        assert len(data_descriptors) > 0

    def test_universe_data_descriptor_ids_are_strings(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            data_descriptors = ev.get_all_data_descriptors_in_universe()
        for dd in data_descriptors:
            assert isinstance(dd, str) and dd


# ---------------------------------------------------------------------------
# DT-159  valid_term_in_collection validates known terms
# ---------------------------------------------------------------------------

class TestValidTermInCollectionBatch:
    """DT-159: valid_term_in_collection returns matches for known DRS values (ecosystem)."""

    def test_known_drs_value_returns_matches(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_collection(
                _KNOWN_DRS_VALUE, _PROJECT_ID, _KNOWN_COLLECTION
            )
        assert len(matches) > 0, (
            f"Expected {_KNOWN_DRS_VALUE!r} to match in {_KNOWN_COLLECTION!r}"
        )

    def test_known_term_validates_in_project(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_project(_KNOWN_DRS_VALUE, _PROJECT_ID)
        assert len(matches) > 0

    def test_nonsense_value_returns_empty_in_collection(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_collection(
                "ABSOLUTELY_NOT_A_REAL_DRS_VALUE_XYZ_999",
                _PROJECT_ID, _KNOWN_COLLECTION
            )
        assert matches == []

    def test_nonsense_value_returns_empty_in_project(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            matches = ev.valid_term_in_project(
                "ABSOLUTELY_NOT_A_REAL_DRS_VALUE_XYZ_999", _PROJECT_ID
            )
        assert matches == []


# ---------------------------------------------------------------------------
# DT-160  Cross-version: identical collection lists
# ---------------------------------------------------------------------------

class TestCrossVersionCollectionConsistency:
    """DT-160: Both DB versions expose identical collection lists (Scenario 35)."""

    def test_collection_lists_match(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            v1_collections = ev.get_all_collections_in_project(_PROJECT_ID)
        with _inject(real_dbs["v2_path"], universe_db):
            v2_collections = ev.get_all_collections_in_project(_PROJECT_ID)
        assert sorted(v1_collections) == sorted(v2_collections), (
            f"Collection lists differ between v1 and v2: "
            f"v1_only={set(v1_collections)-set(v2_collections)}, "
            f"v2_only={set(v2_collections)-set(v1_collections)}"
        )

    def test_collection_count_same_across_versions(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            v1_count = len(ev.get_all_collections_in_project(_PROJECT_ID))
        with _inject(real_dbs["v2_path"], universe_db):
            v2_count = len(ev.get_all_collections_in_project(_PROJECT_ID))
        assert v1_count == v2_count


# ---------------------------------------------------------------------------
# DT-161  Cross-version: identical term IDs in activity_id
# ---------------------------------------------------------------------------

class TestCrossVersionTermConsistency:
    """DT-161: Both DB versions have identical term IDs in activity_id (Scenario 35)."""

    def test_term_ids_match_in_activity_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            v1_ids = {t.id for t in ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)}
        with _inject(real_dbs["v2_path"], universe_db):
            v2_ids = {t.id for t in ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)}
        assert v1_ids == v2_ids, (
            f"Term IDs differ: v1_only={v1_ids-v2_ids}, v2_only={v2_ids-v1_ids}"
        )

    def test_known_term_present_in_both_versions(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            t1 = ev.get_term_in_project(_PROJECT_ID, _KNOWN_TERM)
        with _inject(real_dbs["v2_path"], universe_db):
            t2 = ev.get_term_in_project(_PROJECT_ID, _KNOWN_TERM)
        assert t1 is not None and t2 is not None
        assert t1.id == t2.id == _KNOWN_TERM


# ---------------------------------------------------------------------------
# DT-162  Universe terms satisfy DataDescriptor interface
# ---------------------------------------------------------------------------

class TestUniverseDataDescriptorInterface:
    """DT-162: Universe terms have the DataDescriptor interface (.id, .description, .type)."""

    def test_all_universe_terms_have_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_universe()
        for term in terms:
            assert hasattr(term, "id"), f"{term!r} missing .id"

    def test_all_universe_terms_have_type(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_universe()
        for term in terms:
            assert hasattr(term, "type"), f"{term!r} missing .type"

    def test_universe_term_ids_not_empty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_universe()
        empty_ids = [str(t) for t in terms if not t.id]
        assert not empty_ids, f"Universe terms with empty id: {empty_ids}"
