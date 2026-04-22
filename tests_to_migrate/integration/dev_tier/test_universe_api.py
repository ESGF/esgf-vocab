"""
Dev Tier — Universe API integration tests with real built databases.

Tests universe-specific API functions not covered by test_api_after_build.py.

Plan scenarios covered:
  DT-34  get_all_terms_in_data_descriptor returns terms for a known data descriptor
  DT-35  get_term_in_data_descriptor returns the correct term object
  DT-36  get_term_in_universe returns a term by id (cross-descriptor lookup)
  DT-37  get_data_descriptor_in_universe returns descriptor metadata
  DT-38  find_terms_in_universe performs full-text search, returns results
  DT-39  find_data_descriptors_in_universe returns matching descriptors
  DT-40  find_terms_in_data_descriptor narrows FTS to one data descriptor
  DT-41  All universe functions return empty / None for unknown inputs
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
# Known constants from the real WCRP-universe (activity data descriptor)
# ---------------------------------------------------------------------------

_KNOWN_DD = "activity"          # data descriptor id in universe
_KNOWN_TERM = "aerchemmip"      # term id in activity data descriptor
_UNKNOWN_DD = "nonexistent-descriptor-xyz"
_UNKNOWN_TERM = "nonexistent-term-xyz-abc"


# ---------------------------------------------------------------------------
# Context manager: inject universe DB only
# ---------------------------------------------------------------------------

@contextmanager
def _inject_universe(universe_db: Path):
    """
    Temporarily set service.current_state to expose only the universe DB.
    No project is registered — universe API functions should not need one.
    """
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
# DT-34  get_all_terms_in_data_descriptor
# ---------------------------------------------------------------------------

class TestGetAllTermsInDataDescriptor:
    """DT-34: terms from a specific universe data descriptor."""

    def test_known_dd_returns_nonempty_list(self, universe_db):
        with _inject_universe(universe_db):
            terms = ev.get_all_terms_in_data_descriptor(_KNOWN_DD)
        assert len(terms) > 0

    def test_all_terms_have_id(self, universe_db):
        with _inject_universe(universe_db):
            terms = ev.get_all_terms_in_data_descriptor(_KNOWN_DD)
        for t in terms:
            assert hasattr(t, "id")
            assert t.id

    def test_known_term_is_present_in_result(self, universe_db):
        with _inject_universe(universe_db):
            terms = ev.get_all_terms_in_data_descriptor(_KNOWN_DD)
        ids = [t.id for t in terms]
        assert _KNOWN_TERM in ids, \
            f"Expected '{_KNOWN_TERM}' in terms of '{_KNOWN_DD}'; got {ids[:5]}…"

    def test_unknown_dd_returns_empty_list(self, universe_db):
        with _inject_universe(universe_db):
            terms = ev.get_all_terms_in_data_descriptor(_UNKNOWN_DD)
        assert terms == []


# ---------------------------------------------------------------------------
# DT-35  get_term_in_data_descriptor
# ---------------------------------------------------------------------------

class TestGetTermInDataDescriptor:
    """DT-35: fetch a single term by data descriptor + term id."""

    def test_known_term_returns_object(self, universe_db):
        with _inject_universe(universe_db):
            term = ev.get_term_in_data_descriptor(_KNOWN_DD, _KNOWN_TERM)
        assert term is not None

    def test_term_id_matches(self, universe_db):
        with _inject_universe(universe_db):
            term = ev.get_term_in_data_descriptor(_KNOWN_DD, _KNOWN_TERM)
        assert term.id == _KNOWN_TERM

    def test_unknown_term_returns_none(self, universe_db):
        with _inject_universe(universe_db):
            term = ev.get_term_in_data_descriptor(_KNOWN_DD, _UNKNOWN_TERM)
        assert term is None

    def test_unknown_dd_returns_none(self, universe_db):
        with _inject_universe(universe_db):
            term = ev.get_term_in_data_descriptor(_UNKNOWN_DD, _KNOWN_TERM)
        assert term is None


# ---------------------------------------------------------------------------
# DT-36  get_term_in_universe  (cross-descriptor lookup by term id)
# ---------------------------------------------------------------------------

class TestGetTermInUniverse:
    """DT-36: fetch a term by id across all data descriptors."""

    def test_known_term_found(self, universe_db):
        with _inject_universe(universe_db):
            term = ev.get_term_in_universe(_KNOWN_TERM)
        assert term is not None

    def test_known_term_has_correct_id(self, universe_db):
        with _inject_universe(universe_db):
            term = ev.get_term_in_universe(_KNOWN_TERM)
        assert term.id == _KNOWN_TERM

    def test_unknown_term_returns_none(self, universe_db):
        with _inject_universe(universe_db):
            term = ev.get_term_in_universe(_UNKNOWN_TERM)
        assert term is None


# ---------------------------------------------------------------------------
# DT-37  get_data_descriptor_in_universe
# ---------------------------------------------------------------------------

class TestGetDataDescriptorInUniverse:
    """DT-37: fetch metadata for a data descriptor."""

    def test_known_dd_returns_result(self, universe_db):
        with _inject_universe(universe_db):
            result = ev.get_data_descriptor_in_universe(_KNOWN_DD)
        assert result is not None

    def test_result_is_tuple_of_id_and_dict(self, universe_db):
        with _inject_universe(universe_db):
            result = ev.get_data_descriptor_in_universe(_KNOWN_DD)
        assert isinstance(result, tuple)
        dd_id, specs = result
        assert dd_id == _KNOWN_DD
        assert isinstance(specs, dict)

    def test_unknown_dd_returns_none(self, universe_db):
        with _inject_universe(universe_db):
            result = ev.get_data_descriptor_in_universe(_UNKNOWN_DD)
        assert result is None


# ---------------------------------------------------------------------------
# DT-38  find_terms_in_universe  (full-text search)
# ---------------------------------------------------------------------------

class TestFindTermsInUniverse:
    """DT-38: FTS search across all universe terms."""

    def test_find_known_term_by_id_returns_results(self, universe_db):
        with _inject_universe(universe_db):
            results = ev.find_terms_in_universe(_KNOWN_TERM)
        assert len(results) > 0

    def test_find_results_have_id(self, universe_db):
        with _inject_universe(universe_db):
            results = ev.find_terms_in_universe(_KNOWN_TERM)
        for r in results:
            assert hasattr(r, "id")
            assert r.id

    def test_find_nonsense_returns_empty(self, universe_db):
        with _inject_universe(universe_db):
            results = ev.find_terms_in_universe("xyzxyzxyz_no_match_abc123")
        assert results == []


# ---------------------------------------------------------------------------
# DT-39  find_data_descriptors_in_universe
# ---------------------------------------------------------------------------

class TestFindDataDescriptorsInUniverse:
    """DT-39: search for data descriptors by name/id."""

    def test_find_known_dd_returns_results(self, universe_db):
        with _inject_universe(universe_db):
            results = ev.find_data_descriptors_in_universe(_KNOWN_DD)
        assert len(results) > 0

    def test_find_nonsense_returns_empty(self, universe_db):
        with _inject_universe(universe_db):
            results = ev.find_data_descriptors_in_universe("xyzxyz_no_match_99999")
        assert results == []


# ---------------------------------------------------------------------------
# DT-40  find_terms_in_data_descriptor
# ---------------------------------------------------------------------------

class TestFindTermsInDataDescriptor:
    """DT-40: FTS search restricted to a specific data descriptor."""

    def test_find_known_term_in_known_dd(self, universe_db):
        with _inject_universe(universe_db):
            results = ev.find_terms_in_data_descriptor(_KNOWN_TERM, _KNOWN_DD)
        assert len(results) > 0

    def test_find_in_wrong_dd_returns_empty(self, universe_db):
        """Searching for activity term in a different data descriptor → empty."""
        # Pick a data descriptor that definitely doesn't have "aerchemmip"
        with _inject_universe(universe_db):
            results = ev.find_terms_in_data_descriptor(_KNOWN_TERM, "calendar")
        assert results == []

    def test_find_in_unknown_dd_returns_empty(self, universe_db):
        with _inject_universe(universe_db):
            results = ev.find_terms_in_data_descriptor(_KNOWN_TERM, _UNKNOWN_DD)
        assert results == []


# ---------------------------------------------------------------------------
# DT-41  All universe functions return empty / None for unknown inputs
# ---------------------------------------------------------------------------

class TestUniverseAPIGracefulFallback:
    """DT-41: All universe API functions handle missing data gracefully."""

    def test_get_all_dds_is_always_nonempty(self, universe_db):
        """The universe DB always has at least one data descriptor."""
        with _inject_universe(universe_db):
            dds = ev.get_all_data_descriptors_in_universe()
        assert len(dds) > 0

    def test_get_all_terms_in_universe_is_nonempty(self, universe_db):
        with _inject_universe(universe_db):
            terms = ev.get_all_terms_in_universe()
        assert len(terms) > 0

    def test_all_dds_are_strings(self, universe_db):
        with _inject_universe(universe_db):
            dds = ev.get_all_data_descriptors_in_universe()
        for dd in dds:
            assert isinstance(dd, str), f"Expected str, got {type(dd)}: {dd}"

    def test_known_dd_in_all_dds(self, universe_db):
        with _inject_universe(universe_db):
            dds = ev.get_all_data_descriptors_in_universe()
        assert _KNOWN_DD in dds
