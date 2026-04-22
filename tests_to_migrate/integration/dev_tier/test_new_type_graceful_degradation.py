"""
Dev Tier — New Data Descriptor Type (Scenario 30) tests.

Documents the actual behavior when a term's type is not present in
DATA_DESCRIPTOR_CLASS_MAPPING — this happens when a new type is added to the
CV (e.g. 'license') but the installed esgvoc version does not yet know about it.

Current behavior: instantiate_pydantic_term raises EsgvocDbError (Scenario 16/30).
The distinction from a plain "unknown term type" (Scenario 16) is that here the
type exists in the DB but the running esgvoc code does not recognise it.

Plan scenarios covered:
  DT-146  instantiate_pydantic_term raises EsgvocDbError for unknown type
  DT-147  get_term_in_project propagates EsgvocDbError for unknown type
  DT-148  instantiate_pydantic_term succeeds for known types (control)
  DT-149  DATA_DESCRIPTOR_CLASS_MAPPING.get returns None for unknown type
            (lenient) while get_pydantic_class raises (strict)
  DT-150  get_all_terms_in_collection still returns terms when type is known
  DT-151  Other known terms in same project remain accessible after unknown-type error
  DT-152  DataDescriptorSubSet path is unaffected by unknown type (selected_fields path)
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import esgvoc.api as ev
import esgvoc.core.service as svc
from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING
from esgvoc.api.pydantic_handler import get_pydantic_class, instantiate_pydantic_term
from esgvoc.core.db.connection import DBConnection
from esgvoc.core.exceptions import EsgvocDbError

_PROJECT_ID = "cmip6"
_KNOWN_COLLECTION = "activity_id"
_KNOWN_TERM = "aerchemmip"
_UNKNOWN_TYPE = "license_completely_unknown_xyz"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_term_with_type(term_type: str) -> SimpleNamespace:
    """Return a minimal object that mimics UTerm/PTerm with a custom type field."""
    return SimpleNamespace(
        id="fake-term",
        specs={
            "type": term_type,
            "id": "fake-term",
            "description": "A fake term for testing unknown-type degradation",
        },
    )


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


# ---------------------------------------------------------------------------
# DT-146  instantiate_pydantic_term raises for unknown type
# ---------------------------------------------------------------------------

class TestInstantiateUnknownType:
    """DT-146: instantiate_pydantic_term raises EsgvocDbError for unknown type (Scenario 30)."""

    def test_unknown_type_raises_db_error(self):
        fake = _fake_term_with_type(_UNKNOWN_TYPE)
        with pytest.raises(EsgvocDbError):
            instantiate_pydantic_term(fake, None)

    def test_error_message_references_unknown_type(self):
        fake = _fake_term_with_type(_UNKNOWN_TYPE)
        with pytest.raises(EsgvocDbError) as exc_info:
            instantiate_pydantic_term(fake, None)
        assert _UNKNOWN_TYPE in str(exc_info.value)

    def test_empty_type_raises_db_error(self):
        fake = _fake_term_with_type("")
        with pytest.raises(EsgvocDbError):
            instantiate_pydantic_term(fake, None)

    def test_new_cv_type_not_in_old_esgvoc_raises(self):
        """Simulates Scenario 30: CV adds 'license' type but esgvoc doesn't know it."""
        fake = _fake_term_with_type("license_new_cv_type")
        with pytest.raises(EsgvocDbError):
            instantiate_pydantic_term(fake, None)


# ---------------------------------------------------------------------------
# DT-147  get_term_in_project propagates EsgvocDbError
# ---------------------------------------------------------------------------

class TestGetTermInProjectUnknownType:
    """DT-147: get_term_in_project propagates EsgvocDbError when type is unknown."""

    def test_propagates_db_error_for_unknown_type(self, real_dbs, universe_db):
        """When a DB term has an unknown type, get_term_in_project raises EsgvocDbError."""
        fake = _fake_term_with_type(_UNKNOWN_TYPE)
        with _inject(real_dbs["v1_path"], universe_db):
            with patch("esgvoc.api.projects._get_term_in_project", return_value=fake):
                with pytest.raises(EsgvocDbError):
                    ev.get_term_in_project(_PROJECT_ID, "any-term-id")

    def test_error_not_silently_swallowed(self, real_dbs, universe_db):
        """EsgvocDbError must propagate — not silently return None (Scenario 30)."""
        fake = _fake_term_with_type(_UNKNOWN_TYPE)
        with _inject(real_dbs["v1_path"], universe_db):
            with patch("esgvoc.api.projects._get_term_in_project", return_value=fake):
                raised = False
                try:
                    ev.get_term_in_project(_PROJECT_ID, "any-term-id")
                except EsgvocDbError:
                    raised = True
        assert raised, "EsgvocDbError should propagate, not be silently swallowed"


# ---------------------------------------------------------------------------
# DT-148  Control: instantiate_pydantic_term works for known types
# ---------------------------------------------------------------------------

