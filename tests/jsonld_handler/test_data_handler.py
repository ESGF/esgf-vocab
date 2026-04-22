"""
Tests for JsonLdResource — JSON-LD loading and local path resolution.
These tests do not require installed databases.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from esgvoc.core.data_handler import JsonLdResource, unified_document_loader


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
