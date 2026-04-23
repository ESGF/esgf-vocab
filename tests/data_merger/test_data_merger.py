"""
Tests for data_merger.py — merge_dicts, DataMerger, and helper classes.

All tests are pure unit tests or use the mini_universe fixtures.
No network access, no installed databases required.

Fixture layout used:
    tests/fixtures/mini_universe/
        activity/
            000_context.jsonld   — context with @base = https://example.com/universe/activity/
            cmip.json            — plain term (expands @id to the above base)
        experiment/
            000_context.jsonld   — context with nested @context on parent_experiment
            historical.json      — term with parent_experiment = "piControl" (string ref)
            piControl.json       — the referenced term (resolves during integration tests)
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from esgvoc.core.data_handler import JsonLdResource
from esgvoc.core.service.data_merger import (
    DataMerger,
    merge,
    merge_dicts,
    resolve_nested_ids_in_dict,
)
from esgvoc.core.service.resolver_config import ResolverConfig
from esgvoc.core.service.string_heuristics import StringHeuristics
from esgvoc.core.service.term_cache import TermCache
from esgvoc.core.service.uri_resolver import URIResolver

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "mini_universe"
_ACTIVITY_CMIP = _FIXTURES / "activity" / "cmip.json"
_EXPERIMENT_HISTORICAL = _FIXTURES / "experiment" / "historical.json"
_EXPERIMENT_PICONTROL = _FIXTURES / "experiment" / "piControl.json"

# Allowed base URI that matches our mini_universe fixture files
_EXAMPLE_BASE = "https://example.com/universe/"


def _merger_for(path: Path, allowed_base_uris=None, locally_available=None) -> DataMerger:
    """Convenience: build a DataMerger pointing at a local fixture file."""
    resource = JsonLdResource(uri=str(path))
    return DataMerger(
        data=resource,
        allowed_base_uris=allowed_base_uris or {_EXAMPLE_BASE},
        locally_available=locally_available or {_EXAMPLE_BASE: str(_FIXTURES) + "/"},
    )


# ---------------------------------------------------------------------------
# merge_dicts — pure function
# ---------------------------------------------------------------------------

class TestMergeDicts:
    def test_override_takes_precedence_for_shared_key(self):
        base = [{"name": "Base", "value": 1}]
        override = [{"value": 99}]
        result = merge_dicts(base, override)
        assert result["value"] == 99

    def test_base_only_keys_preserved(self):
        base = [{"only_in_base": "yes", "shared": "b"}]
        override = [{"shared": "o"}]
        result = merge_dicts(base, override)
        assert result["only_in_base"] == "yes"
        assert result["shared"] == "o"

    def test_override_only_keys_included(self):
        base = [{"a": 1}]
        override = [{"b": 2}]
        result = merge_dicts(base, override)
        assert result["a"] == 1
        assert result["b"] == 2

    def test_id_excluded_from_base(self):
        base = [{"@id": "should-not-appear", "name": "base"}]
        override = [{"name": "override"}]
        result = merge_dicts(base, override)
        assert "@id" not in result

    def test_id_excluded_from_override(self):
        base = [{"name": "base"}]
        override = [{"@id": "should-not-appear", "name": "override"}]
        result = merge_dicts(base, override)
        assert "@id" not in result

    def test_empty_base(self):
        base = [{}]
        override = [{"key": "val"}]
        assert merge_dicts(base, override) == {"key": "val"}

    def test_empty_override(self):
        base = [{"key": "val"}]
        override = [{}]
        assert merge_dicts(base, override) == {"key": "val"}


# ---------------------------------------------------------------------------
# URIResolver
# ---------------------------------------------------------------------------

class TestURIResolver:
    def test_to_local_path_substitutes_remote_base(self):
        r = URIResolver({"https://example.com/data": "/local/cache"})
        assert r.to_local_path("https://example.com/data/term.json") == "/local/cache/term.json"

    def test_to_local_path_no_match_returns_original(self):
        r = URIResolver({"https://other.com": "/local"})
        uri = "https://example.com/data/term.json"
        assert r.to_local_path(uri) == uri

    def test_ensure_json_extension_adds_suffix(self):
        r = URIResolver({})
        assert r.ensure_json_extension("https://example.com/term") == "https://example.com/term.json"

    def test_ensure_json_extension_no_dup(self):
        r = URIResolver({})
        assert r.ensure_json_extension("https://example.com/term.json") == "https://example.com/term.json"

    def test_normalize_combines_both(self):
        r = URIResolver({"https://example.com": "/local"})
        assert r.normalize("https://example.com/term") == "/local/term.json"

    def test_exists_returns_false_for_missing(self, tmp_path):
        r = URIResolver({"https://example.com": str(tmp_path)})
        assert not r.exists("https://example.com/nonexistent")

    def test_exists_returns_true_for_real_file(self, tmp_path):
        f = tmp_path / "term.json"
        f.write_text("{}")
        r = URIResolver({"https://example.com": str(tmp_path)})
        assert r.exists("https://example.com/term.json")

    def test_get_filename(self):
        r = URIResolver({})
        assert r.get_filename("https://example.com/data/term.json") == "term.json"

    def test_get_parent_dir(self, tmp_path):
        r = URIResolver({})
        parent = r.get_parent_dir(str(tmp_path / "sub" / "term.json"))
        assert parent == tmp_path / "sub"


# ---------------------------------------------------------------------------
# StringHeuristics
# ---------------------------------------------------------------------------

class TestStringHeuristics:
    def test_short_simple_id_is_resolvable(self):
        h = StringHeuristics()
        assert h.is_resolvable("hadgem3_gc31_atmosphere") is True

    def test_string_with_space_not_resolvable(self):
        h = StringHeuristics()
        assert h.is_resolvable("has a space") is False

    def test_string_with_dot_not_resolvable(self):
        h = StringHeuristics()
        assert h.is_resolvable("file.json") is False

    def test_too_long_not_resolvable(self):
        h = StringHeuristics(max_length=10)
        assert h.is_resolvable("this_is_longer_than_ten") is False

    def test_http_url_not_resolvable(self):
        h = StringHeuristics()
        assert h.is_resolvable("https://doi.org/10.5194") is False

    def test_should_skip_literal_with_value(self):
        h = StringHeuristics()
        assert h.should_skip_literal({"@value": "some text"}) is True

    def test_should_skip_literal_with_id(self):
        h = StringHeuristics()
        assert h.should_skip_literal({"@id": "https://example.com/term"}) is False

    def test_has_id_in_expanded_true(self):
        h = StringHeuristics()
        assert h.has_id_in_expanded({"@id": "https://example.com/term"}) is True

    def test_has_id_in_expanded_false(self):
        h = StringHeuristics()
        assert h.has_id_in_expanded({"@value": "literal"}) is False


# ---------------------------------------------------------------------------
# TermCache
# ---------------------------------------------------------------------------

class TestTermCache:
    def test_get_returns_none_when_empty(self):
        cache = TermCache()
        assert cache.get("https://example.com/term") is None

    def test_put_and_get(self):
        cache = TermCache()
        cache.put("key", {"id": "val"})
        assert cache.get("key") == {"id": "val"}

    def test_disabled_cache_get_returns_none(self):
        cache = TermCache(enabled=False)
        cache.put("key", {"id": "val"})
        assert cache.get("key") is None

    def test_evicts_oldest_when_full(self):
        cache = TermCache(max_size=2)
        cache.put("a", {})
        cache.put("b", {})
        cache.put("c", {})  # evicts "a"
        assert cache.get("a") is None
        assert cache.get("b") is not None

    def test_stats_tracks_hits_and_misses(self):
        cache = TermCache()
        cache.put("k", {})
        cache.get("k")   # hit
        cache.get("x")   # miss
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_clear_resets(self):
        cache = TermCache()
        cache.put("k", {})
        cache.clear()
        assert cache.get("k") is None
        assert cache.get_stats()["size"] == 0

    def test_repr_contains_cache_info(self):
        cache = TermCache(max_size=10)
        assert "TermCache" in repr(cache)
        assert "10" in repr(cache)


# ---------------------------------------------------------------------------
# ResolverConfig
# ---------------------------------------------------------------------------

class TestResolverConfig:
    def test_defaults(self):
        c = ResolverConfig()
        assert c.max_depth == 5
        assert c.enable_caching is True
        assert c.max_string_length == 200

    def test_invalid_max_depth_raises(self):
        with pytest.raises(ValueError, match="max_depth"):
            ResolverConfig(max_depth=0)

    def test_invalid_max_string_length_raises(self):
        with pytest.raises(ValueError, match="max_string_length"):
            ResolverConfig(max_string_length=0)

    def test_invalid_cache_size_raises(self):
        with pytest.raises(ValueError, match="cache_size"):
            ResolverConfig(cache_size=0)

    def test_missing_links_tracker_default_none(self):
        assert ResolverConfig().missing_links_tracker is None


# ---------------------------------------------------------------------------
# DataMerger.__init__
# ---------------------------------------------------------------------------

class TestDataMergerInit:
    def _mock_resource(self):
        r = MagicMock(spec=JsonLdResource)
        r.uri = "http://example.com/fake"
        return r

    def test_default_allowed_base_uris(self):
        dm = DataMerger(data=self._mock_resource())
        assert "https://espri-mod.github.io/mip-cmor-tables" in dm.allowed_base_uris

    def test_none_locally_available_becomes_empty_dict(self):
        dm = DataMerger(data=self._mock_resource(), locally_available=None)
        assert dm.locally_available == {}

    def test_custom_allowed_base_uris(self):
        dm = DataMerger(data=self._mock_resource(), allowed_base_uris={"https://my.base/"})
        assert dm.allowed_base_uris == {"https://my.base/"}

    def test_custom_config_used(self):
        cfg = ResolverConfig(max_depth=10)
        dm = DataMerger(data=self._mock_resource(), config=cfg)
        assert dm.config.max_depth == 10

    def test_default_config_created_when_none(self):
        dm = DataMerger(data=self._mock_resource(), config=None)
        assert dm.config is not None
        assert isinstance(dm.config, ResolverConfig)


# ---------------------------------------------------------------------------
# DataMerger._should_resolve
# ---------------------------------------------------------------------------

class TestShouldResolve:
    def _merger(self, allowed_base_uris=None):
        r = MagicMock(spec=JsonLdResource)
        return DataMerger(data=r, allowed_base_uris=allowed_base_uris or {_EXAMPLE_BASE})

    def test_matching_uri_returns_true(self):
        dm = self._merger()
        assert dm._should_resolve(_EXAMPLE_BASE + "activity/cmip") is True

    def test_non_matching_uri_returns_false(self):
        dm = self._merger()
        assert dm._should_resolve("https://other.example.com/data") is False

    def test_exact_prefix_match(self):
        dm = self._merger({"https://exact.com/"})
        assert dm._should_resolve("https://exact.com/path") is True
        assert dm._should_resolve("https://exact2.com/path") is False


# ---------------------------------------------------------------------------
# DataMerger._get_next_id
# ---------------------------------------------------------------------------

class TestGetNextId:
    def _merger(self):
        r = MagicMock(spec=JsonLdResource)
        return DataMerger(data=r, allowed_base_uris={_EXAMPLE_BASE})

    def test_no_id_returns_none(self):
        dm = self._merger()
        assert dm._get_next_id({"type": "activity"}) is None

    def test_id_not_in_allowed_returns_none(self):
        dm = self._merger()
        assert dm._get_next_id({"@id": "https://other.com/term"}) is None

    def test_id_in_allowed_returns_uri(self):
        dm = self._merger()
        result = dm._get_next_id({"@id": _EXAMPLE_BASE + "activity/cmip"})
        assert result == _EXAMPLE_BASE + "activity/cmip.json"

    def test_appends_json_extension(self):
        dm = self._merger()
        result = dm._get_next_id({"@id": _EXAMPLE_BASE + "activity/cmip"})
        assert result.endswith(".json")

    def test_list_input_unwrapped(self):
        dm = self._merger()
        result = dm._get_next_id([{"@id": _EXAMPLE_BASE + "activity/cmip"}])
        assert result is not None

    def test_self_reference_returns_none(self):
        dm = self._merger()
        uri = _EXAMPLE_BASE + "activity/cmip.json"
        result = dm._get_next_id({"@id": _EXAMPLE_BASE + "activity/cmip"}, current_uri=uri)
        assert result is None


# ---------------------------------------------------------------------------
# DataMerger._get_resolve_mode
# ---------------------------------------------------------------------------

class TestGetResolveMode:
    def test_no_context_attr_returns_full(self):
        r = MagicMock(spec=JsonLdResource)
        del r.context  # ensure hasattr returns False
        dm = DataMerger(data=r)
        assert dm._get_resolve_mode("any_field") == "full"

    def test_no_resolve_modes_in_context_returns_full(self):
        r = JsonLdResource(uri=str(_ACTIVITY_CMIP))
        dm = DataMerger(data=r)
        assert dm._get_resolve_mode("type") == "full"

    def test_custom_resolve_mode_returned(self):
        r = MagicMock(spec=JsonLdResource)
        r.context = {"esgvoc_resolve_modes": {"model_components": "shallow"}}
        dm = DataMerger(data=r)
        assert dm._get_resolve_mode("model_components") == "shallow"

    def test_key_not_in_resolve_modes_returns_full(self):
        r = MagicMock(spec=JsonLdResource)
        r.context = {"esgvoc_resolve_modes": {"other_field": "reference"}}
        dm = DataMerger(data=r)
        assert dm._get_resolve_mode("unknown_field") == "full"


# ---------------------------------------------------------------------------
# DataMerger.merge_linked_json — no chaining (URI not in allowed_base_uris)
# ---------------------------------------------------------------------------

class TestMergeLinkedJsonNoChaining:
    def test_returns_list_with_single_element_when_no_chain(self):
        """Default allowed_base_uris doesn't match example.com → no chaining."""
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            allowed_base_uris={"https://espri-mod.github.io/"},  # doesn't match fixture
        )
        result = dm.merge_linked_json()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "cmip"

    def test_returns_original_json_dict(self):
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            allowed_base_uris={"https://espri-mod.github.io/"},
        )
        result = dm.merge_linked_json()
        assert result[0]["type"] == "activity"


