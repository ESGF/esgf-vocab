import esgvoc.api.projects as projects
from esgvoc.api.search import ItemKind
from tests.api_inputs import (
    DEFAULT_COLLECTION,  # noqa: F401
    DEFAULT_PROJECT,
    LEN_COLLECTIONS,
    LEN_PROJECTS,
    ValidationExpression,
    check_id,
    check_validation,
    find_col_param,
    find_proj_item_param,
    find_term_param,
    get_param,
    val_query,
)


def test_get_all_projects() -> None:
    prjs = projects.get_all_projects()
    assert len(prjs) == LEN_PROJECTS


def test_get_project(get_param) -> None:
    project = projects.get_project(get_param.project_id)
    check_id(project, get_param.project_id)


def test_get_all_terms_in_project(get_param) -> None:
    terms = projects.get_all_terms_in_project(get_param.project_id)
    check_id(terms, get_param.term_id)


def test_get_all_terms_in_all_projects() -> None:
    terms = projects.get_all_terms_in_all_projects()
    assert len(terms) == LEN_PROJECTS


def test_get_all_collections_in_project(get_param) -> None:
    collections = projects.get_all_collections_in_project(get_param.project_id)
    assert len(collections) > 10
    check_id(collections, get_param.collection_id)


def test_get_all_terms_in_collection(get_param) -> None:
    terms = projects.get_all_terms_in_collection(get_param.project_id, get_param.collection_id)
    assert len(terms) >= LEN_COLLECTIONS[get_param.project_id][get_param.collection_id]
    check_id(terms, get_param.term_id)


def test_get_term_in_project(get_param) -> None:
    term_found = projects.get_term_in_project(get_param.project_id, get_param.term_id, [])
    check_id(term_found, get_param.term_id)


def test_get_term_in_collection(get_param) -> None:
    term_found = projects.get_term_in_collection(get_param.project_id, get_param.collection_id, get_param.term_id, [])
    check_id(term_found, get_param.term_id)


def test_get_collection_in_project(get_param) -> None:
    collection_found = projects.get_collection_in_project(get_param.project_id, get_param.collection_id)
    check_id(collection_found, get_param.collection_id)


def test_get_collection_from_data_descriptor_in_project(get_param) -> None:
    if get_param.data_descriptor_id == "institution":
        dd_id = "organisation"
    else:
        dd_id = get_param.data_descriptor_id
    collections_found = projects.get_collection_from_data_descriptor_in_project(get_param.project_id, dd_id)
    # Now returns a list of tuples [(collection_id, context), ...]
    assert isinstance(collections_found, list)
    check_id(collections_found, get_param.collection_id)


def test_get_collection_from_data_descriptor_in_all_projects(get_param):
    if get_param.data_descriptor_id == "institution":
        dd_id = "organisation"
    else:
        dd_id = get_param.data_descriptor_id
    collections_found = projects.get_collection_from_data_descriptor_in_all_projects(dd_id)
    assert len(collections_found) == LEN_PROJECTS


def test_get_term_from_universe_term_id_in_project(get_param) -> None:
    if get_param.data_descriptor_id == "institution":
        dd_id = "organisation"
    else:
        dd_id = get_param.data_descriptor_id
    term_found = projects.get_term_from_universe_term_id_in_project(get_param.project_id, dd_id, get_param.term_id)
    assert term_found
    assert term_found[0] == get_param.collection_id
    check_id(term_found[1], get_param.term_id)


def test_get_term_from_universe_term_id_in_all_projects(get_param) -> None:
    if get_param.data_descriptor_id == "institution":
        dd_id = "organisation"
    else:
        dd_id = get_param.data_descriptor_id
    terms_found = projects.get_term_from_universe_term_id_in_all_projects(dd_id, get_param.term_id)
    assert terms_found


def test_valid_term(val_query) -> None:
    vr = projects.valid_term(
        val_query.value, val_query.item.project_id, val_query.item.collection_id, val_query.item.term_id
    )
    assert val_query.nb_errors == len(vr.errors)


def test_valid_term_in_collection(val_query) -> None:
    matching_terms = projects.valid_term_in_collection(
        val_query.value, val_query.item.project_id, val_query.item.collection_id
    )
    check_validation(val_query, matching_terms)


