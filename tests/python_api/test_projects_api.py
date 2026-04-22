"""
Tests for esgvoc.api.projects — uses real cmip7@v1.0.0 and universe@v1.0.0.

Marked `needs_db`: network is only required on the very first run to download
the DBs.  Once installed (ESGVOC_HOME set with the DBs present) tests run offline.
"""

from typing import TYPE_CHECKING
import pytest

pytestmark = pytest.mark.needs_db


class TestGetAllProjects:
    def test_returns_nonempty(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_all_projects()
        assert len(result) > 0
        assert all(isinstance(p, str) for p in result)

    def test_includes_cmip7(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_all_projects()
        assert "cmip7" in result


class TestGetProject:
    def test_get_cmip7(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_project("cmip7")
        assert result is not None

    def test_unknown_project_returns_none(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_project("nonexistent_project_xyz")
        assert result is None

    def test_version_param(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_project("cmip7", version="v1.0.0")
        assert result is not None


class TestGetAllCollections:
    def test_returns_collections_for_cmip7(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        assert isinstance(collections, list)
        assert len(collections) > 0

    def test_unknown_project_returns_empty_or_raises(self, installed_dbs):
        import esgvoc.api.projects as projects
        from esgvoc.core.exceptions import EsgvocNotFoundError

        try:
            result = projects.get_all_collections_in_project("nonexistent_xyz")
            assert result == [] or result is None
        except EsgvocNotFoundError:
            pass


class TestGetAllTermsInProject:
    def test_returns_terms_for_cmip7(self, installed_dbs):
        import esgvoc.api.projects as projects

        terms = projects.get_all_terms_in_project("cmip7")
        assert isinstance(terms, list)
        assert len(terms) > 0

    def test_version_param_consistency(self, installed_dbs):
        import esgvoc.api.projects as projects

        terms_default = projects.get_all_terms_in_project("cmip7")
        terms_v1 = projects.get_all_terms_in_project("cmip7", version="v1.0.0")
        assert len(terms_default) == len(terms_v1)


class TestGetAllTermsInCollection:
    def test_returns_terms_in_collection(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        first_collection = collections[0]
        terms = projects.get_all_terms_in_collection("cmip7", first_collection)
        assert isinstance(terms, list)

    def test_unknown_collection_returns_empty(self, installed_dbs):
        import esgvoc.api.projects as projects

        terms = projects.get_all_terms_in_collection("cmip7", "nonexistent_collection_xyz")
        assert terms == [] or terms is None


class TestGetTermInProject:
    def test_get_known_term(self, installed_dbs):
        import esgvoc.api.projects as projects

        terms = projects.get_all_terms_in_project("cmip7")
        if not terms:
            pytest.skip("No terms in cmip7")
        first = terms[0]
        term_id = first.id if hasattr(first, "id") else first["id"]
        result = projects.get_term_in_project("cmip7", term_id, [])
        assert result is not None

    def test_unknown_term_returns_none(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_term_in_project("cmip7", "nonexistent_term_xyz", [])
        assert result is None


class TestValidation:
    def test_valid_term_in_project(self, installed_dbs):
        import esgvoc.api.projects as projects

        terms = projects.get_all_terms_in_project("cmip7")
        if not terms:
            pytest.skip("No terms in cmip7")
        first = terms[0]
        term_id = first.id if hasattr(first, "id") else first["id"]
        # Validate the term against itself — should match
        result = projects.valid_term_in_project(term_id, "cmip7")
        assert isinstance(result, list)

    def test_invalid_value_returns_empty(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.valid_term_in_project("this_value_definitely_does_not_exist_xyz_abc_123", "cmip7")
        assert result == []


class TestGetAllTermsInAllProjects:
    def test_returns_grouped_results(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_all_terms_in_all_projects()
        assert isinstance(result, list)
        # Should have at least cmip7
        assert len(result) >= 1


class TestGetTermInCollection:
    def test_get_known_term(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        first_collection = collections[0]
        terms = projects.get_all_terms_in_collection("cmip7", first_collection)
        if not terms:
            pytest.skip(f"No terms in cmip7/{first_collection}")
        first = terms[0]
        term_id = first.id if hasattr(first, "id") else first["id"]
        result = projects.get_term_in_collection("cmip7", first_collection, term_id, [])
        assert result is not None
        result_id = result.id if hasattr(result, "id") else result["id"]
        assert result_id == term_id

    def test_unknown_term_returns_none(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        first_collection = collections[0]
        result = projects.get_term_in_collection("cmip7", first_collection, "nonexistent_term_xyz", [])
        assert result is None

    def test_unknown_collection_returns_none(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_term_in_collection("cmip7", "nonexistent_collection_xyz", "any_term", [])
        assert result is None


class TestGetCollectionInProject:
    def test_get_known_collection(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        first_collection = collections[0]
        result = projects.get_collection_in_project("cmip7", first_collection)
        assert result is not None
        coll_id, coll_dict = result
        assert coll_id == first_collection
        assert isinstance(coll_dict, dict)

    def test_unknown_collection_returns_none(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_collection_in_project("cmip7", "nonexistent_collection_xyz")
        assert result is None

    def test_unknown_project_returns_none(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_collection_in_project("nonexistent_project_xyz", "any_collection")
        assert result is None


class TestGetCollectionFromDataDescriptor:
    def test_get_collection_from_dd_in_project(self, installed_dbs):
        import esgvoc.api.projects as projects

        # Discover a data descriptor that cmip7 uses
        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        # Try to find the data_descriptor for the first collection
        dd = projects.get_data_descriptor_from_collection_in_project("cmip7", collections[0])
        if dd is None:
            pytest.skip("First collection has no linked data descriptor")
            return
        result = projects.get_collection_from_data_descriptor_in_project("cmip7", dd)
        assert isinstance(result, list)
        assert len(result) > 0
        for coll_id, context in result:
            assert isinstance(coll_id, str)
            assert isinstance(context, dict)

    def test_unknown_dd_returns_empty(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_collection_from_data_descriptor_in_project("cmip7", "nonexistent_dd_xyz")
        assert result == [] or result is None

    def test_unknown_project_returns_empty_or_none(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_collection_from_data_descriptor_in_project("nonexistent_project_xyz", "institution")
        assert result == [] or result is None

    def test_get_collection_from_dd_in_all_projects(self, installed_dbs):
        import esgvoc.api.projects as projects

        # Discover a data descriptor that cmip7 uses
        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        dd = projects.get_data_descriptor_from_collection_in_project("cmip7", collections[0])
        if dd is None:
            pytest.skip("First collection has no linked data descriptor")
        result = projects.get_collection_from_data_descriptor_in_all_projects(dd)
        assert isinstance(result, list)
        # At minimum cmip7 should be in there
        assert len(result) >= 1
        for proj_id, coll_id, context in result:
            assert isinstance(proj_id, str)
            assert isinstance(coll_id, str)
            assert isinstance(context, dict)

    def test_unknown_dd_all_projects_returns_empty(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_collection_from_data_descriptor_in_all_projects("nonexistent_dd_xyz_abc")
        assert result == [] or result is None


class TestGetTermFromUniverseTermId:
    def test_get_term_from_universe_id_in_project(self, installed_dbs):
        import esgvoc.api.projects as projects

        # Discover a collection + term that links to the universe
        collections = projects.get_all_collections_in_project("cmip7")
        for coll in collections:
            dd = projects.get_data_descriptor_from_collection_in_project("cmip7", coll)
            if dd is None:
                continue
            terms = projects.get_all_terms_in_collection("cmip7", coll)
            if not terms:
                continue
            first_term_id = terms[0].id if hasattr(terms[0], "id") else terms[0]["id"]
            # Try looking up by universe term id
            result = projects.get_term_from_universe_term_id_in_project("cmip7", dd, first_term_id)
            if result is not None:
                found_coll_id, found_term = result
                assert isinstance(found_coll_id, str)
                assert found_term is not None
                return
        pytest.skip("No collection in cmip7 links to a universe data descriptor with accessible terms")

    def test_unknown_term_returns_none(self, installed_dbs):
        import esgvoc.api.projects as projects

        # institution is a common universe dd; nonexistent term should return None
        result = projects.get_term_from_universe_term_id_in_project("cmip7", "institution", "nonexistent_xyz_abc")
        assert result is None

    def test_get_term_from_universe_id_in_all_projects(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        for coll in collections:
            dd = projects.get_data_descriptor_from_collection_in_project("cmip7", coll)
            if dd is None:
                continue
            terms = projects.get_all_terms_in_collection("cmip7", coll)
            if not terms:
                continue
            first_term_id = terms[0].id if hasattr(terms[0], "id") else terms[0]["id"]
            result = projects.get_term_from_universe_term_id_in_all_projects(dd, first_term_id)
            if result:
                assert isinstance(result, list)
                return
        pytest.skip("No suitable universe-linked term found in cmip7")

    def test_unknown_term_all_projects_returns_empty(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_term_from_universe_term_id_in_all_projects("institution", "nonexistent_xyz_abc")
        assert result == [] or result is None


class TestValidTermFull:
    def test_valid_term_returns_report(self, installed_dbs):
        import esgvoc.api.projects as projects
        from esgvoc.api.report import ValidationReport

        # Get a known valid term from cmip7 and validate its drs_name if available
        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        for coll in collections:
            terms = projects.get_all_terms_in_collection("cmip7", coll)
            if terms:
                first = terms[0]
                first_term_id = first.id if hasattr(first, "id") else first["id"]
                # Try validating the drs_name if available (the real "value" that terms validate)
                value = None
                if hasattr(first, "drs_name") and first.drs_name:
                    value = str(first.drs_name)
                else:
                    value = first_term_id
                report = projects.valid_term(value, "cmip7", coll, first_term_id)
                assert isinstance(report, ValidationReport)
                assert isinstance(report.errors, list)
                assert hasattr(report, "nb_errors")
                return
        pytest.skip("No terms found in any cmip7 collection")

    def test_valid_term_with_errors(self, installed_dbs):
        import esgvoc.api.projects as projects
        from esgvoc.api.report import ValidationReport

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        for coll in collections:
            terms = projects.get_all_terms_in_collection("cmip7", coll)
            if terms:
                first_term_id = terms[0].id if hasattr(terms[0], "id") else terms[0]["id"]
                # Validate a nonsense value against a real term
                report = projects.valid_term(
                    "this_value_certainly_does_not_match_xyz_abc_123", "cmip7", coll, first_term_id
                )
                assert isinstance(report, ValidationReport)
                assert report.nb_errors >= 1
                return
        pytest.skip("No terms found in any cmip7 collection")

    def test_valid_term_in_all_projects(self, installed_dbs):
        import esgvoc.api.projects as projects

        # Valid matching value — should return >= 1 match
        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        for coll in collections:
            terms = projects.get_all_terms_in_collection("cmip7", coll)
            if terms:
                first_term_id = terms[0].id if hasattr(terms[0], "id") else terms[0]["id"]
                result = projects.valid_term_in_all_projects(first_term_id)
                assert isinstance(result, list)
                return
        pytest.skip("No terms found in any cmip7 collection")

    def test_valid_term_in_all_projects_no_match(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.valid_term_in_all_projects("this_value_certainly_does_not_match_xyz_123")
        assert result == []


class TestValidTermInCollection:
    def test_valid_term_in_collection_match(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        for coll in collections:
            terms = projects.get_all_terms_in_collection("cmip7", coll)
            if not terms:
                continue
            first = terms[0]
            # Use drs_name (the actual validated value) rather than term id
            if hasattr(first, "drs_name") and first.drs_name:
                value = str(first.drs_name)
                result = projects.valid_term_in_collection(value, "cmip7", coll)
                assert isinstance(result, list)
                assert len(result) >= 1
                return
        pytest.skip("No term with drs_name found in any cmip7 collection")

    def test_valid_term_in_collection_no_match(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        result = projects.valid_term_in_collection(
            "this_value_certainly_does_not_match_xyz_abc_123", "cmip7", collections[0]
        )
        assert result == []


class TestFindCollectionsInProject:
    def test_find_known_collection(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        first = collections[0]
        # Search by first few chars
        prefix = first[:3]
        results = projects.find_collections_in_project(prefix, "cmip7")
        assert results is not None
        assert len(results) > 0

    def test_find_no_match_returns_empty(self, installed_dbs):
        import esgvoc.api.projects as projects

        results = projects.find_collections_in_project("zzzzxqjk_nonexistent_xyz", "cmip7")
        assert results == [] or results is None

    def test_find_with_wildcard(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        # Use first char + wildcard
        prefix = collections[0][0] + "*"
        results = projects.find_collections_in_project(prefix, "cmip7")
        assert len(results) > 0

    def test_find_unknown_project_returns_empty(self, installed_dbs):
        import esgvoc.api.projects as projects

        results = projects.find_collections_in_project("institution", "nonexistent_project_xyz")
        assert results == [] or results is None


class TestFindTermsInCollection:
    def test_find_known_term(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        for coll in collections:
            terms = projects.get_all_terms_in_collection("cmip7", coll)
            if terms:
                first = terms[0]
                term_id = first.id if hasattr(first, "id") else first["id"]
                results = projects.find_terms_in_collection(term_id, "cmip7", coll, selected_term_fields=[])
                assert len(results) > 0
                return
        pytest.skip("No terms found in any cmip7 collection")

    def test_find_no_match_returns_empty(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        results = projects.find_terms_in_collection(
            "zzzzxqjk_nonexistent_xyz", "cmip7", collections[0], selected_term_fields=[]
        )
        assert results == [] or results is None

    def test_find_with_wildcard(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        for coll in collections:
            terms = projects.get_all_terms_in_collection("cmip7", coll)
            if terms and len(terms) > 1:
                first_term_id = terms[0].id if hasattr(terms[0], "id") else terms[0]["id"]
                prefix = first_term_id[:2] + "*"
                results = projects.find_terms_in_collection(prefix, "cmip7", coll, selected_term_fields=[])
                assert results is not None
                return
        pytest.skip("No collection with enough terms found in cmip7")


class TestFindTermsInProject:
    def test_find_known_term(self, installed_dbs):
        import esgvoc.api.projects as projects

        terms = projects.get_all_terms_in_project("cmip7")
        if not terms:
            pytest.skip("No terms in cmip7")
        first = terms[0]
        term_id = first.id if hasattr(first, "id") else first["id"]
        results = projects.find_terms_in_project(term_id, "cmip7", selected_term_fields=[])
        assert len(results) > 0

    def test_find_no_match_returns_empty(self, installed_dbs):
        import esgvoc.api.projects as projects

        results = projects.find_terms_in_project("zzzzxqjk_nonexistent_xyz", "cmip7", selected_term_fields=[])
        assert results == [] or results is None

    def test_find_with_wildcard(self, installed_dbs):
        import esgvoc.api.projects as projects

        terms = projects.get_all_terms_in_project("cmip7")
        if not terms:
            pytest.skip("No terms in cmip7")
        first_term_id = terms[0].id if hasattr(terms[0], "id") else terms[0]["id"]
        prefix = first_term_id[:3] + "*"
        results = projects.find_terms_in_project(prefix, "cmip7", selected_term_fields=[])
        assert results is not None


class TestFindTermsInAllProjects:
    def test_find_known_term(self, installed_dbs):
        import esgvoc.api.projects as projects

        terms = projects.get_all_terms_in_project("cmip7")
        if not terms:
            pytest.skip("No terms in cmip7")
        first_term_id = terms[0].id if hasattr(terms[0], "id") else terms[0]["id"]
        results = projects.find_terms_in_all_projects(first_term_id)
        assert isinstance(results, list)
        # Flatten and find the term
        all_found = []
        for _project_id, project_terms in results:
            all_found.extend(project_terms)
        assert len(all_found) > 0

    def test_find_no_match_returns_empty_groups(self, installed_dbs):
        import esgvoc.api.projects as projects

        results = projects.find_terms_in_all_projects("zzzzxqjk_nonexistent_xyz")
        # Each project group should have empty terms list
        all_found = []
        for _project_id, project_terms in results:
            all_found.extend(project_terms)
        assert all_found == []


class TestLimitOffset:
    def test_find_terms_with_limit(self, installed_dbs):
        import esgvoc.api.projects as projects

        terms = projects.get_all_terms_in_project("cmip7")
        if not terms:
            pytest.skip("No terms in cmip7")
        # Use a short prefix wildcard that matches multiple terms
        first_term_id = terms[0].id if hasattr(terms[0], "id") else terms[0]["id"]
        prefix = first_term_id[:2] + "*"
        results = projects.find_terms_in_project(prefix, "cmip7", limit=2, selected_term_fields=[])
        assert results is not None

    def test_find_terms_with_limit_and_offset_beyond_results(self, installed_dbs):
        import esgvoc.api.projects as projects

        terms = projects.get_all_terms_in_project("cmip7")
        if not terms:
            pytest.skip("No terms in cmip7")
        first_term_id = terms[0].id if hasattr(terms[0], "id") else terms[0]["id"]
        # offset beyond any result set
        results = projects.find_terms_in_project(
            first_term_id, "cmip7", only_id=True, limit=10, offset=9999, selected_term_fields=[]
        )
        assert not results

    def test_find_items_with_limit_and_offset(self, installed_dbs):
        import esgvoc.api.projects as projects

        terms = projects.get_all_terms_in_project("cmip7")
        if not terms:
            pytest.skip("No terms in cmip7")
        first_term_id = terms[0].id if hasattr(terms[0], "id") else terms[0]["id"]
        # Should not raise
        results = projects.find_items_in_project(first_term_id, "cmip7", limit=10, offset=5)
        assert results is not None


class TestFindItemsInProject:
    def test_find_term_item(self, installed_dbs):
        import esgvoc.api.projects as projects
        from esgvoc.api.search import ItemKind

        terms = projects.get_all_terms_in_project("cmip7")
        if not terms:
            pytest.skip("No terms in cmip7")
        first_term_id = terms[0].id if hasattr(terms[0], "id") else terms[0]["id"]
        results = projects.find_items_in_project(first_term_id, "cmip7")
        assert results is not None
        # Should include a TERM item
        term_items = [item for item in results if item.kind == ItemKind.TERM and item.id == first_term_id]
        assert len(term_items) > 0

    def test_find_collection_item(self, installed_dbs):
        import esgvoc.api.projects as projects
        from esgvoc.api.search import ItemKind

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        first_coll = collections[0]
        results = projects.find_items_in_project(first_coll, "cmip7")
        assert results is not None
        collection_items = [item for item in results if item.kind == ItemKind.COLLECTION]
        assert len(collection_items) > 0

    def test_find_no_match_returns_empty(self, installed_dbs):
        import esgvoc.api.projects as projects

        results = projects.find_items_in_project("zzzzxqjk_nonexistent_xyz", "cmip7")
        assert results == [] or results is None


class TestGetDataDescriptorFromCollection:
    def test_returns_string_for_known_collection(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        for coll in collections:
            dd = projects.get_data_descriptor_from_collection_in_project("cmip7", coll)
            if dd is not None:
                assert isinstance(dd, str)
                return
        pytest.skip("No collection in cmip7 has a linked data descriptor")

    def test_returns_none_for_unknown_collection(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_data_descriptor_from_collection_in_project("cmip7", "non_existent_collection_xyz")
        assert result is None

    def test_returns_none_for_unknown_project(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_data_descriptor_from_collection_in_project("non_existent_project_xyz", "any_collection")
        assert result is None


class TestGetTermsByKeyValue:
    def test_get_terms_in_collection_by_key_value(self, installed_dbs):
        import esgvoc.api.projects as projects

        # Discover a collection and key-value from cmip7 dynamically
        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        for coll in collections:
            terms = projects.get_all_terms_in_collection("cmip7", coll)
            if not terms:
                continue
            first = terms[0]
            # Try "drs_name" as a common key
            if hasattr(first, "drs_name") and first.drs_name:
                result = projects.get_terms_in_collection_by_key_value("cmip7", coll, "drs_name", str(first.drs_name))
                assert isinstance(result, list)
                assert len(result) >= 1
                return
        pytest.skip("No term with drs_name found in cmip7")

    def test_get_terms_in_collection_by_key_value_not_found(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        result = projects.get_terms_in_collection_by_key_value(
            "cmip7", collections[0], "drs_name", "NON_EXISTENT_VALUE_12345_XYZ"
        )
        assert result == []

    def test_get_terms_in_collection_by_key_value_invalid_project(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_terms_in_collection_by_key_value(
            "non_existent_project", "any_collection", "drs_name", "anyvalue"
        )
        assert result == []

    def test_get_terms_in_project_by_key_value(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        for coll in collections:
            terms = projects.get_all_terms_in_collection("cmip7", coll)
            if not terms:
                continue
            first = terms[0]
            if hasattr(first, "drs_name") and first.drs_name:
                result = projects.get_terms_in_project_by_key_value("cmip7", "drs_name", str(first.drs_name))
                assert isinstance(result, list)
                assert len(result) >= 1
                return
        pytest.skip("No term with drs_name found in cmip7")

    def test_get_terms_in_project_by_key_value_not_found(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_terms_in_project_by_key_value("cmip7", "drs_name", "NON_EXISTENT_VALUE_12345_XYZ")
        assert result == []

    def test_get_terms_in_all_projects_by_key_value(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        for coll in collections:
            terms = projects.get_all_terms_in_collection("cmip7", coll)
            if not terms:
                continue
            first = terms[0]
            if hasattr(first, "drs_name") and first.drs_name:
                results = projects.get_terms_in_all_projects_by_key_value("drs_name", str(first.drs_name))
                assert isinstance(results, list)
                # At least one project should have results
                total = sum(len(terms_list) for _, terms_list in results)
                assert total >= 1
                return
        pytest.skip("No term with drs_name found in cmip7")

    def test_get_terms_in_all_projects_by_key_value_not_found(self, installed_dbs):
        import esgvoc.api.projects as projects

        result = projects.get_terms_in_all_projects_by_key_value("drs_name", "NON_EXISTENT_VALUE_12345_XYZ")
        assert result == []

    def test_get_terms_in_collection_by_key_value_with_selected_fields(self, installed_dbs):
        import esgvoc.api.projects as projects

        collections = projects.get_all_collections_in_project("cmip7")
        if not collections:
            pytest.skip("No collections in cmip7")
        for coll in collections:
            terms = projects.get_all_terms_in_collection("cmip7", coll)
            if not terms:
                continue
            first = terms[0]
            if hasattr(first, "drs_name") and first.drs_name:
                result = projects.get_terms_in_collection_by_key_value(
                    "cmip7", coll, "drs_name", str(first.drs_name), selected_term_fields=[]
                )
                assert isinstance(result, list)
                assert len(result) >= 1
                return
        pytest.skip("No term with drs_name found in cmip7")
