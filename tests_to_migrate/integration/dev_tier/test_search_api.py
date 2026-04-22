"""
Dev Tier — Search/FTS API integration tests.

Covers the remaining full-text-search functions not exercised in other test files:
  find_items_in_universe, find_items_in_project,
  find_collections_in_project, find_terms_in_collection.
Also tests limit/offset pagination and the Item return type.

Plan scenarios covered:
  DT-55  find_items_in_universe returns both terms and data-descriptors
  DT-56  find_items_in_project returns both terms and collections
  DT-57  find_collections_in_project performs FTS on collection IDs
  DT-58  find_terms_in_collection narrows FTS to one collection
  DT-59  Pagination: limit and offset reduce result sizes
  DT-60  All search functions return empty list for nonsense expressions
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
# Known constants from real DBs
# ---------------------------------------------------------------------------

_PROJECT_ID = "cmip6"
_KNOWN_COLLECTION = "activity_id"
_KNOWN_TERM = "aerchemmip"        # id of a known term in activity_id
_KNOWN_DD = "activity"            # data descriptor id in universe
_UNKNOWN_EXPR = "xyzxyz_no_match_abc999"


# ---------------------------------------------------------------------------
# Context managers (same pattern as other dev_tier tests)
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


@contextmanager
def _inject_universe_only(universe_db: Path):
    original = svc.current_state
    universe_conn = DBConnection(db_file_path=universe_db)
    svc.current_state = SimpleNamespace(
        projects={},
        universe=SimpleNamespace(db_connection=universe_conn),
    )
    try:
        yield
    finally:
        universe_conn.engine.dispose()
        svc.current_state = original


# ---------------------------------------------------------------------------
# DT-55  find_items_in_universe
# ---------------------------------------------------------------------------

class TestFindItemsInUniverse:
    """DT-55: find_items_in_universe returns both terms and data-descriptors."""

    def test_known_term_returns_results(self, universe_db):
        with _inject_universe_only(universe_db):
            items = ev.find_items_in_universe(_KNOWN_TERM)
        assert len(items) > 0

    def test_known_dd_id_returns_results(self, universe_db):
        with _inject_universe_only(universe_db):
            items = ev.find_items_in_universe(_KNOWN_DD)
        assert len(items) > 0

    def test_result_items_have_id_kind_parent_id(self, universe_db):
        with _inject_universe_only(universe_db):
            items = ev.find_items_in_universe(_KNOWN_TERM)
        for item in items:
            assert hasattr(item, "id"), "Item should have 'id'"
            assert hasattr(item, "kind"), "Item should have 'kind'"
            assert hasattr(item, "parent_id"), "Item should have 'parent_id'"
            assert item.id

    def test_result_contains_term_kind(self, universe_db):
        """At least one result should be a 'term' kind."""
        from esgvoc.api.search import ItemKind
        with _inject_universe_only(universe_db):
            items = ev.find_items_in_universe(_KNOWN_TERM)
        kinds = {item.kind for item in items}
        assert ItemKind.TERM in kinds, f"Expected TERM kind in results; got {kinds}"

    def test_nonsense_returns_empty(self, universe_db):
        with _inject_universe_only(universe_db):
            items = ev.find_items_in_universe(_UNKNOWN_EXPR)
        assert items == []

    def test_empty_string_raises_value_error(self, universe_db):
        from esgvoc.core.exceptions import EsgvocValueError
        with _inject_universe_only(universe_db):
            with pytest.raises(EsgvocValueError):
                ev.find_items_in_universe("")

    def test_only_id_mode_returns_results(self, universe_db):
        """only_id=True searches IDs only — should still find the known term."""
        with _inject_universe_only(universe_db):
            items = ev.find_items_in_universe(_KNOWN_TERM, only_id=True)
        assert len(items) > 0


# ---------------------------------------------------------------------------
# DT-56  find_items_in_project
# ---------------------------------------------------------------------------

class TestFindItemsInProject:
    """DT-56: find_items_in_project returns both terms and collections."""

    def test_known_term_returns_results(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            items = ev.find_items_in_project(_KNOWN_TERM, _PROJECT_ID)
        assert len(items) > 0

    def test_known_collection_id_returns_results(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            items = ev.find_items_in_project(_KNOWN_COLLECTION, _PROJECT_ID)
        assert len(items) > 0

    def test_result_items_have_id_kind_parent_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            items = ev.find_items_in_project(_KNOWN_TERM, _PROJECT_ID)
        for item in items:
            assert hasattr(item, "id")
            assert hasattr(item, "kind")
            assert hasattr(item, "parent_id")
            assert item.id

    def test_result_contains_term_kind(self, real_dbs, universe_db):
        from esgvoc.api.search import ItemKind
        with _inject(real_dbs["v1_path"], universe_db):
            items = ev.find_items_in_project(_KNOWN_TERM, _PROJECT_ID)
        kinds = {item.kind for item in items}
        assert ItemKind.TERM in kinds

    def test_unknown_project_returns_empty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            items = ev.find_items_in_project(_KNOWN_TERM, "nonexistent-project-xyz")
        assert items == []

    def test_nonsense_expression_returns_empty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            items = ev.find_items_in_project(_UNKNOWN_EXPR, _PROJECT_ID)
        assert items == []

    def test_empty_string_raises_value_error(self, real_dbs, universe_db):
        from esgvoc.core.exceptions import EsgvocValueError
        with _inject(real_dbs["v1_path"], universe_db):
            with pytest.raises(EsgvocValueError):
                ev.find_items_in_project("", _PROJECT_ID)


# ---------------------------------------------------------------------------
# DT-57  find_collections_in_project
# ---------------------------------------------------------------------------

class TestFindCollectionsInProject:
    """DT-57: find_collections_in_project performs FTS on collection IDs."""

    def test_known_collection_id_returns_results(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            results = ev.find_collections_in_project(_KNOWN_COLLECTION, _PROJECT_ID)
        assert len(results) > 0

    def test_result_is_list_of_id_context_tuples(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            results = ev.find_collections_in_project(_KNOWN_COLLECTION, _PROJECT_ID)
        for coll_id, context in results:
            assert isinstance(coll_id, str)
            assert coll_id
            assert isinstance(context, dict)

    def test_known_collection_found_in_results(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            results = ev.find_collections_in_project(_KNOWN_COLLECTION, _PROJECT_ID)
        coll_ids = [r[0] for r in results]
        assert _KNOWN_COLLECTION in coll_ids, (
            f"Expected '{_KNOWN_COLLECTION}' in {coll_ids[:5]}"
        )

    def test_unknown_project_returns_empty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            results = ev.find_collections_in_project(_KNOWN_COLLECTION, "nonexistent-xyz")
        assert results == []

    def test_nonsense_expression_returns_empty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            results = ev.find_collections_in_project(_UNKNOWN_EXPR, _PROJECT_ID)
        assert results == []

    def test_empty_string_raises_value_error(self, real_dbs, universe_db):
        from esgvoc.core.exceptions import EsgvocValueError
        with _inject(real_dbs["v1_path"], universe_db):
            with pytest.raises(EsgvocValueError):
                ev.find_collections_in_project("", _PROJECT_ID)


# ---------------------------------------------------------------------------
# DT-58  find_terms_in_collection
# ---------------------------------------------------------------------------

class TestFindTermsInCollection:
    """DT-58: find_terms_in_collection narrows FTS to one collection."""

    def test_known_term_found_in_its_collection(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.find_terms_in_collection(
                _KNOWN_TERM, _PROJECT_ID, _KNOWN_COLLECTION
            )
        assert len(terms) > 0

    def test_returned_term_has_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.find_terms_in_collection(
                _KNOWN_TERM, _PROJECT_ID, _KNOWN_COLLECTION
            )
        for t in terms:
            assert hasattr(t, "id")
            assert t.id

    def test_known_term_id_in_results(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.find_terms_in_collection(
                _KNOWN_TERM, _PROJECT_ID, _KNOWN_COLLECTION
            )
        ids = [t.id for t in terms]
        assert _KNOWN_TERM in ids, f"Expected '{_KNOWN_TERM}' in {ids[:5]}"

    def test_wrong_collection_returns_empty(self, real_dbs, universe_db):
        """Searching for an activity term in a different collection → empty."""
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.find_terms_in_collection(
                _KNOWN_TERM, _PROJECT_ID, "institution_id"
            )
        assert terms == []

    def test_unknown_collection_returns_empty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.find_terms_in_collection(
                _KNOWN_TERM, _PROJECT_ID, "nonexistent-collection-xyz"
            )
        assert terms == []

    def test_unknown_project_returns_empty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.find_terms_in_collection(
                _KNOWN_TERM, "nonexistent-project-xyz", _KNOWN_COLLECTION
            )
        assert terms == []

    def test_nonsense_expression_returns_empty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.find_terms_in_collection(
                _UNKNOWN_EXPR, _PROJECT_ID, _KNOWN_COLLECTION
            )
        assert terms == []


# ---------------------------------------------------------------------------
# DT-59  Pagination: limit and offset
# ---------------------------------------------------------------------------

class TestPaginationLimitOffset:
    """DT-59: limit and offset parameters control result page size."""

    def test_limit_reduces_universe_results(self, universe_db):
        """With limit=1, at most one result is returned."""
        with _inject_universe_only(universe_db):
            all_items = ev.find_items_in_universe(_KNOWN_TERM)
            limited = ev.find_items_in_universe(_KNOWN_TERM, limit=1)
        if len(all_items) > 1:
            assert len(limited) == 1, (
                f"Expected 1 result with limit=1; got {len(limited)}"
            )
        else:
            assert len(limited) <= 1

    def test_offset_shifts_universe_results(self, universe_db):
        """With offset=1, results differ from no-offset (assuming ≥2 hits)."""
        with _inject_universe_only(universe_db):
            all_items = ev.find_terms_in_universe(_KNOWN_DD)
            offset_items = ev.find_terms_in_universe(_KNOWN_DD, offset=1)
        if len(all_items) > 1:
            assert len(offset_items) == len(all_items) - 1

    def test_limit_reduces_project_results(self, real_dbs, universe_db):
        """find_terms_in_project with limit=1 returns at most 1 result."""
        with _inject(real_dbs["v1_path"], universe_db):
            all_terms = ev.find_terms_in_project(_PROJECT_ID, "activity")
            limited = ev.find_terms_in_project(_PROJECT_ID, "activity", limit=1)
        if len(all_terms) > 1:
            assert len(limited) == 1

    def test_limit_reduces_collection_results(self, real_dbs, universe_db):
        """find_terms_in_collection with limit=1 returns at most 1 result."""
        with _inject(real_dbs["v1_path"], universe_db):
            limited = ev.find_terms_in_collection(
                "a", _PROJECT_ID, _KNOWN_COLLECTION, limit=1
            )
        assert len(limited) <= 1


# ---------------------------------------------------------------------------
# DT-60  All search functions return empty for nonsense expressions
# ---------------------------------------------------------------------------

class TestSearchGracefulFallback:
    """DT-60: All search API functions handle no-match gracefully (no exceptions)."""

    def test_find_items_in_universe_nonsense(self, universe_db):
        with _inject_universe_only(universe_db):
            assert ev.find_items_in_universe(_UNKNOWN_EXPR) == []

    def test_find_items_in_project_nonsense(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            assert ev.find_items_in_project(_UNKNOWN_EXPR, _PROJECT_ID) == []

    def test_find_collections_in_project_nonsense(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            assert ev.find_collections_in_project(_UNKNOWN_EXPR, _PROJECT_ID) == []

    def test_find_terms_in_collection_nonsense(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            assert ev.find_terms_in_collection(
                _UNKNOWN_EXPR, _PROJECT_ID, _KNOWN_COLLECTION
            ) == []

    def test_find_terms_in_universe_nonsense(self, universe_db):
        with _inject_universe_only(universe_db):
            assert ev.find_terms_in_universe(_UNKNOWN_EXPR) == []

    def test_find_terms_in_project_nonsense(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            assert ev.find_terms_in_project(_PROJECT_ID, _UNKNOWN_EXPR) == []