# ---------------------------------------------------------------------------
# DataMerger.merge_linked_json — with local chaining (self-referential)
# ---------------------------------------------------------------------------

class TestMergeLinkedJsonWithChaining:
    def test_self_referential_chain_terminates(self):
        """
        cmip.json expands to @id=https://example.com/universe/activity/cmip.
        With allowed_base_uris matching and locally_available mapping, the merger
        follows the chain, finds cmip.json again (self-ref), and stops.
        """
        dm = _merger_for(_ACTIVITY_CMIP)
        result = dm.merge_linked_json()
        # Self-referential: original + one merge iteration → 2 items
        assert len(result) >= 1
        # Final result still contains the cmip data
        assert result[-1]["id"] == "cmip"

    def test_merge_module_function(self):
        """The module-level merge() function works without error on a local file."""
        # merge() uses default allowed_base_uris which won't match fixture → no chain
        result = merge(str(_ACTIVITY_CMIP))
        assert "id" in result
        assert result["id"] == "cmip"


# ---------------------------------------------------------------------------
# DataMerger.resolve_nested_ids — dict and list branches
# ---------------------------------------------------------------------------

class TestResolveNestedIdsContainers:
    def test_plain_dict_no_ids_returned_unchanged(self):
        dm = _merger_for(_ACTIVITY_CMIP)
        data = {"name": "test", "value": 42}
        result = dm.resolve_nested_ids(data)
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_list_with_matching_expanded_processed(self):
        dm = _merger_for(_ACTIVITY_CMIP)
        data = ["a", "b"]
        expanded = ["a_exp", "b_exp"]
        result = dm.resolve_nested_ids(data, expanded_data=expanded, _is_root_call=False)
        assert result == ["a", "b"]

    def test_list_without_expanded_each_item_processed(self):
        dm = _merger_for(_ACTIVITY_CMIP)
        result = dm.resolve_nested_ids(["hello", 42], expanded_data=None, _is_root_call=False)
        assert result == ["hello", 42]

    def test_primitive_int_returned_unchanged(self):
        dm = _merger_for(_ACTIVITY_CMIP)
        assert dm.resolve_nested_ids(42, _is_root_call=False) == 42

    def test_none_returned_unchanged(self):
        dm = _merger_for(_ACTIVITY_CMIP)
        assert dm.resolve_nested_ids(None, _is_root_call=False) is None

    def test_empty_string_returned_unchanged(self):
        dm = _merger_for(_ACTIVITY_CMIP)
        assert dm.resolve_nested_ids("", expanded_data={"@id": "x"}, _is_root_call=False) == ""

    def test_whitespace_string_returned_unchanged(self):
        dm = _merger_for(_ACTIVITY_CMIP)
        assert dm.resolve_nested_ids("   ", expanded_data={"@id": "x"}, _is_root_call=False) == "   "


