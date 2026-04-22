"""
Tests for esgvoc.api.universe — uses real universe@v1.0.0 database.

Marked `needs_db`: network is only required on the very first run to download
the DB.  Once installed (ESGVOC_HOME set with the DB present) tests run offline.
"""
import pytest

pytestmark = pytest.mark.needs_db


class TestGetAllDataDescriptors:
    def test_returns_nonempty_list(self, installed_dbs):
        import esgvoc.api.universe as universe
        result = universe.get_all_data_descriptors_in_universe()
        assert len(result) > 0
        assert all(isinstance(dd, str) for dd in result)

    def test_includes_known_descriptor(self, installed_dbs):
        import esgvoc.api.universe as universe
        descriptors = universe.get_all_data_descriptors_in_universe()
        # universe should have at least 'institution' or similar
        assert len(descriptors) > 5


class TestGetAllTermsInUniverse:
    def test_returns_nonempty_list(self, installed_dbs):
        import esgvoc.api.universe as universe
        terms = universe.get_all_terms_in_universe()
        assert len(terms) > 0

    def test_selected_fields_subset(self, installed_dbs):
        import esgvoc.api.universe as universe
        terms_full = universe.get_all_terms_in_universe()
        terms_subset = universe.get_all_terms_in_universe(selected_term_fields=["id"])
        # Subset should return same count, each item having fewer fields
        assert len(terms_full) == len(terms_subset)


class TestGetDataDescriptor:
    def test_get_known_descriptor(self, installed_dbs):
        import esgvoc.api.universe as universe
        descriptors = universe.get_all_data_descriptors_in_universe()
        first = descriptors[0]
        result = universe.get_data_descriptor_in_universe(first)
        assert result is not None
        dd_id, dd_dict = result
        assert dd_id == first

    def test_unknown_descriptor_returns_none(self, installed_dbs):
        import esgvoc.api.universe as universe
        result = universe.get_data_descriptor_in_universe("nonexistent_descriptor_xyz")
        assert result is None


class TestGetTermInUniverse:
    def test_get_known_term(self, installed_dbs):
        import esgvoc.api.universe as universe
        terms = universe.get_all_terms_in_universe()
        assert len(terms) > 0
        first_term = terms[0]
        term_id = first_term.id if hasattr(first_term, "id") else first_term["id"]
        result = universe.get_term_in_universe(term_id)
        assert result is not None

    def test_unknown_term_returns_none(self, installed_dbs):
        import esgvoc.api.universe as universe
        result = universe.get_term_in_universe("nonexistent_term_xyz_abc")
        assert result is None


class TestGetAllTermsInDataDescriptor:
    def test_returns_list_for_known_descriptor(self, installed_dbs):
        import esgvoc.api.universe as universe
        descriptors = universe.get_all_data_descriptors_in_universe()
        first = descriptors[0]
        terms = universe.get_all_terms_in_data_descriptor(first)
        assert isinstance(terms, list)

    def test_returns_empty_for_unknown_descriptor(self, installed_dbs):
        import esgvoc.api.universe as universe
        terms = universe.get_all_terms_in_data_descriptor("nonexistent_xyz")
        assert terms == [] or terms is None


class TestGetTermInDataDescriptor:
    def test_get_term_by_data_descriptor(self, installed_dbs):
        import esgvoc.api.universe as universe
        # Use known stable term: activity/volmip
        term = universe.get_term_in_data_descriptor("activity", "volmip", [])
        assert term is not None
        term_id = term.id if hasattr(term, "id") else term["id"]
        assert term_id == "volmip"

    def test_unknown_term_in_descriptor_returns_none(self, installed_dbs):
        import esgvoc.api.universe as universe
        descriptors = universe.get_all_data_descriptors_in_universe()
        first = descriptors[0]
        result = universe.get_term_in_data_descriptor(first, "nonexistent_term_xyz_abc", [])
        assert result is None

    def test_unknown_descriptor_returns_none(self, installed_dbs):
        import esgvoc.api.universe as universe
        result = universe.get_term_in_data_descriptor("nonexistent_descriptor_xyz", "volmip", [])
        assert result is None


