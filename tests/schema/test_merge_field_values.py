"""
Unit tests for the merge of catalog properties sharing the same field name
(several YAML entries for one catalog field, e.g. CMIP6 variable_cf_standard_name
fed by both standard_name and alias_standard_name).

No DB needed: the property translator is stubbed.
"""

import jsonschema
import pytest

from esgvoc.apps.jsg.json_schema_generator import (
    _catalog_properties_json_processor,
    _CatalogProperty,
    _merge_field_values,
)
from esgvoc.core.exceptions import EsgvocValueError


def _enum(*values: str) -> dict:
    return {"type": "string", "enum": list(values)}


def _pattern(pattern: str) -> dict:
    return {"type": "string", "pattern": pattern}


def _array_of(items: dict) -> dict:
    return {"type": "array", "items": {**items, "minItems": 1}}


def _prop(field_value: dict, field_name: str = "proj:field", is_required: bool = False) -> _CatalogProperty:
    return _CatalogProperty(field_name=field_name, field_value=field_value, is_required=is_required)


class _StubTranslator:
    """Stands for CatalogPropertiesJsonTranslator: specs are already translated properties."""

    def translate_property(self, catalog_property: _CatalogProperty) -> _CatalogProperty:
        return catalog_property


def _process(*props: _CatalogProperty) -> list[_CatalogProperty]:
    return _catalog_properties_json_processor(_StubTranslator(), list(props))  # type: ignore


def _accepts(field_value: dict, value) -> bool:
    return jsonschema.Draft7Validator(field_value).is_valid(value)


class TestMergeFieldValues:
    def test_identical_definitions(self):
        assert _merge_field_values(_enum("a", "b"), _enum("a", "b")) == _enum("a", "b")

    def test_enums_are_united(self):
        assert _merge_field_values(_enum("a", "b"), _enum("b", "c")) == _enum("a", "b", "c")

    def test_enum_union_keeps_left_order(self):
        assert _merge_field_values(_enum("b", "a"), _enum("c", "a"))["enum"] == ["b", "a", "c"]

    def test_enums_with_different_constraints_become_any_of(self):
        left = {"type": "string", "enum": ["a"], "maxLength": 1}
        right = {"type": "string", "enum": ["bb"], "maxLength": 2}
        merged = _merge_field_values(left, right)
        assert merged["type"] == "string"
        assert "anyOf" in merged
        assert _accepts(merged, "a")
        assert _accepts(merged, "bb")
        assert not _accepts(merged, "c")

    def test_patterns_become_any_of(self):
        merged = _merge_field_values(_pattern("^a+$"), _pattern("^b+$"))
        assert merged == {"type": "string", "anyOf": [{"pattern": "^a+$"}, {"pattern": "^b+$"}]}
        assert _accepts(merged, "aaa")
        assert _accepts(merged, "bb")
        assert not _accepts(merged, "ab")

    def test_arrays_merge_their_items(self):
        merged = _merge_field_values(_array_of(_enum("a")), _array_of(_enum("b")))
        assert merged == _array_of(_enum("a", "b"))

    def test_different_types_raise(self):
        with pytest.raises(EsgvocValueError, match="different JSON types"):
            _merge_field_values(_enum("a"), {"type": "integer", "enum": [1]})

    def test_different_keywords_raise(self):
        with pytest.raises(EsgvocValueError, match="different constraint keywords"):
            _merge_field_values(_enum("a"), _pattern("^a$"))

    def test_different_array_constraints_raise(self):
        left = {**_array_of(_enum("a")), "uniqueItems": True}
        right = {**_array_of(_enum("b")), "uniqueItems": False}
        with pytest.raises(EsgvocValueError, match="different array constraints"):
            _merge_field_values(left, right)


class TestCatalogPropertiesJsonProcessor:
    def test_distinct_fields_are_untouched(self):
        props = [_prop(_enum("a"), "proj:x"), _prop(_pattern("^b$"), "proj:y", is_required=True)]
        assert _process(*props) == props

    def test_same_field_is_merged_once(self):
        result = _process(
            _prop(_enum("air_temperature"), "cmip6:variable_cf_standard_name"),
            _prop(_enum("surface_temperature"), "proj:other"),
            _prop(_enum("air_temperature_alias"), "cmip6:variable_cf_standard_name"),
        )
        assert [p.field_name for p in result] == ["cmip6:variable_cf_standard_name", "proj:other"]
        assert result[0].field_value == _enum("air_temperature", "air_temperature_alias")

    def test_identical_duplicates_collapse(self):
        # e.g. the copy-pasted variable_units entry of Obs4REF.
        (result,) = _process(_prop(_enum("K", "m")), _prop(_enum("K", "m")))
        assert result.field_value == _enum("K", "m")

    @pytest.mark.parametrize(
        ("left", "right", "expected"),
        [(False, False, False), (True, False, True), (False, True, True), (True, True, True)],
    )
    def test_required_if_any_definition_is(self, left, right, expected):
        (result,) = _process(_prop(_enum("a"), is_required=left), _prop(_enum("b"), is_required=right))
        assert result.is_required is expected

    @pytest.mark.parametrize(
        "enums",
        [
            (("a",), ("b",), ("c",)),
            (("a",), ("a",), ("b",)),
            (("a",), ("b",), ("a",)),
            (("a", "b"), ("c",), ("d",), ("e",)),
        ],
    )
    def test_many_definitions_accept_every_value(self, enums):
        (result,) = _process(*(_prop(_enum(*values)) for values in enums))
        expected_values = {value for values in enums for value in values}
        for value in expected_values:
            assert _accepts(result.field_value, value)
        assert not _accepts(result.field_value, "unknown")

    def test_incompatible_definitions_name_the_field(self):
        with pytest.raises(EsgvocValueError, match="'cmip6:variable_units'"):
            _process(_prop(_enum("K"), "cmip6:variable_units"), _prop(_pattern("^K$"), "cmip6:variable_units"))
