"""
Tests for JsonLdResource — JSON-LD loading and local path resolution.
These tests do not require installed databases.

Fixtures used
-------------
tests/fixtures/mini_universe/
    activity/000_context.jsonld   — minimal JSON-LD context (plain terms)
    activity/cmip.json            — plain term referencing the context
    experiment/000_context.jsonld — context with nested @context/@base fields
    experiment/historical.json    — term with linked string and list fields
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from esgvoc.core.data_handler import JsonLdResource, unified_document_loader

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "mini_universe"
_ACTIVITY_CMIP = _FIXTURES / "activity" / "cmip.json"
_EXPERIMENT_HISTORICAL = _FIXTURES / "experiment" / "historical.json"


# ---------------------------------------------------------------------------
# unified_document_loader
# ---------------------------------------------------------------------------

class TestUnifiedDocumentLoader:
    def test_loads_local_json_file(self, tmp_path):
        data = {"@context": "http://example.com/ctx", "id": "test"}
        f = tmp_path / "term.jsonld"
        f.write_text(json.dumps(data))
        result = unified_document_loader(str(f))
        assert result == data

    def test_loads_file_uri(self, tmp_path):
        data = {"key": "value"}
        f = tmp_path / "data.jsonld"
        f.write_text(json.dumps(data))
        result = unified_document_loader(f"file://{f}")
        assert result == data

    def test_invalid_path_raises(self):
        with pytest.raises(FileNotFoundError):
            unified_document_loader("/nonexistent/path/file.jsonld")


# ---------------------------------------------------------------------------
# JsonLdResource model validation
# ---------------------------------------------------------------------------

class TestJsonLdResourceValidation:
    def test_valid_uri_string(self):
        r = JsonLdResource(uri="http://example.com/term")
        assert r.uri == "http://example.com/term"

    def test_invalid_uri_type_raises(self):
        with pytest.raises(ValidationError):
            JsonLdResource(uri=123)

    def test_local_path_becomes_absolute(self, tmp_path):
        r = JsonLdResource(uri="http://example.com/term", local_path=str(tmp_path))
        assert r.local_path.startswith("/")
        assert r.local_path.endswith("/")


# ---------------------------------------------------------------------------
# JsonLdResource.json_dict (mocked loader)
# ---------------------------------------------------------------------------

class TestJsonLdResourceJsonDict:
    def test_json_dict_calls_loader(self):
        mock_data = {"@context": "http://example.com/ctx", "name": "Test"}
        with patch(
            "esgvoc.core.data_handler.unified_document_loader",
            return_value=mock_data,
        ) as mock_loader:
            r = JsonLdResource(uri="http://example.com/resource")
            result = r.json_dict
        assert result == mock_data
        mock_loader.assert_called_once_with("http://example.com/resource")

    def test_json_dict_from_real_local_file(self, tmp_path):
        data = {"@context": {}, "id": "myterm", "type": "institution"}
        f = tmp_path / "term.jsonld"
        f.write_text(json.dumps(data))
        r = JsonLdResource(uri=str(f))
        assert r.json_dict["id"] == "myterm"


# ---------------------------------------------------------------------------
# unified_document_loader — HTTP branch (mocked)
# ---------------------------------------------------------------------------

class TestUnifiedDocumentLoaderHttp:
    def test_http_200_returns_json(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "remote-term"}
        with patch("esgvoc.core.data_handler.requests.get", return_value=mock_resp):
            result = unified_document_loader("https://example.com/term.json")
        assert result == {"id": "remote-term"}

    def test_http_404_returns_empty_dict(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"
        with patch("esgvoc.core.data_handler.requests.get", return_value=mock_resp):
            result = unified_document_loader("https://example.com/missing.json")
        assert result == {}


# ---------------------------------------------------------------------------
# JsonLdResource — fixture-backed properties
# ---------------------------------------------------------------------------

class TestJsonLdResourceProperties:
    def test_context_returns_dict(self):
        r = JsonLdResource(uri=str(_ACTIVITY_CMIP))
        ctx = r.context
        assert isinstance(ctx, dict)

    def test_context_contains_at_context(self):
        r = JsonLdResource(uri=str(_ACTIVITY_CMIP))
        ctx = r.context
        assert "@context" in ctx

    def test_expanded_returns_list(self):
        r = JsonLdResource(uri=str(_ACTIVITY_CMIP))
        expanded = r.expanded
        assert isinstance(expanded, list)
        assert len(expanded) > 0

    def test_expanded_contains_id(self):
        r = JsonLdResource(uri=str(_ACTIVITY_CMIP))
        expanded = r.expanded
        assert "@id" in expanded[0]

    def test_normalized_returns_string(self):
        r = JsonLdResource(uri=str(_ACTIVITY_CMIP))
        normalized = r.normalized
        assert isinstance(normalized, str)

    def test_info_returns_non_empty_string(self):
        r = JsonLdResource(uri=str(_ACTIVITY_CMIP))
        info = r.info
        assert isinstance(info, str)
        assert len(info) > 0
        assert "cmip" in info


# ---------------------------------------------------------------------------
# JsonLdResource._extract_model_key
# ---------------------------------------------------------------------------

class TestExtractModelKey:
    def _resource(self):
        return JsonLdResource(uri="http://example.com/fake")

    def test_extracts_second_to_last_segment(self):
        r = self._resource()
        assert r._extract_model_key("https://example.com/universe/activity/cmip") == "activity"

    def test_extracts_from_trailing_slash(self):
        r = self._resource()
        assert r._extract_model_key("https://example.com/universe/activity/") == "universe"

    def test_returns_none_for_short_uri(self):
        r = self._resource()
        assert r._extract_model_key("single") is None

    def test_returns_none_for_empty(self):
        r = self._resource()
        assert r._extract_model_key("") is None


# ---------------------------------------------------------------------------
# JsonLdResource._preprocess_nested_contexts — pure logic tests
# ---------------------------------------------------------------------------

class TestPreprocessNestedContexts:
    def _resource(self):
        return JsonLdResource(uri="http://example.com/fake")

    def _ctx_with_nested(self, field="parent", base="https://example.com/base/"):
        """Return a context dict that has a nested @context on `field`."""
        return {
            field: {
                "@id": base,
                "@type": "@id",
                "@context": {"@base": base},
            }
        }

    def test_at_context_key_copied_as_is(self):
        r = self._resource()
        data = {"@context": "000_context.jsonld", "id": "foo"}
        result = r._preprocess_nested_contexts(data, {})
        assert result["@context"] == "000_context.jsonld"

    def test_plain_value_copied(self):
        r = self._resource()
        result = r._preprocess_nested_contexts({"id": "foo"}, {})
        assert result["id"] == "foo"

    def test_dict_value_without_nested_ctx_recursed(self):
        r = self._resource()
        data = {"nested": {"key": "val"}}
        result = r._preprocess_nested_contexts(data, {})
        assert result["nested"] == {"key": "val"}

    def test_list_value_without_nested_ctx_items_recursed(self):
        r = self._resource()
        data = {"items": [{"a": 1}, "plain"]}
        result = r._preprocess_nested_contexts(data, {})
        assert result["items"] == [{"a": 1}, "plain"]

    def test_string_with_nested_ctx_wrapped_in_id(self):
        r = self._resource()
        ctx = self._ctx_with_nested("parent", "https://example.com/exp/")
        data = {"parent": "piControl"}
        result = r._preprocess_nested_contexts(data, ctx)
        assert result["parent"] == {"@id": "https://example.com/exp/piControl"}

    def test_absolute_url_string_wrapped_without_base_prepend(self):
        r = self._resource()
        ctx = self._ctx_with_nested("parent", "https://example.com/exp/")
        data = {"parent": "https://other.com/exp/piControl"}
        result = r._preprocess_nested_contexts(data, ctx)
        assert result["parent"] == {"@id": "https://other.com/exp/piControl"}

    def test_list_strings_with_nested_ctx_each_wrapped(self):
        r = self._resource()
        ctx = self._ctx_with_nested("related", "https://example.com/exp/")
        data = {"related": ["piControl", "historical"]}
        result = r._preprocess_nested_contexts(data, ctx)
        assert result["related"] == [
            {"@id": "https://example.com/exp/piControl"},
            {"@id": "https://example.com/exp/historical"},
        ]

    def test_list_mixed_abs_url_not_prepended(self):
        r = self._resource()
        ctx = self._ctx_with_nested("related", "https://example.com/exp/")
        data = {"related": ["piControl", "https://other.com/exp/abrupt"]}
        result = r._preprocess_nested_contexts(data, ctx)
        assert result["related"][0] == {"@id": "https://example.com/exp/piControl"}
        assert result["related"][1] == {"@id": "https://other.com/exp/abrupt"}

    def test_list_dicts_with_nested_ctx_recursed(self):
        r = self._resource()
        ctx = self._ctx_with_nested("related", "https://example.com/exp/")
        data = {"related": [{"id": "piControl"}]}
        result = r._preprocess_nested_contexts(data, ctx)
        assert result["related"] == [{"id": "piControl"}]

    def test_dict_value_with_nested_ctx_recursed(self):
        r = self._resource()
        ctx = self._ctx_with_nested("parent", "https://example.com/exp/")
        data = {"parent": {"id": "piControl"}}
        result = r._preprocess_nested_contexts(data, ctx)
        assert result["parent"] == {"id": "piControl"}

    def test_non_dict_input_returned_unchanged(self):
        r = self._resource()
        result = r._preprocess_nested_contexts("not a dict", {})
        assert result == "not a dict"

    def test_on_real_experiment_fixture(self):
        """Smoke test: preprocess the historical.json fixture — no exception."""
        r = JsonLdResource(uri=str(_EXPERIMENT_HISTORICAL))
        data = r.json_dict
        ctx = r.context
        if isinstance(ctx, dict) and "@context" in ctx:
            ctx = ctx["@context"]
        result = r._preprocess_nested_contexts(data, ctx)
        assert isinstance(result, dict)
        assert "parent_experiment" in result
        assert result["parent_experiment"] == {"@id": "https://example.com/universe/experiment/piControl"}