class TestFindTermsInUniverse:
    def test_find_returns_results(self, installed_dbs):
        import esgvoc.api.universe as universe
        terms = universe.get_all_terms_in_universe()
        if not terms:
            pytest.skip("No terms in universe DB")
        first = terms[0]
        term_id = first.id if hasattr(first, "id") else first["id"]
        # Search for the first few chars
        prefix = term_id[:3]
        results = universe.find_terms_in_universe(prefix)
        assert len(results) > 0

    def test_find_no_match_returns_empty(self, installed_dbs):
        import esgvoc.api.universe as universe
        results = universe.find_terms_in_universe("zzzzxqjk_nonexistent_xyz")
        assert results == [] or results is None

    def test_find_with_wildcard(self, installed_dbs):
        import esgvoc.api.universe as universe
        # "vol*" should find "volmip" in activity
        results = universe.find_terms_in_universe("vol*")
        assert len(results) > 0

    def test_find_with_selected_fields(self, installed_dbs):
        import esgvoc.api.universe as universe
        results = universe.find_terms_in_universe("volmip", selected_term_fields=[])
        assert len(results) > 0


class TestFindDataDescriptorsInUniverse:
    def test_find_known_descriptor(self, installed_dbs):
        import esgvoc.api.universe as universe
        # "institution" is a known data descriptor in the universe
        results = universe.find_data_descriptors_in_universe("institution")
        assert results is not None
        assert len(results) > 0

    def test_find_with_wildcard(self, installed_dbs):
        import esgvoc.api.universe as universe
        # "var*" should find "variable" data descriptor
        results = universe.find_data_descriptors_in_universe("var*")
        assert results is not None
        # should find at least the "variable" descriptor
        assert len(results) > 0

    def test_find_no_match_returns_empty(self, installed_dbs):
        import esgvoc.api.universe as universe
        results = universe.find_data_descriptors_in_universe("zzzzxqjk_nonexistent_xyz")
        assert results == [] or results is None

    def test_find_with_not_operator(self, installed_dbs):
        import esgvoc.api.universe as universe
        # "var* NOT ver*" — finds variable-like descriptors excluding version-like ones
        results = universe.find_data_descriptors_in_universe("var* NOT ver*")
        # May return results or empty; just ensure no crash
        assert results is not None


class TestFindTermsInDataDescriptor:
    def test_find_volmip_in_activity(self, installed_dbs):
        import esgvoc.api.universe as universe
        results = universe.find_terms_in_data_descriptor("volmip", "activity", selected_term_fields=[])
        assert len(results) > 0
        ids = [t.id if hasattr(t, "id") else t["id"] for t in results]
        assert "volmip" in ids

    def test_find_no_match_returns_empty(self, installed_dbs):
        import esgvoc.api.universe as universe
        results = universe.find_terms_in_data_descriptor("zzzzxqjk_nonexistent", "activity", selected_term_fields=[])
        assert results == [] or results is None

    def test_find_with_wildcard(self, installed_dbs):
        import esgvoc.api.universe as universe
        results = universe.find_terms_in_data_descriptor("vol*", "activity", selected_term_fields=[])
        assert len(results) > 0

    def test_find_in_nonexistent_descriptor_returns_empty(self, installed_dbs):
        import esgvoc.api.universe as universe
        results = universe.find_terms_in_data_descriptor("volmip", "nonexistent_descriptor_xyz", selected_term_fields=[])
        assert results == [] or results is None