# ---------------------------------------------------------------------------
# DataMerger.resolve_nested_ids — string primitive branches
# ---------------------------------------------------------------------------

class TestResolveNestedIdsPrimitiveString:
    """Test the primitive string resolution branches."""

    def _dm(self) -> DataMerger:
        return _merger_for(_ACTIVITY_CMIP)

    def test_literal_string_skipped(self):
        """@value in expanded → literal, skip resolution."""
        dm = self._dm()
        result = dm.resolve_nested_ids(
            "some text",
            expanded_data={"@value": "some text"},
            _is_root_call=False,
        )
        assert result == "some text"

    def test_no_id_in_expanded_skipped(self):
        """expanded_data has no @id → return as-is."""
        dm = self._dm()
        result = dm.resolve_nested_ids(
            "plain",
            expanded_data={"@type": "http://schema.org/Text"},
            _is_root_call=False,
        )
        assert result == "plain"

    def test_uri_not_in_allowed_base_skipped(self):
        """URI doesn't match allowed_base_uris → return as-is."""
        dm = self._dm()
        result = dm.resolve_nested_ids(
            "myterm",
            expanded_data={"@id": "https://other.com/universe/myterm"},
            _is_root_call=False,
        )
        assert result == "myterm"

    def test_string_fails_heuristic_too_long(self):
        """String longer than max_string_length → return as-is."""
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            allowed_base_uris={_EXAMPLE_BASE},
            locally_available={_EXAMPLE_BASE: str(_FIXTURES) + "/"},
            config=ResolverConfig(max_string_length=5),
        )
        long_id = "toolong"  # 7 chars > max 5
        result = dm.resolve_nested_ids(
            long_id,
            expanded_data={"@id": _EXAMPLE_BASE + "activity/" + long_id},
            _is_root_call=False,
        )
        assert result == long_id

    def test_string_fails_heuristic_has_space(self):
        """String with a space → not resolvable."""
        dm = self._dm()
        result = dm.resolve_nested_ids(
            "has space",
            expanded_data={"@id": _EXAMPLE_BASE + "activity/has space"},
            _is_root_call=False,
        )
        assert result == "has space"

    def test_max_depth_exceeded_returns_data(self):
        """Visited set larger than max_depth → return data."""
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            allowed_base_uris={_EXAMPLE_BASE},
            locally_available={_EXAMPLE_BASE: str(_FIXTURES) + "/"},
            config=ResolverConfig(max_depth=2),
        )
        large_visited = {f"https://example.com/uri{i}" for i in range(10)}
        result = dm.resolve_nested_ids(
            "cmip",
            expanded_data={"@id": _EXAMPLE_BASE + "activity/cmip"},
            visited=large_visited,
            _is_root_call=False,
        )
        assert result == "cmip"

    def test_circular_reference_returns_data(self):
        """URI already in visited → return data."""
        dm = self._dm()
        uri = _EXAMPLE_BASE + "activity/cmip.json"
        result = dm.resolve_nested_ids(
            "cmip",
            expanded_data={"@id": _EXAMPLE_BASE + "activity/cmip"},
            visited={uri},
            _is_root_call=False,
        )
        assert result == "cmip"

    def test_file_not_found_returns_data_unchanged(self):
        """File doesn't exist → warning logged, return original string."""
        dm = self._dm()
        result = dm.resolve_nested_ids(
            "nonexistent_term",
            expanded_data={"@id": _EXAMPLE_BASE + "activity/nonexistent_term"},
            _is_root_call=False,
        )
        assert result == "nonexistent_term"

    def test_file_not_found_reports_to_tracker(self):
        """When tracker configured, missing link is reported."""
        mock_tracker = MagicMock()
        config = ResolverConfig(missing_links_tracker=mock_tracker)
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            allowed_base_uris={_EXAMPLE_BASE},
            locally_available={_EXAMPLE_BASE: str(_FIXTURES) + "/"},
            config=config,
        )
        dm.resolve_nested_ids(
            "missing_term",
            expanded_data={"@id": _EXAMPLE_BASE + "activity/missing_term"},
            _is_root_call=False,
        )
        mock_tracker.add_from_params.assert_called_once()

    def test_reference_mode_keeps_string_when_file_missing(self):
        """resolve_mode='reference': validate but keep as string even if missing."""
        dm = self._dm()
        result = dm.resolve_nested_ids(
            "missing_term",
            expanded_data={"@id": _EXAMPLE_BASE + "activity/missing_term"},
            _is_root_call=False,
            resolve_mode="reference",
        )
        assert result == "missing_term"

    def test_file_found_resolves_to_object(self):
        """piControl.json exists → string resolved to full object."""
        dm = _merger_for(_EXPERIMENT_HISTORICAL)
        result = dm.resolve_nested_ids(
            "piControl",
            expanded_data={"@id": _EXAMPLE_BASE + "experiment/piControl"},
            _is_root_call=False,
        )
        # Should be a dict (the resolved term), not the original string
        assert isinstance(result, dict)
        assert result.get("id") == "piControl"

    def test_shallow_mode_resolves_but_no_recursion(self):
        """resolve_mode='shallow': return resolved object without recursing."""
        dm = _merger_for(_EXPERIMENT_HISTORICAL)
        result = dm.resolve_nested_ids(
            "piControl",
            expanded_data={"@id": _EXAMPLE_BASE + "experiment/piControl"},
            _is_root_call=False,
            resolve_mode="shallow",
        )
        assert isinstance(result, dict)
        assert result.get("id") == "piControl"


