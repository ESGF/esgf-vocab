from typing import Generator

import pytest

import esgvoc.api.universe as universe
from esgvoc.api import SearchSettings, SearchType

_SOME_DATA_DESCRIPTOR_IDS = ['institution', 'product', 'variable']
_SOME_TERM_IDS = ['ipsl', 'observations', 'airmass']
_SETTINGS = SearchSettings(type=SearchType.LIKE, selected_term_fields=('id', 'type', 'name'))


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
        

def test_find_term_in_data_descriptor(data_descriptor_id, term_id) -> None:
    terms = universe.find_terms_in_data_descriptor(data_descriptor_id, term_id)
    if terms:
        assert terms[0].id == term_id
    terms = universe.find_terms_in_data_descriptor(data_descriptor_id, term_id, _SETTINGS)
    if terms:
        assert terms[0].id == term_id


def test_find_terms_in_universe(term_id) -> None:
    terms = universe.find_terms_in_universe(term_id)
    assert len(terms) == 1
    terms = universe.find_terms_in_universe(term_id, settings=_SETTINGS)
    assert len(terms) > 0


def test_find_data_descriptor_in_universe(data_descriptor_id) -> None:
    data_descriptors = universe.find_data_descriptors_in_universe(data_descriptor_id)
    assert len(data_descriptors) == 1
    universe.find_data_descriptors_in_universe(data_descriptor_id, settings=_SETTINGS)
    assert len(data_descriptors) > 0