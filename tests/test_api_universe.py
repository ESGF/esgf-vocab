import esgvoc.api.universe as universe
from esgvoc.api.search import ItemKind
from tests.api_inputs import (  # noqa: F401
    DEFAULT_DD,
    LEN_DATA_DESCRIPTORS,
    check_id,
    find_dd_param,
    find_term_param,
    find_univ_item_param,
    get_param,
)


def test_get_all_terms_in_universe() -> None:
    terms = universe.get_all_terms_in_universe()
    assert len(terms) > 0


def test_get_all_data_descriptors_in_universe(get_param) -> None:
    data_descriptors = universe.get_all_data_descriptors_in_universe()
    check_id(data_descriptors, get_param.data_descriptor_id)
    assert len(data_descriptors) > 0


def test_get_all_terms_in_data_descriptor(get_param) -> None:
    terms = universe.get_all_terms_in_data_descriptor(get_param.data_descriptor_id)
    assert len(terms) >= LEN_DATA_DESCRIPTORS[get_param.data_descriptor_id]
    check_id(terms, get_param.term_id)


def test_get_term_in_data_descriptor(get_param) -> None:
    term_id = get_param.term_id
    term_found = universe.get_term_in_data_descriptor(get_param.data_descriptor_id,
                                                      term_id, [])
    check_id(term_found, term_id)


def test_get_term_in_universe(get_param) -> None:
    term_found = universe.get_term_in_universe(get_param.term_id, [])
    check_id(term_found, get_param.term_id)


def test_get_data_descriptor_in_universe(get_param) -> None:
    data_descriptor_found = universe.get_data_descriptor_in_universe(get_param.data_descriptor_id)
    check_id(data_descriptor_found, get_param.data_descriptor_id)


def test_find_data_descriptors_in_universe(find_dd_param) -> None:
    data_descriptors_found = universe.find_data_descriptors_in_universe(find_dd_param.expression)
    id = find_dd_param.item.data_descriptor_id if find_dd_param.item else None
    check_id(data_descriptors_found, id)


def test_find_terms_in_universe(find_term_param) -> None:
    terms_found = universe.find_terms_in_universe(find_term_param.expression,
                                                  selected_term_fields=[])
    id = find_term_param.item.term_id if find_term_param.item else None
    check_id(terms_found, id)


def test_find_terms_in_data_descriptor(find_term_param) -> None:
    dd_id = find_term_param.item.data_descriptor_id if find_term_param.item else DEFAULT_DD
    terms_found = universe.find_terms_in_data_descriptor(find_term_param.expression,
                                                         dd_id,
                                                         selected_term_fields=[])
    id = find_term_param.item.term_id if find_term_param.item else None
    check_id(terms_found, id)


def test_find_items_in_universe(find_univ_item_param) -> None:
    items_found = universe.find_items_in_universe(find_univ_item_param.expression)
    if find_univ_item_param.item is None:
        id = None
        parent_id = None
    else:
        if find_univ_item_param.item_kind == ItemKind.TERM:
            id = find_univ_item_param.item.term_id
            parent_id = find_univ_item_param.item.data_descriptor_id
        else:
            id = find_univ_item_param.item.data_descriptor_id
            parent_id = 'universe'
    if id:
        check_id(items_found,
                 id,
                 find_univ_item_param.item_kind,
                 parent_id)
    else:
        pass
