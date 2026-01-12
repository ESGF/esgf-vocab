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
        assert len(collections_found) == len(expected_collections), \
            f"{project_id}/{data_descriptor_id}: Expected {len(expected_collections)} collections, got {len(collections_found)}"

        # Each item should be a tuple (collection_id, context)
        for collection_id, context in collections_found:
            assert isinstance(collection_id, str), f"Expected collection_id to be str, got {type(collection_id)}"
            assert isinstance(context, dict), f"Expected context to be dict, got {type(context)}"

        # Check that all expected collections are present
        found_collection_ids = {coll_id for coll_id, _ in collections_found}
        expected_set = set(expected_collections)
        assert found_collection_ids == expected_set, \
            f"{project_id}/{data_descriptor_id}: Expected {expected_set}, got {found_collection_ids}"


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
    assert cordex_collection_ids == {"mip_era", "project_id"}, \
        f"Expected mip_era and project_id, got {cordex_collection_ids}"
