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
    collection_found = projects.get_collection_from_data_descriptor_in_project(get_param.project_id, dd_id)
    check_id(collection_found, get_param.collection_id)


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
    for term_found in terms_found:
        id = find_term_param.item.term_id if find_term_param.item else None
        check_id(term_found[1], id)


def test_only_id_limit_and_offset_find_terms(find_term_param):
    project_id = find_term_param.item.project_id if find_term_param.item else DEFAULT_PROJECT
    terms_found = projects.find_terms_in_project(
        find_term_param.expression, project_id, only_id=True, limit=10, offset=5, selected_term_fields=[]
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