# ---------------------------------------------------------------------------
# DataMerger.resolve_nested_ids — single-@id dict branch
# ---------------------------------------------------------------------------

class TestResolveNestedIdsIdDict:
    """Tests for data = {"@id": "some_id"} with single key."""

    def test_id_dict_not_in_allowed_returns_unchanged(self):
        dm = _merger_for(_ACTIVITY_CMIP)
        data = {"@id": "https://other.com/term"}
        expanded = {"@id": "https://other.com/term"}
        result = dm.resolve_nested_ids(data, expanded_data=expanded, _is_root_call=False)
        assert result == data

    def test_id_dict_circular_ref_returns_unchanged(self):
        dm = _merger_for(_ACTIVITY_CMIP)
        uri = _EXAMPLE_BASE + "activity/cmip.json"
        data = {"@id": _EXAMPLE_BASE + "activity/cmip"}
        expanded = {"@id": _EXAMPLE_BASE + "activity/cmip"}
        result = dm.resolve_nested_ids(data, expanded_data=expanded, visited={uri}, _is_root_call=False)
        assert result == data

    def test_id_dict_resolves_to_object(self):
        """File exists → @id dict resolved to full object."""
        dm = _merger_for(_EXPERIMENT_HISTORICAL)
        data = {"@id": _EXAMPLE_BASE + "experiment/piControl"}
        expanded = {"@id": _EXAMPLE_BASE + "experiment/piControl"}
        result = dm.resolve_nested_ids(data, expanded_data=expanded, _is_root_call=False)
        assert isinstance(result, dict)
        assert result.get("id") == "piControl"

    def test_id_dict_file_not_found_returns_data(self):
        dm = _merger_for(_ACTIVITY_CMIP)
        data = {"@id": _EXAMPLE_BASE + "activity/nonexistent"}
        expanded = {"@id": _EXAMPLE_BASE + "activity/nonexistent"}
        result = dm.resolve_nested_ids(data, expanded_data=expanded, _is_root_call=False)
        assert result == data

    def test_id_dict_exception_returns_data(self):
        """Exception during resolution → return original data."""
        dm = _merger_for(_ACTIVITY_CMIP)
        data = {"@id": _EXAMPLE_BASE + "activity/cmip"}
        expanded = {"@id": _EXAMPLE_BASE + "activity/cmip"}
        with patch("esgvoc.core.service.data_merger.JsonLdResource", side_effect=RuntimeError("boom")):
            result = dm.resolve_nested_ids(data, expanded_data=expanded, _is_root_call=False)
        assert result == data