def test_valid_term_in_project(val_query) -> None:
    matching_terms = projects.valid_term_in_project(val_query.value, val_query.item.project_id)
    check_validation(val_query, matching_terms, True)


def test_valid_term_in_all_projects(val_query) -> None:
    matching_terms = projects.valid_term_in_all_projects(val_query.value)
    check_validation(val_query, matching_terms, False, True)


def test_find_collections_in_project(find_col_param) -> None:
    collections_found = projects.find_collections_in_project(find_col_param.expression, find_col_param.item.project_id)
    id = find_col_param.item.collection_id if find_col_param.item else None
    check_id(collections_found, id)


def test_find_terms_in_collection(find_term_param) -> None:
    if find_term_param.item:
        project_id = find_term_param.item.project_id
        collection_id = find_term_param.item.collection_id
    else:
        project_id = DEFAULT_PROJECT
        collection_id = DEFAULT_COLLECTION
    terms_found = projects.find_terms_in_collection(
        find_term_param.expression, project_id, collection_id, selected_term_fields=[]
    )
    id = find_term_param.item.term_id if find_term_param.item else None
    check_id(terms_found, id)


def test_find_terms_in_project(find_term_param) -> None:
    project_id = find_term_param.item.project_id if find_term_param.item else DEFAULT_PROJECT
    terms_found = projects.find_terms_in_project(find_term_param.expression, project_id, selected_term_fields=[])
    id = find_term_param.item.term_id if find_term_param.item else None
    check_id(terms_found, id)


def test_find_terms_in_all_projects(find_term_param) -> None:
    terms_found = projects.find_terms_in_all_projects(find_term_param.expression)
    # Collect all terms from all projects into one list
    all_terms = []
    for project_id, terms in terms_found:
        all_terms.extend(terms)
    # Check if expected ID is among any of the results
    id = find_term_param.item.term_id if find_term_param.item else None
    check_id(all_terms, id)


def test_only_id_limit_and_offset_find_terms(find_term_param):
    project_id = find_term_param.item.project_id if find_term_param.item else DEFAULT_PROJECT
    terms_found = projects.find_terms_in_project(
        find_term_param.expression, project_id, only_id=True, limit=10, offset=6, selected_term_fields=[]
    )
    assert not terms_found


def test_find_items_in_project(find_proj_item_param) -> None:
    project_id = find_proj_item_param.item.project_id if find_proj_item_param.item else DEFAULT_PROJECT
    items_found = projects.find_items_in_project(find_proj_item_param.expression, project_id)
    if find_proj_item_param.item is None:
        id = None
        parent_id = None
    else:
        if find_proj_item_param.item_kind == ItemKind.TERM:
            id = find_proj_item_param.item.term_id
            parent_id = find_proj_item_param.item.collection_id
        else:
            id = find_proj_item_param.item.collection_id
            parent_id = find_proj_item_param.item.project_id
    check_id(items_found, id, find_proj_item_param.item_kind, parent_id)


def test_only_id_limit_and_offset_find_items(find_proj_item_param):
    project_id = find_proj_item_param.item.project_id if find_proj_item_param.item else DEFAULT_PROJECT
    _ = projects.find_items_in_project(find_proj_item_param.expression, project_id, limit=10, offset=5)


def test_multiple_collections_per_data_descriptor(use_all_dev_config) -> None:
    """Test that data descriptors with multiple collections return all of them."""
    # Test cases where we know there are multiple collections per data descriptor
    test_cases = [
        ("cordex-cmip6", "mip_era", ["mip_era", "project_id"]),
        ("cordex-cmip6", "organisation", ["driving_institution_id", "institution_id"]),
        ("cordex-cmip6", "source", ["driving_source_id", "source_id"]),
        ("input4mip", "activity", ["activity_id", "target_mip"]),
        ("input4mip", "realm", ["dataset_category", "realm"]),
        ("obs4ref", "contact", ["contact", "dataset_contributor"]),
    ]

    for project_id, data_descriptor_id, expected_collections in test_cases:
        collections_found = projects.get_collection_from_data_descriptor_in_project(project_id, data_descriptor_id)

        # Should return a list
        assert isinstance(collections_found, list), f"{project_id}/{data_descriptor_id}: Expected list"

        # Should have the expected number of collections
        assert len(collections_found) == len(expected_collections), (
            f"{project_id}/{data_descriptor_id}: Expected {len(expected_collections)} collections, got {len(collections_found)}"
        )
        # Each item should be a tuple (collection_id, context)
        for collection_id, context in collections_found:
            assert isinstance(collection_id, str), f"Expected collection_id to be str, got {type(collection_id)}"
            assert isinstance(context, dict), f"Expected context to be dict, got {type(context)}"

        # Check that all expected collections are present
        found_collection_ids = {coll_id for coll_id, _ in collections_found}
        expected_set = set(expected_collections)
        assert found_collection_ids == expected_set, (
            f"{project_id}/{data_descriptor_id}: Expected {expected_set}, got {found_collection_ids}"
        )


