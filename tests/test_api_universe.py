from typing import Generator

import pytest

import esgvoc.api.universe as universe
from esgvoc.api._utils import ItemKind

_SOME_DATA_DESCRIPTOR_IDS = ['institution', 'product', 'variable']
_SOME_TERM_IDS = ['ipsl', 'observations', 'airmass']
_SOME_DD_TERM_IDS = [(_SOME_DATA_DESCRIPTOR_IDS[0], _SOME_TERM_IDS[0]),
                     (_SOME_DATA_DESCRIPTOR_IDS[1], _SOME_TERM_IDS[1]),
                     (_SOME_DATA_DESCRIPTOR_IDS[2], _SOME_TERM_IDS[2])]
_SOME_ITEM_IDS = list(zip(_SOME_DATA_DESCRIPTOR_IDS, [ItemKind.DATA_DESCRIPTOR for _ in _SOME_DATA_DESCRIPTOR_IDS])) + \
                 list(zip(_SOME_TERM_IDS, [ItemKind.TERM for _ in _SOME_TERM_IDS]))


def _provide_item_ids() -> Generator:
    for item_id in _SOME_ITEM_IDS:
        yield item_id


@pytest.fixture(params=_provide_item_ids())
def item_id(request) -> str:
    return request.param


def _provide_dd_term_ids() -> Generator:
    for combo in _SOME_DD_TERM_IDS:
        yield combo


@pytest.fixture(params=_provide_dd_term_ids())
def dd_term_ids(request) -> tuple[str, str]:
    return request.param


def _provide_data_descriptor_ids() -> Generator:
    for id in _SOME_DATA_DESCRIPTOR_IDS:
        yield id


@pytest.fixture(params=_provide_data_descriptor_ids())
def data_descriptor_id(request) -> str:
    return request.param


def _provide_term_ids() -> Generator:
    for id in _SOME_TERM_IDS:
        yield id


@pytest.fixture(params=_provide_term_ids())
def term_id(request) -> str:
    return request.param


def test_get_all_terms_in_universe() -> None:
    terms = universe.get_all_terms_in_universe()
    assert len(terms) > 0


def test_get_all_data_descriptors_in_universe() -> None:
    data_descriptors = universe.get_all_data_descriptors_in_universe()
    assert len(data_descriptors) > 0


def test_get_terms_in_data_descriptor(data_descriptor_id) -> None:
    terms = universe.get_all_terms_in_data_descriptor(data_descriptor_id)
    assert len(terms) > 0


def test_get_term_in_data_descriptor(dd_term_ids) -> None:
    term_found = universe.get_term_in_data_descriptor(dd_term_ids[0], dd_term_ids[1], [])
    assert term_found.id == dd_term_ids[1]


def test_get_term_in_universe(term_id) -> None:
    term_found = universe.get_term_in_universe(term_id, [])
    assert term_found.id == term_id


def test_get_data_descriptor_in_universe(data_descriptor_id) -> None:
    data_descriptor_found = universe.get_data_descriptor_in_universe(data_descriptor_id)
    assert data_descriptor_found[0] == data_descriptor_id


def test_find_data_descriptors_in_universe(data_descriptor_id) -> None:
    data_descriptors_found = universe.Rfind_data_descriptors_in_universe(data_descriptor_id)
    has_been_found = False
    for data_descriptor_found in data_descriptors_found:
        if data_descriptor_found[0] == data_descriptor_id:
            has_been_found = True
            break
    assert has_been_found


def test_find_terms_in_universe(term_id) -> None:
    terms_found = universe.Rfind_terms_in_universe(term_id, selected_term_fields=[])
    has_been_found = False
    for term_found in terms_found:
        if term_found.id == term_id:
            has_been_found = True
            break
    assert has_been_found


def test_find_terms_in_data_descriptor(dd_term_ids) -> None:
    terms_found = universe.Rfind_terms_in_data_descriptor(dd_term_ids[1], dd_term_ids[0], selected_term_fields=[])
    has_been_found = False
    for term_found in terms_found:
        if term_found.id == dd_term_ids[1]:
            has_been_found = True
            break
    assert has_been_found


def test_find_items_in_universe(item_id) -> None:
    items_found = universe.find_items_in_universe(item_id[0])
    has_been_found = False
    for item_found in items_found:
        if item_found.id == item_id[0]:
            assert item_found.kind == item_id[1]
            has_been_found = True
            break
    assert has_been_found