# ---------------------------------------------------------------------------
# DataMerger.resolve_nested_ids_in_dict (module-level wrapper)
# ---------------------------------------------------------------------------

class TestResolveNestedIdsInDict:
    def test_delegates_to_merger(self):
        dm = _merger_for(_ACTIVITY_CMIP)
        data = {"name": "test", "value": 42}
        result = resolve_nested_ids_in_dict(data, dm)
        assert result["name"] == "test"


# ---------------------------------------------------------------------------
# DataMerger._deep_merge_contexts
# ---------------------------------------------------------------------------

class TestDeepMergeContexts:
    def _dm(self):
        return DataMerger(data=MagicMock(spec=JsonLdResource))

    def test_base_keys_preserved(self):
        dm = self._dm()
        base = {"@context": {"key1": "val1"}, "other": "x"}
        overlay = {"@context": {"key2": "val2"}}
        result = dm._deep_merge_contexts(base, overlay)
        assert result["other"] == "x"
        assert result["@context"]["key1"] == "val1"
        assert result["@context"]["key2"] == "val2"

    def test_overlay_at_context_overrides_base(self):
        dm = self._dm()
        base = {"@context": {"shared": "base_val", "base_only": "b"}}
        overlay = {"@context": {"shared": "overlay_val"}}
        result = dm._deep_merge_contexts(base, overlay)
        assert result["@context"]["shared"] == "overlay_val"
        assert result["@context"]["base_only"] == "b"

    def test_merge_esgvoc_resolve_modes(self):
        dm = self._dm()
        base = {"esgvoc_resolve_modes": {"field1": "full"}}
        overlay = {"esgvoc_resolve_modes": {"field2": "shallow"}}
        result = dm._deep_merge_contexts(base, overlay)
        assert result["esgvoc_resolve_modes"]["field1"] == "full"
        assert result["esgvoc_resolve_modes"]["field2"] == "shallow"

    def test_overlay_esgvoc_resolve_modes_override_base(self):
        dm = self._dm()
        base = {"esgvoc_resolve_modes": {"f": "full"}}
        overlay = {"esgvoc_resolve_modes": {"f": "shallow"}}
        result = dm._deep_merge_contexts(base, overlay)
        assert result["esgvoc_resolve_modes"]["f"] == "shallow"

    def test_empty_overlay_returns_copy_of_base(self):
        dm = self._dm()
        base = {"@context": {"k": "v"}, "esgvoc_resolve_modes": {"f": "full"}}
        result = dm._deep_merge_contexts(base, {})
        assert result == base

    def test_at_context_created_when_missing_from_base(self):
        dm = self._dm()
        result = dm._deep_merge_contexts({}, {"@context": {"k": "v"}})
        assert result["@context"] == {"k": "v"}

    def test_esgvoc_resolve_modes_created_when_missing_from_base(self):
        dm = self._dm()
        result = dm._deep_merge_contexts({}, {"esgvoc_resolve_modes": {"f": "shallow"}})
        assert result["esgvoc_resolve_modes"]["f"] == "shallow"


