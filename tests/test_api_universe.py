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


def test_get_term_with_selected_fields() -> None:
    """Test that --select option returns only the selected fields."""
    # Get a term with only drs_name selected
    term = universe.get_term_in_data_descriptor("activity", "volmip", selected_term_fields=["drs_name"])

    # Check mandatory field 'id' is present
    assert hasattr(term, "id")
    assert term.id == "volmip"

    # Check selected field is present
    assert hasattr(term, "drs_name")
    assert term.drs_name == "VolMIP"

    # Check non-selected fields are NOT present
    assert not hasattr(term, "type")
    assert not hasattr(term, "description")


def test_get_all_terms_with_selected_fields() -> None:
    """Test that selected_term_fields works for get_all_terms_in_data_descriptor."""
    terms = universe.get_all_terms_in_data_descriptor("activity", selected_term_fields=["drs_name"])

    assert len(terms) > 0

    # Check the first term
    first_term = terms[0]

    # Check mandatory field 'id' is present
    assert hasattr(first_term, "id")

    # Check selected field is present
    assert hasattr(first_term, "drs_name")

    # Check non-selected fields are NOT present
    assert not hasattr(first_term, "type")
    assert not hasattr(first_term, "description")


def test_find_terms_with_selected_fields() -> None:
    """Test that selected_term_fields works for find_terms_in_data_descriptor."""
    terms = universe.find_terms_in_data_descriptor("volmip", "activity", selected_term_fields=["drs_name"])

    assert len(terms) > 0

    # Check the found term
    term = terms[0]

    # Check mandatory field 'id' is present
    assert hasattr(term, "id")
    assert term.id == "volmip"

    # Check selected field is present
    assert hasattr(term, "drs_name")
    assert term.drs_name == "VolMIP"

    # Check non-selected fields are NOT present
    assert not hasattr(term, "type")
    assert not hasattr(term, "description")


def test_get_term_with_multiple_selected_fields() -> None:
    """Test selecting multiple fields."""
    # Get a term with multiple fields selected (using fields that actually exist in term.specs)
    term = universe.get_term_in_data_descriptor("activity", "volmip", selected_term_fields=["drs_name", "long_name"])

    # Check mandatory field 'id' is present
    assert hasattr(term, "id")

    # Check both selected fields are present
    assert hasattr(term, "drs_name")
    assert hasattr(term, "long_name")

    # Check non-selected fields are NOT present
    assert not hasattr(term, "type")
    assert not hasattr(term, "description")


def test_get_term_with_type_selected() -> None:
    """Test that 'type' can be explicitly selected."""
    # Get a term with type explicitly selected
    term = universe.get_term_in_data_descriptor("activity", "volmip", selected_term_fields=["type", "drs_name"])

    # Check mandatory field 'id' is present
    assert hasattr(term, "id")
    assert term.id == "volmip"

    # Check selected fields are present
    assert hasattr(term, "type")
    assert term.type == "activity"
    assert hasattr(term, "drs_name")
    assert term.drs_name == "VolMIP"

    # Check non-selected field is NOT present
    assert not hasattr(term, "description")


def test_get_term_with_non_existent_field() -> None:
    """Test that non-existent fields are not included in the response."""
    # Request a field that doesn't exist in the term data
    term = universe.get_term_in_data_descriptor("activity", "volmip", selected_term_fields=["drs_name", "nothing"])

    # Check mandatory field 'id' is present
    assert hasattr(term, "id")
    assert term.id == "volmip"

    # Check the existing selected field is present
    assert hasattr(term, "drs_name")
    assert term.drs_name == "VolMIP"

    # Check the non-existent field is NOT present
    assert not hasattr(term, "nothing")

    # Check other fields are also NOT present
    assert not hasattr(term, "type")
    assert not hasattr(term, "description")