class TestFindItemsInUniverse:
    def test_find_term_item(self, installed_dbs):
        import esgvoc.api.universe as universe
        from esgvoc.api.search import ItemKind
        results = universe.find_items_in_universe("volmip")
        assert results is not None
        # Should include a TERM item for volmip
        term_items = [item for item in results if item.kind == ItemKind.TERM and item.id == "volmip"]
        assert len(term_items) > 0

    def test_find_data_descriptor_item(self, installed_dbs):
        import esgvoc.api.universe as universe
        from esgvoc.api.search import ItemKind
        results = universe.find_items_in_universe("institution")
        assert results is not None
        # Should include either a DATA_DESCRIPTOR item or TERM items
        assert len(results) > 0

    def test_find_no_match_returns_empty(self, installed_dbs):
        import esgvoc.api.universe as universe
        results = universe.find_items_in_universe("zzzzxqjk_nonexistent_xyz")
        assert results == [] or results is None

    def test_find_with_wildcard(self, installed_dbs):
        import esgvoc.api.universe as universe
        results = universe.find_items_in_universe("vol*")
        assert len(results) > 0


class TestSelectedTermFields:
    def test_get_term_with_single_selected_field(self, installed_dbs):
        import esgvoc.api.universe as universe
        term = universe.get_term_in_data_descriptor("activity", "volmip", selected_term_fields=["drs_name"])
        assert term is not None
        assert hasattr(term, "id")
        assert term.id == "volmip"
        assert hasattr(term, "drs_name")
        assert term.drs_name == "VolMIP"
        assert not hasattr(term, "type")
        assert not hasattr(term, "description")

    def test_get_all_terms_with_selected_field(self, installed_dbs):
        import esgvoc.api.universe as universe
        terms = universe.get_all_terms_in_data_descriptor("activity", selected_term_fields=["drs_name"])
        assert len(terms) > 0
        first = terms[0]
        assert hasattr(first, "id")
        assert hasattr(first, "drs_name")
        assert not hasattr(first, "type")
        assert not hasattr(first, "description")

    def test_find_terms_with_selected_field(self, installed_dbs):
        import esgvoc.api.universe as universe
        terms = universe.find_terms_in_data_descriptor("volmip", "activity", selected_term_fields=["drs_name"])
        assert len(terms) > 0
        term = terms[0]
        assert hasattr(term, "id")
        assert term.id == "volmip"
        assert hasattr(term, "drs_name")
        assert term.drs_name == "VolMIP"
        assert not hasattr(term, "type")
        assert not hasattr(term, "description")

    def test_get_term_with_multiple_selected_fields(self, installed_dbs):
        import esgvoc.api.universe as universe
        term = universe.get_term_in_data_descriptor(
            "activity", "volmip", selected_term_fields=["drs_name", "long_name"]
        )
        assert term is not None
        assert hasattr(term, "id")
        assert hasattr(term, "drs_name")
        assert hasattr(term, "long_name")
        assert not hasattr(term, "type")
        assert not hasattr(term, "description")

    def test_get_term_with_type_selected(self, installed_dbs):
        import esgvoc.api.universe as universe
        term = universe.get_term_in_data_descriptor(
            "activity", "volmip", selected_term_fields=["type", "drs_name"]
        )
        assert term is not None
        assert hasattr(term, "id")
        assert term.id == "volmip"
        assert hasattr(term, "type")
        assert term.type == "activity"
        assert hasattr(term, "drs_name")
        assert term.drs_name == "VolMIP"
        assert not hasattr(term, "description")

    def test_get_term_with_nonexistent_field(self, installed_dbs):
        import esgvoc.api.universe as universe
        term = universe.get_term_in_data_descriptor(
            "activity", "volmip", selected_term_fields=["drs_name", "nothing"]
        )
        assert term is not None
        assert hasattr(term, "id")
        assert term.id == "volmip"
        assert hasattr(term, "drs_name")
        assert term.drs_name == "VolMIP"
        assert not hasattr(term, "nothing")
        assert not hasattr(term, "type")
        assert not hasattr(term, "description")