# ---------------------------------------------------------------------------
# DataMerger.resolve_merged_ids — fallback paths
# ---------------------------------------------------------------------------

class TestResolveMergedIdsFallbacks:
    def test_no_locally_available_falls_back(self):
        """No locally_available mapping → falls back to resolve_nested_ids."""
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            locally_available={},
        )
        merged_data = {"id": "cmip", "type": "activity", "description": "test"}
        result = dm.resolve_merged_ids(merged_data)
        assert result["id"] == "cmip"

    def test_no_data_descriptor_falls_back(self):
        """Missing 'type' field → falls back to resolve_nested_ids."""
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            locally_available={_EXAMPLE_BASE: str(_FIXTURES) + "/"},
        )
        merged_data = {"id": "cmip"}  # no "type"
        result = dm.resolve_merged_ids(
            merged_data,
            context_base_path=str(_FIXTURES),
        )
        assert result["id"] == "cmip"

    def test_context_dir_not_found_falls_back(self):
        """Primary context dir doesn't exist → falls back."""
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            locally_available={_EXAMPLE_BASE: str(_FIXTURES) + "/"},
        )
        merged_data = {"id": "cmip", "type": "nonexistent_type"}
        result = dm.resolve_merged_ids(
            merged_data,
            context_base_path=str(_FIXTURES),
        )
        assert result["id"] == "cmip"

    def test_with_real_context_dir(self):
        """activity/ context dir exists → creates temp files, expands, resolves."""
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            locally_available={_EXAMPLE_BASE: str(_FIXTURES) + "/"},
        )
        merged_data = {
            "@context": "000_context.jsonld",
            "id": "cmip",
            "type": "activity",
            "description": "test",
        }
        result = dm.resolve_merged_ids(
            merged_data,
            context_base_path=str(_FIXTURES),
        )
        assert isinstance(result, dict)
        assert "id" in result or "type" in result  # some fields preserved

    def test_with_fallback_context_dir(self):
        """Fallback context path used when primary doesn't have the dir."""
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            locally_available={_EXAMPLE_BASE: str(_FIXTURES) + "/"},
        )
        merged_data = {"id": "cmip", "type": "activity", "description": "test"}
        # primary_context_path: something that doesn't have activity/
        # fallback: _FIXTURES which does
        import tempfile
        with tempfile.TemporaryDirectory() as no_ctx_dir:
            result = dm.resolve_merged_ids(
                merged_data,
                context_base_path=no_ctx_dir,
                fallback_context_base_path=str(_FIXTURES),
            )
        assert isinstance(result, dict)

    def test_locally_available_universe_key_infers_base_path(self):
        """When locally_available has the universe key, use it as context_base_path."""
        universe_key = "https://esgvoc.ipsl.fr/resource/universe"
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            locally_available={universe_key: str(_FIXTURES)},
        )
        merged_data = {"id": "cmip", "type": "activity", "description": "test"}
        result = dm.resolve_merged_ids(merged_data)
        assert isinstance(result, dict)

    def test_locally_available_other_key_infers_base_path(self):
        """When locally_available has only non-universe keys, use first value."""
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            locally_available={"https://some.other/": str(_FIXTURES)},
        )
        merged_data = {"id": "cmip", "type": "activity", "description": "test"}
        result = dm.resolve_merged_ids(merged_data)
        assert isinstance(result, dict)

    def test_bad_fallback_context_file_skipped_gracefully(self, tmp_path):
        """Invalid JSON in fallback context file is silently skipped (lines 636-637)."""
        # Fallback dir has bad context; primary (_FIXTURES) has valid context
        fallback_dir = tmp_path / "fallback"
        (fallback_dir / "activity").mkdir(parents=True)
        (fallback_dir / "activity" / "000_context.jsonld").write_text("not valid json{{{")
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            locally_available={},
        )
        merged_data = {"id": "cmip", "type": "activity"}
        result = dm.resolve_merged_ids(
            merged_data,
            context_base_path=str(_FIXTURES),
            fallback_context_base_path=str(fallback_dir),
        )
        assert isinstance(result, dict)

    def test_bad_primary_context_file_skipped_gracefully(self, tmp_path):
        """Invalid JSON in primary context file is silently skipped (lines 648-649)."""
        # Primary dir has bad context; fallback (_FIXTURES) has valid context
        primary_dir = tmp_path / "primary"
        (primary_dir / "activity").mkdir(parents=True)
        (primary_dir / "activity" / "000_context.jsonld").write_text("bad{{{json")
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            locally_available={},
        )
        merged_data = {"id": "cmip", "type": "activity"}
        result = dm.resolve_merged_ids(
            merged_data,
            context_base_path=str(primary_dir),
            fallback_context_base_path=str(_FIXTURES),
        )
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# resolve_nested_ids — additional branch coverage
# ---------------------------------------------------------------------------