def test_multiple_collections_across_all_projects(use_all_dev_config) -> None:
    """Test that get_collection_from_data_descriptor_in_all_projects returns all collections flattened."""
    # Test with 'mip_era' which has duplicates in cordex-cmip6 but single collections in other projects
    collections = projects.get_collection_from_data_descriptor_in_all_projects("mip_era")

    # Should return a list of tuples (project_id, collection_id, context)
    assert isinstance(collections, list)

    # Find cordex-cmip6 entries
    cordex_entries = [(proj, coll, ctx) for proj, coll, ctx in collections if proj == "cordex-cmip6"]

    # Should have 2 entries for cordex-cmip6 (mip_era and project_id)
    assert len(cordex_entries) == 2, f"Expected 2 collections for cordex-cmip6, got {len(cordex_entries)}"

    cordex_collection_ids = {coll for _, coll, _ in cordex_entries}
    assert cordex_collection_ids == {"mip_era", "project_id"}, (
        f"Expected mip_era and project_id, got {cordex_collection_ids}"
    )


def test_get_data_descriptor_from_collection_in_project(get_param) -> None:
    """Test that get_data_descriptor_from_collection_in_project returns the correct data descriptor."""
    # Use the parameterized test data
    data_descriptor = projects.get_data_descriptor_from_collection_in_project(
        get_param.project_id, get_param.collection_id
    )

    # Should return a string (the data descriptor id)
    assert isinstance(data_descriptor, str), f"Expected str, got {type(data_descriptor)}"

    # The returned data descriptor should match the expected one from get_param
    # Note: Some collections map to different data descriptor names (e.g., institution -> organisation)
    if get_param.data_descriptor_id == "institution":
        expected_dd_id = "organisation"
    else:
        expected_dd_id = get_param.data_descriptor_id

    assert data_descriptor == expected_dd_id, (
        f"Expected data descriptor '{expected_dd_id}', got '{data_descriptor}'"
    )


def test_get_data_descriptor_from_collection_cmip6_institution(use_all_dev_config) -> None:
    """Test that CMIP6 institution_id collection returns 'organisation' as data descriptor."""
    data_descriptor = projects.get_data_descriptor_from_collection_in_project("cmip6", "institution_id")

    # Should return 'organisation' for CMIP6's institution_id collection
    assert data_descriptor == "organisation", (
        f"Expected 'organisation' for CMIP6/institution_id, got '{data_descriptor}'"
    )


def test_get_data_descriptor_from_collection_not_found() -> None:
    """Test that get_data_descriptor_from_collection_in_project returns None for non-existent collection."""
    # Test with a valid project but non-existent collection
    data_descriptor = projects.get_data_descriptor_from_collection_in_project("cmip6", "non_existent_collection")

    # Should return None when collection is not found
    assert data_descriptor is None, f"Expected None for non-existent collection, got {data_descriptor}"


def test_get_data_descriptor_from_collection_invalid_project() -> None:
    """Test that get_data_descriptor_from_collection_in_project returns None for non-existent project."""
    # Test with a non-existent project
    data_descriptor = projects.get_data_descriptor_from_collection_in_project("non_existent_project", "institution_id")

    # Should return None when project is not found
    assert data_descriptor is None, f"Expected None for non-existent project, got {data_descriptor}"


def test_get_terms_in_collection_by_key_value_plain_term() -> None:
    """Test that get_terms_in_collection_by_key_value returns correct terms for plain terms."""
    # Test with a known plain term: institution_id/IPSL
    terms_found = projects.get_terms_in_collection_by_key_value(
        "cmip6plus", "institution_id", "drs_name", "IPSL"
    )
    assert isinstance(terms_found, list)
    assert len(terms_found) == 1
    check_id(terms_found, "ipsl")