class TestInstantiateKnownType:
    """DT-148: instantiate_pydantic_term succeeds for types in DATA_DESCRIPTOR_CLASS_MAPPING."""

    def test_activity_type_returns_descriptor(self, real_dbs, universe_db):
        """A real activity term can be instantiated without error."""
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, _KNOWN_TERM)
        assert term is not None

    def test_returned_term_has_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, _KNOWN_TERM)
        assert hasattr(term, "id")
        assert term.id == _KNOWN_TERM

    def test_all_known_types_instantiate(self):
        """Each type in DATA_DESCRIPTOR_CLASS_MAPPING can be retrieved via get_pydantic_class."""
        for type_id in DATA_DESCRIPTOR_CLASS_MAPPING:
            cls = get_pydantic_class(type_id)
            assert cls is not None
            assert callable(cls)


# ---------------------------------------------------------------------------
# DT-149  Lenient vs strict type lookup
# ---------------------------------------------------------------------------

class TestLenientVsStrictLookup:
    """DT-149: DATA_DESCRIPTOR_CLASS_MAPPING.get is lenient; get_pydantic_class is strict."""

    def test_mapping_get_returns_none_for_unknown(self):
        result = DATA_DESCRIPTOR_CLASS_MAPPING.get(_UNKNOWN_TYPE)
        assert result is None

    def test_get_pydantic_class_raises_for_unknown(self):
        with pytest.raises(EsgvocDbError):
            get_pydantic_class(_UNKNOWN_TYPE)

    def test_mapping_get_returns_class_for_known(self):
        cls = DATA_DESCRIPTOR_CLASS_MAPPING.get("activity")
        assert cls is not None
        assert callable(cls)

    def test_get_pydantic_class_returns_class_for_known(self):
        cls = get_pydantic_class("activity")
        assert callable(cls)

    def test_both_agree_on_known_types(self):
        for type_id, expected_cls in DATA_DESCRIPTOR_CLASS_MAPPING.items():
            via_mapping = DATA_DESCRIPTOR_CLASS_MAPPING.get(type_id)
            via_function = get_pydantic_class(type_id)
            assert via_mapping is via_function is expected_cls


# ---------------------------------------------------------------------------
# DT-150  get_all_terms_in_collection still works for known types
# ---------------------------------------------------------------------------

class TestGetAllTermsKnownType:
    """DT-150: Collections of known types are fully accessible (Scenario 30 control)."""

    def test_activity_id_collection_is_nonempty(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        assert len(terms) > 0

    def test_all_terms_have_non_empty_ids(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            terms = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        for term in terms:
            assert term.id, f"term {term!r} has empty id"

    def test_term_count_same_in_both_db_versions(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            v1_terms = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        with _inject(real_dbs["v2_path"], universe_db):
            v2_terms = ev.get_all_terms_in_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        assert len(v1_terms) == len(v2_terms), (
            f"Term count mismatch: v1={len(v1_terms)}, v2={len(v2_terms)}"
        )


# ---------------------------------------------------------------------------
# DT-151  Other terms remain accessible after unknown-type error
# ---------------------------------------------------------------------------

class TestResilienceAfterError:
    """DT-151: After an EsgvocDbError from unknown type, other known terms are accessible."""

    def test_known_term_accessible_after_unknown_type_error(self, real_dbs, universe_db):
        """Known terms work fine regardless of whether an unknown-type error occurred."""
        fake = _fake_term_with_type(_UNKNOWN_TYPE)
        with _inject(real_dbs["v1_path"], universe_db):
            # First call: raises EsgvocDbError for unknown type
            with patch("esgvoc.api.projects._get_term_in_project", return_value=fake):
                with pytest.raises(EsgvocDbError):
                    ev.get_term_in_project(_PROJECT_ID, "fake-term")

            # Second call: no patch — real query for a known term
            term = ev.get_term_in_project(_PROJECT_ID, _KNOWN_TERM)

        assert term is not None
        assert term.id == _KNOWN_TERM


# ---------------------------------------------------------------------------
# DT-152  DataDescriptorSubSet path unaffected by unknown type
# ---------------------------------------------------------------------------

class TestSubSetPathUnaffected:
    """DT-152: When selected_term_fields is provided, type checking is skipped (SubSet path)."""

    def test_unknown_type_with_selected_fields_does_not_raise(self):
        """The DataDescriptorSubSet code path uses model_construct — no type lookup."""
        fake = _fake_term_with_type(_UNKNOWN_TYPE)
        # selected_term_fields path: does NOT call get_pydantic_class
        from esgvoc.api.data_descriptors.data_descriptor import DataDescriptorSubSet
        result = instantiate_pydantic_term(fake, [])  # empty list → subset path
        assert isinstance(result, DataDescriptorSubSet)

    def test_subset_has_id(self):
        fake = _fake_term_with_type(_UNKNOWN_TYPE)
        result = instantiate_pydantic_term(fake, [])
        assert result.id == "fake-term"

    def test_subset_with_known_type_also_works(self, real_dbs, universe_db):
        """Confirm that selected_term_fields path works for known types too."""
        with _inject(real_dbs["v1_path"], universe_db):
            term = ev.get_term_in_project(_PROJECT_ID, _KNOWN_TERM, selected_term_fields=["drs_name"])
        assert term is not None
        assert term.id == _KNOWN_TERM