class TestResolveNestedIdsAdditionalBranches:
    """Cover the remaining branches: expanded_data list unwrap, context key lookup,
    OSError path, and exception-during-resolution path."""

    def test_root_call_with_single_element_expanded_list(self):
        """Line 242: expanded_data=[{...}] on root call → unwrap the list."""
        dm = _merger_for(_ACTIVITY_CMIP)
        data = {"name": "test"}
        # Pass expanded_data as a single-element list on the root call
        result = dm.resolve_nested_ids(data, expanded_data=[{"name_expanded": "x"}])
        assert result["name"] == "test"

    def test_context_key_lookup_id_exact_match(self):
        """Lines 335-341: compact key not found by URI suffix; context @id matches exactly."""
        r = MagicMock(spec=JsonLdResource)
        r.uri = "http://fake"
        # Context maps "required_model_components" → @id "source_type/"
        r.context = {
            "@context": {
                "required_model_components": {"@id": "source_type/", "@type": "@id"}
            }
        }
        dm = DataMerger(data=r, allowed_base_uris={_EXAMPLE_BASE})
        # expanded_data key is "source_type/" — found by context lookup
        expanded = {"source_type/": [{"@id": _EXAMPLE_BASE + "activity/cmip"}]}
        result = dm.resolve_nested_ids(
            {"required_model_components": "some_value"},
            expanded_data=expanded,
            _is_root_call=False,
        )
        # The value should be processed (in this case, string heuristics skip it since it has _)
        assert "required_model_components" in result

    def test_context_key_lookup_id_trailing_slash(self):
        """Lines 342-343: context @id without trailing slash; expanded has trailing slash."""
        r = MagicMock(spec=JsonLdResource)
        r.uri = "http://fake"
        r.context = {
            "@context": {
                "myfield": {"@id": "source_type", "@type": "@id"}
            }
        }
        dm = DataMerger(data=r, allowed_base_uris={_EXAMPLE_BASE})
        # expanded_data key is "source_type/" — found via rstrip("/") + "/"
        expanded = {"source_type/": [{"@id": _EXAMPLE_BASE + "activity/cmip"}]}
        result = dm.resolve_nested_ids(
            {"myfield": "some_value"},
            expanded_data=expanded,
            _is_root_call=False,
        )
        assert "myfield" in result

    def test_context_key_lookup_id_without_slash(self):
        """Lines 344-345: context @id without slash; expanded key matches without slash."""
        r = MagicMock(spec=JsonLdResource)
        r.uri = "http://fake"
        r.context = {
            "@context": {
                "myfield": {"@id": "source_type", "@type": "@id"}
            }
        }
        dm = DataMerger(data=r, allowed_base_uris={_EXAMPLE_BASE})
        expanded = {"source_type": [{"@id": _EXAMPLE_BASE + "activity/cmip"}]}
        result = dm.resolve_nested_ids(
            {"myfield": "some_value"},
            expanded_data=expanded,
            _is_root_call=False,
        )
        assert "myfield" in result

    def test_oserror_in_uri_check_returns_data(self):
        """Lines 483-504: OSError during uri_resolver.exists → return data."""
        dm = _merger_for(_ACTIVITY_CMIP)
        with patch.object(dm.uri_resolver, "exists", side_effect=OSError("permission denied")):
            result = dm.resolve_nested_ids(
                "cmip",
                expanded_data={"@id": _EXAMPLE_BASE + "activity/cmip"},
                _is_root_call=False,
            )
        assert result == "cmip"

    def test_oserror_with_tracker_reports_missing_link(self):
        """Lines 495-503: OSError with tracker configured → tracker.add_from_params called."""
        mock_tracker = MagicMock()
        config = ResolverConfig(missing_links_tracker=mock_tracker)
        dm = DataMerger(
            data=JsonLdResource(uri=str(_ACTIVITY_CMIP)),
            allowed_base_uris={_EXAMPLE_BASE},
            locally_available={_EXAMPLE_BASE: str(_FIXTURES) + "/"},
            config=config,
        )
        with patch.object(dm.uri_resolver, "exists", side_effect=OSError("io error")):
            dm.resolve_nested_ids(
                "cmip",
                expanded_data={"@id": _EXAMPLE_BASE + "activity/cmip"},
                _is_root_call=False,
            )
        mock_tracker.add_from_params.assert_called_once()

    def test_exception_during_resolution_returns_data(self):
        """Lines 550-561: exception during actual resolution (after file found)."""
        dm = _merger_for(_EXPERIMENT_HISTORICAL)
        # Patch JsonLdResource to succeed on exists() check but fail during actual resolution
        with patch.object(dm.uri_resolver, "exists", return_value=True), \
             patch("esgvoc.core.service.data_merger.JsonLdResource", side_effect=RuntimeError("load failed")):
            result = dm.resolve_nested_ids(
                "piControl",
                expanded_data={"@id": _EXAMPLE_BASE + "experiment/piControl"},
                _is_root_call=False,
            )
        assert result == "piControl"
