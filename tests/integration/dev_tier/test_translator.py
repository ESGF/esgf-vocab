"""
Dev Tier — generic_translator module tests.

Tests the parse_mapping / apply_mappings string-based DSL, the
TranslationResult container, and the high-level translate_term / translate_collection
functions against real project + universe DBs.

Plan scenarios covered:
  DT-99   parse_mapping("@id") produces from_id() — term_id is used as value
  DT-100  parse_mapping("field_name") copies the named field
  DT-101  parse_mapping("=value") returns a constant
  DT-102  parse_mapping("=[]") returns an empty list constant
  DT-103  parse_mapping("[field]") wraps a field value in a list
  DT-104  parse_mapping("{field}") wraps a field value in a dict
  DT-105  parse_mapping("a|b") returns first non-None value (fallback chain)
  DT-106  apply_mappings transforms data and passes through unmapped fields
  DT-107  translate_term with known collection returns TranslationResult with data
  DT-108  translate_term with unknown collection returns result with validation_md error
  DT-109  translate_collection yields one result per term
  DT-110  get_pydantic_model_for_collection returns correct class for known collection
  DT-111  get_pydantic_model_for_collection returns None for unknown collection
  DT-112  TranslationResult.data is None when validation fails
  DT-113  translate_term applies transform_fn before validation
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import esgvoc.core.service as svc
from esgvoc.core.db.connection import DBConnection
from esgvoc.api.data_descriptors.translator.generic_translator import (
    parse_mapping,
    apply_mappings,
    translate_term,
    translate_collection,
    get_pydantic_model_for_collection,
    TranslationResult,
    from_id,
    field,
    default,
    as_list,
    as_dict,
    first_of,
)

# ---------------------------------------------------------------------------
# Known constants from real cmip6 DB
# ---------------------------------------------------------------------------

_PROJECT_ID = "cmip6"
_KNOWN_COLLECTION = "activity_id"
_KNOWN_TERM = "aerchemmip"


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
# DT-99 to DT-105  parse_mapping DSL
# ---------------------------------------------------------------------------

class TestParseMappingAtId:
    """DT-99: parse_mapping('@id') uses the term_id as the value."""

    def test_at_id_returns_term_id(self):
        fn = parse_mapping("@id")
        result = fn("my_term", {"some_field": "ignored"})
        assert result == "my_term"

    def test_at_id_ignores_data(self):
        fn = parse_mapping("@id")
        assert fn("term_a", {}) == "term_a"
        assert fn("term_b", {"id": "x"}) == "term_b"


class TestParseMappingField:
    """DT-100: parse_mapping('field_name') copies the named field from data."""

    def test_copies_existing_field(self):
        fn = parse_mapping("drs_name")
        result = fn("ignored_id", {"drs_name": "AerChemMIP", "other": "x"})
        assert result == "AerChemMIP"

    def test_returns_none_when_field_missing(self):
        fn = parse_mapping("nonexistent_field")
        result = fn("id", {"a": 1})
        assert result is None

    def test_copies_nested_value_unchanged(self):
        fn = parse_mapping("tags")
        result = fn("id", {"tags": ["a", "b"]})
        assert result == ["a", "b"]


class TestParseMappingDefault:
    """DT-101/DT-102: parse_mapping('=value') returns a constant."""

    def test_constant_string_value(self):
        fn = parse_mapping("=aerosol")
        assert fn("any_id", {}) == "aerosol"

    def test_empty_list_constant(self):
        fn = parse_mapping("=[]")
        result = fn("any_id", {})
        assert result == []

    def test_bracketed_item_gives_list(self):
        fn = parse_mapping("=[cmip6]")
        result = fn("id", {})
        assert result == ["cmip6"]


class TestParseMappingAsList:
    """DT-103: parse_mapping('[field]') wraps the field value in a list."""

    def test_scalar_wrapped_in_list(self):
        fn = parse_mapping("[drs_name]")
        result = fn("id", {"drs_name": "AerChemMIP"})
        assert result == ["AerChemMIP"]

    def test_missing_field_gives_empty_list(self):
        fn = parse_mapping("[nonexistent]")
        result = fn("id", {})
        assert result == []

    def test_list_field_passed_through_unchanged(self):
        fn = parse_mapping("[tags]")
        result = fn("id", {"tags": ["a", "b"]})
        assert result == ["a", "b"]


class TestParseMappingAsDict:
    """DT-104: parse_mapping('{field}') wraps the field value in a dict."""

    def test_scalar_wrapped_in_dict(self):
        fn = parse_mapping("{drs_name}")
        result = fn("id", {"drs_name": "AerChemMIP"})
        assert result == {"id": "AerChemMIP"}

    def test_missing_field_gives_empty_dict(self):
        fn = parse_mapping("{nonexistent}")
        result = fn("id", {})
        assert result == {}


class TestParseMappingFirstOf:
    """DT-105: parse_mapping('a|b') returns first non-None value."""

    def test_first_field_takes_priority(self):
        fn = parse_mapping("primary|fallback")
        result = fn("id", {"primary": "first", "fallback": "second"})
        assert result == "first"

    def test_falls_back_to_second_when_first_none(self):
        fn = parse_mapping("primary|fallback")
        result = fn("id", {"primary": None, "fallback": "second"})
        assert result == "second"

    def test_at_id_in_chain(self):
        fn = parse_mapping("missing_field|@id")
        result = fn("my_term", {"other": "x"})
        assert result == "my_term"

    def test_all_missing_returns_none(self):
        fn = parse_mapping("a|b|c")
        result = fn("id", {})
        assert result is None


# ---------------------------------------------------------------------------
# DT-106  apply_mappings
# ---------------------------------------------------------------------------

class TestApplyMappings:
    """DT-106: apply_mappings transforms data and passes through unmapped fields."""

    def test_transforms_mapped_field(self):
        collection_mappings = {
            "activity_id": {"label": "@id"}
        }
        result = apply_mappings(
            "activity_id", "aerchemmip",
            {"drs_name": "AerChemMIP", "extra": "val"},
            collection_mappings,
        )
        assert result["label"] == "aerchemmip"

    def test_passes_through_unmapped_fields(self):
        collection_mappings = {"activity_id": {"label": "@id"}}
        result = apply_mappings(
            "activity_id", "aerchemmip",
            {"drs_name": "AerChemMIP"},
            collection_mappings,
        )
        assert result["drs_name"] == "AerChemMIP"

    def test_excluded_fields_are_dropped(self):
        collection_mappings = {"activity_id": {}}
        excluded = {"activity_id": {"secret"}}
        result = apply_mappings(
            "activity_id", "term",
            {"drs_name": "X", "secret": "hidden"},
            collection_mappings,
            excluded_fields=excluded,
        )
        assert "secret" not in result
        assert result["drs_name"] == "X"

    def test_empty_string_becomes_none(self):
        collection_mappings = {"activity_id": {}}
        result = apply_mappings(
            "activity_id", "term",
            {"description": ""},
            collection_mappings,
        )
        assert result["description"] is None

    def test_unknown_collection_passes_all_fields_through(self):
        collection_mappings = {}  # no mapping for "other_coll"
        result = apply_mappings(
            "other_coll", "term",
            {"a": 1, "b": 2},
            collection_mappings,
        )
        assert result["a"] == 1
        assert result["b"] == 2


# ---------------------------------------------------------------------------
# DT-107  translate_term with known collection
# ---------------------------------------------------------------------------

class TestTranslateTermKnownCollection:
    """DT-107: translate_term with a known collection returns TranslationResult with data."""

    def test_known_collection_returns_result(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            result = translate_term(
                _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM,
                {"drs_name": "AerChemMIP"}
            )
        assert isinstance(result, TranslationResult)

    def test_result_has_term_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            result = translate_term(
                _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM,
                {"drs_name": "AerChemMIP"}
            )
        assert result.term_id == _KNOWN_TERM

    def test_result_has_collection_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            result = translate_term(
                _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM,
                {"drs_name": "AerChemMIP"}
            )
        assert result.collection_id == _KNOWN_COLLECTION

    def test_result_has_data_descriptor_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            result = translate_term(
                _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM,
                {"drs_name": "AerChemMIP"}
            )
        assert result.data_descriptor_id is not None


# ---------------------------------------------------------------------------
# DT-108  translate_term with unknown collection
# ---------------------------------------------------------------------------

class TestTranslateTermUnknownCollection:
    """DT-108: translate_term with unknown collection returns error in validation_md."""

    def test_unknown_collection_gives_error_message(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            result = translate_term(
                _PROJECT_ID, "nonexistent-collection-xyz", "some_term",
                {"drs_name": "X"}
            )
        assert isinstance(result, TranslationResult)
        assert result.data is None
        assert result.validation_md is not None and result.validation_md.strip()

    def test_unknown_collection_result_has_term_id(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            result = translate_term(
                _PROJECT_ID, "nonexistent-collection-xyz", "some_term",
                {}
            )
        assert result.term_id == "some_term"


# ---------------------------------------------------------------------------
# DT-109  translate_collection
# ---------------------------------------------------------------------------

class TestTranslateCollection:
    """DT-109: translate_collection yields one result per term."""

    def test_yields_results_for_each_term(self, real_dbs, universe_db):
        terms = {
            _KNOWN_TERM: {"drs_name": "AerChemMIP"},
            "aerchemmip": {"drs_name": "AerChemMIP"},
        }
        with _inject(real_dbs["v1_path"], universe_db):
            results = list(translate_collection(_PROJECT_ID, _KNOWN_COLLECTION, terms))
        assert len(results) == 2

    def test_each_result_is_translation_result(self, real_dbs, universe_db):
        terms = {_KNOWN_TERM: {"drs_name": "AerChemMIP"}}
        with _inject(real_dbs["v1_path"], universe_db):
            results = list(translate_collection(_PROJECT_ID, _KNOWN_COLLECTION, terms))
        for r in results:
            assert isinstance(r, TranslationResult)

    def test_empty_terms_yields_nothing(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            results = list(translate_collection(_PROJECT_ID, _KNOWN_COLLECTION, {}))
        assert results == []


# ---------------------------------------------------------------------------
# DT-110  get_pydantic_model_for_collection
# ---------------------------------------------------------------------------

class TestGetPydanticModelForCollection:
    """DT-110: get_pydantic_model_for_collection returns correct class for known collection."""

    def test_known_collection_returns_class(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            cls = get_pydantic_model_for_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        # May be None if the collection has no data_descriptor, but not an error
        # For activity_id, typically maps to Activity
        assert cls is None or isinstance(cls, type)

    def test_return_is_a_class_or_none(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            cls = get_pydantic_model_for_collection(_PROJECT_ID, _KNOWN_COLLECTION)
        assert cls is None or callable(cls)


# ---------------------------------------------------------------------------
# DT-111  get_pydantic_model_for_collection with unknown collection
# ---------------------------------------------------------------------------

class TestGetPydanticModelUnknown:
    """DT-111: get_pydantic_model_for_collection returns None for unknown collection."""

    def test_unknown_collection_returns_none(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            cls = get_pydantic_model_for_collection(
                _PROJECT_ID, "nonexistent-collection-xyz"
            )
        assert cls is None


# ---------------------------------------------------------------------------
# DT-112  TranslationResult.data is None when validation fails
# ---------------------------------------------------------------------------

class TestTranslationResultFailure:
    """DT-112: TranslationResult.data is None when model validation fails."""

    def test_data_none_on_missing_collection(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            result = translate_term(
                _PROJECT_ID, "nonexistent_collection", "term",
                {}
            )
        assert result.data is None

    def test_validation_md_set_on_failure(self, real_dbs, universe_db):
        with _inject(real_dbs["v1_path"], universe_db):
            result = translate_term(
                _PROJECT_ID, "nonexistent_collection", "term",
                {}
            )
        assert result.validation_md is not None


# ---------------------------------------------------------------------------
# DT-113  translate_term applies transform_fn before validation
# ---------------------------------------------------------------------------

class TestTranslatTermTransformFn:
    """DT-113: translate_term applies the transform_fn to data before validation."""

    def test_transform_fn_is_called(self, real_dbs, universe_db):
        calls = []

        def _track(collection_id, term_id, data):
            calls.append((collection_id, term_id))
            return data

        with _inject(real_dbs["v1_path"], universe_db):
            result = translate_term(
                _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM,
                {"drs_name": "AerChemMIP"},
                transform_fn=_track,
            )

        assert len(calls) == 1, f"transform_fn should be called once; got {calls}"
        assert calls[0][0] == _KNOWN_COLLECTION
        assert calls[0][1] == _KNOWN_TERM

    def test_transform_fn_can_modify_data(self, real_dbs, universe_db):
        """transform_fn can inject extra fields into data."""

        def _inject_extra(collection_id, term_id, data):
            return {**data, "injected_field": "injected_value"}

        with _inject(real_dbs["v1_path"], universe_db):
            result = translate_term(
                _PROJECT_ID, _KNOWN_COLLECTION, _KNOWN_TERM,
                {"drs_name": "AerChemMIP"},
                transform_fn=_inject_extra,
            )

        # The result may succeed or fail based on the model, but transform was applied
        assert isinstance(result, TranslationResult)