def test_get_terms_in_collection_by_key_value_composite_term() -> None:
    """Test that get_terms_in_collection_by_key_value works for composite terms."""
    # Test with separator key for composite terms (member_id uses "-")
    terms_found = projects.get_terms_in_collection_by_key_value(
        "cmip6", "member_id", "separator", "-"
    )
    assert isinstance(terms_found, list)
    assert len(terms_found) >= 1


def test_get_terms_in_project_by_key_value_plain_term() -> None:
    """Test that get_terms_in_project_by_key_value returns correct terms for plain terms."""
    # Test with a known plain term: IPSL
    terms_found = projects.get_terms_in_project_by_key_value(
        "cmip6plus", "drs_name", "IPSL"
    )
    assert isinstance(terms_found, list)
    assert len(terms_found) >= 1
    check_id(terms_found, "ipsl")


def test_get_terms_in_project_by_key_value_composite_term() -> None:
    """Test that get_terms_in_project_by_key_value works for composite terms."""
    # Test with separator key - should find multiple composite terms
    terms_found = projects.get_terms_in_project_by_key_value(
        "cmip6", "separator", "-"
    )
    assert isinstance(terms_found, list)
    assert len(terms_found) >= 1


def test_get_terms_in_all_projects_by_key_value() -> None:
    """Test that get_terms_in_all_projects_by_key_value returns terms from multiple projects."""
    # Use a term that exists in multiple projects (e.g., "IPSL" institution)
    results = projects.get_terms_in_all_projects_by_key_value("drs_name", "IPSL")

    # Should return a list of tuples (project_id, terms_list)
    assert isinstance(results, list)
    assert len(results) >= 1

    # Check structure of results
    for project_id, terms in results:
        assert isinstance(project_id, str)
        assert isinstance(terms, list)
        assert len(terms) >= 1
        check_id(terms, "ipsl")


def test_get_terms_in_project_by_key_value_multiple_results() -> None:
    """Test that get_terms_in_project_by_key_value returns all matching terms."""
    # Use separator="-" which should match multiple composite terms
    terms_found = projects.get_terms_in_project_by_key_value("cmip6", "separator", "-")

    # Should return a list with multiple terms
    assert isinstance(terms_found, list)
    assert len(terms_found) >= 1  # At least member_id uses "-"


def test_get_terms_in_collection_by_key_value_not_found() -> None:
    """Test that get_terms_in_collection_by_key_value returns empty list for non-existent value."""
    terms_found = projects.get_terms_in_collection_by_key_value(
        "cmip6plus", "institution_id", "drs_name", "NON_EXISTENT_VALUE_12345"
    )
    assert terms_found == []


def test_get_terms_in_project_by_key_value_not_found() -> None:
    """Test that get_terms_in_project_by_key_value returns empty list for non-existent value."""
    terms_found = projects.get_terms_in_project_by_key_value(
        "cmip6plus", "drs_name", "NON_EXISTENT_VALUE_12345"
    )
    assert terms_found == []


def test_get_terms_in_collection_by_key_value_invalid_project() -> None:
    """Test that get_terms_in_collection_by_key_value returns empty list for non-existent project."""
    terms_found = projects.get_terms_in_collection_by_key_value(
        "non_existent_project", "institution_id", "drs_name", "IPSL"
    )
    assert terms_found == []


def test_get_terms_in_all_projects_by_key_value_not_found() -> None:
    """Test that get_terms_in_all_projects_by_key_value returns empty list for non-existent value."""
    terms_found = projects.get_terms_in_all_projects_by_key_value("drs_name", "NON_EXISTENT_VALUE_12345")
    assert terms_found == []


def test_get_terms_in_collection_by_key_value_with_selected_fields() -> None:
    """Test that get_terms_in_collection_by_key_value respects selected_term_fields."""
    # Test with selected fields
    terms_found = projects.get_terms_in_collection_by_key_value(
        "cmip6plus", "institution_id", "drs_name", "IPSL", selected_term_fields=[]
    )
    assert isinstance(terms_found, list)
    assert len(terms_found) >= 1
    check_id(terms_found, "ipsl")
