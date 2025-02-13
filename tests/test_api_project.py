from typing import Generator

import pytest

import esgvoc.api.projects as projects
from esgvoc.api import SearchSettings, SearchType

_SOME_PROJECT_IDS = ['cmip6plus']
_SOME_COLLECTION_IDS = ['institution_id', 'time_range', 'source_id']
_SOME_DATA_DESCRIPTOR_IDS = ['organisation', 'time_range', 'source']
_SOME_TERM_IDS = ['ipsl', 'daily', 'miroc6']
_SETTINGS = SearchSettings(type=SearchType.LIKE, selected_term_fields=('id', 'type', 'name'))


def _provide_project_ids() -> Generator:
    for project_id in _SOME_PROJECT_IDS:
        yield project_id


@pytest.fixture(params=_provide_project_ids())
def project_id(request) -> str:
    return request.param


def _provide_collection_ids() -> Generator:
    for collection_id in _SOME_COLLECTION_IDS:
        yield collection_id


@pytest.fixture(params=_provide_collection_ids())
def collection_id(request) -> str:
    return request.param


def _provide_data_descriptor_ids() -> Generator:
    for collection_id in _SOME_DATA_DESCRIPTOR_IDS:
        yield collection_id


@pytest.fixture(params=_provide_data_descriptor_ids())
def data_descriptor_id(request) -> str:
    return request.param


def _provide_term_ids() -> Generator:
    for term_id in _SOME_TERM_IDS:
        yield term_id


@pytest.fixture(params=_provide_term_ids())
def term_id(request) -> str:
    return request.param


def test_get_all_projects() -> None:
    prjs = projects.get_all_projects()
    assert len(prjs) > 0


def test_find_project(project_id) -> None:
    project = projects.find_project(project_id)
    assert project is not None
    assert project.project_id == project_id


def test_get_all_terms_in_project(project_id) -> None:
    terms = projects.get_all_terms_in_project(project_id)
    assert len(terms) > 0


def test_get_all_terms_in_all_projects() -> None:
    terms = projects.get_all_terms_in_all_projects()
    assert len(terms) >= 2


def test_get_all_collections_in_project(project_id) -> None:
    collections = projects.get_all_collections_in_project(project_id)
    assert len(collections) > 0


def test_find_collections_in_project(project_id, collection_id) -> None:
    collections = projects.find_collections_in_project(project_id, collection_id)
    assert len(collections) == 1
    collections = projects.find_collections_in_project(project_id, collection_id, _SETTINGS)
    assert len(collections) > 0


def test_get_all_terms_in_collection(project_id, collection_id) -> None:
    terms = projects.get_all_terms_in_collection(project_id, collection_id)
    assert len(terms) > 0


def test_find_terms_in_project(project_id, term_id) -> None:
    terms = projects.find_terms_in_project(project_id, term_id)
    assert len(terms) > 0
    terms = projects.find_terms_in_project(project_id, term_id, _SETTINGS)
    assert len(terms) > 0


def test_find_terms_in_all_projects(term_id) -> None:
    terms = projects.find_terms_in_all_projects(term_id)
    assert len(terms) > 0
    terms = projects.find_terms_in_all_projects(term_id, _SETTINGS)
    assert len(terms) > 0


def test_find_terms_in_collection(project_id, collection_id, term_id) -> None:
    terms = projects.find_terms_in_collection(project_id, collection_id, term_id)
    if terms:
        assert len(terms) == 1
        assert terms[0].id == term_id
    projects.find_terms_in_collection(project_id, collection_id, term_id, _SETTINGS)


def test_find_terms_from_data_descriptor_in_project(project_id, data_descriptor_id, term_id) -> None:
    terms = projects.find_terms_from_data_descriptor_in_project(project_id, data_descriptor_id, term_id)
    if terms:
        assert len(terms) == 1
    projects.find_terms_from_data_descriptor_in_project(project_id,
                                                        data_descriptor_id,
                                                        term_id,
                                                        _SETTINGS)


def test_find_terms_from_data_descriptor_in_all_projects(data_descriptor_id,
                                                         term_id) -> None:
    terms = projects.find_terms_from_data_descriptor_in_all_projects(data_descriptor_id, term_id)
    if terms:
        assert (len(terms) == 1) or (len(terms) == 2)
    projects.find_terms_from_data_descriptor_in_all_projects(data_descriptor_id,
                                                             term_id,
                                                             _SETTINGS)


def test_valid_term() -> None:
    validation_requests = [
    (0, ('IPSL', 'cmip6plus', 'institution_id', 'ipsl')),
    (0, ('r1i1p1f1', 'cmip6plus', 'member_id', 'ripf')),
    (1, ('IPL', 'cmip6plus', 'institution_id', 'ipsl')),
    (1, ('r1i1p1f111', 'cmip6plus', 'member_id', 'ripf')),
    (0, ('20241206-20241207', 'cmip6plus', 'time_range', 'daily')),
    (2, ('0241206-0241207', 'cmip6plus', 'time_range', 'daily'))]
    for validation_request in validation_requests:
        nb_errors, parameters = validation_request
        vr = projects.valid_term(*parameters)
        assert nb_errors == len(vr), f'not matching number of errors for parameters {parameters}'


def test_valid_term_in_collection() -> None:
    validation_requests = [
    (1, ('IPSL', 'cmip6plus', 'institution_id'), 'ipsl'),
    (1, ('r1i1p1f1', 'cmip6plus', 'member_id'), 'ripf'),
    (0, ('IPL', 'cmip6plus', 'institution_id'), None),
    (0, ('r1i1p1f11', 'cmip6plus', 'member_id'), None),
    (1, ('20241206-20241207', 'cmip6plus', 'time_range'), 'daily'),
    (0, ('0241206-0241207', 'cmip6plus', 'time_range'), None)]
    for validation_request in validation_requests:
        nb_matching_terms, parameters, term_id = validation_request
        matching_terms = projects.valid_term_in_collection(*parameters)
        assert len(matching_terms) == nb_matching_terms
        if nb_matching_terms == 1:
            assert matching_terms[0].term_id == term_id


def test_valid_term_in_project() -> None:
    validation_requests = [
    (1, ('IPSL', 'cmip6plus'), 'ipsl'),
    (1, ('r1i1p1f1', 'cmip6plus'), 'ripf'),
    (0, ('IPL', 'cmip6plus'), None),
    (0, ('r1i1p1f11', 'cmip6plus'), None),
    (1, ('20241206-20241207', 'cmip6plus'), 'daily'),
    (0, ('0241206-0241207', 'cmip6plus'), None)]
    for validation_request in validation_requests:
        nb_matching_terms, parameters, term_id = validation_request
        matching_terms = projects.valid_term_in_project(*parameters)
        assert len(matching_terms) == nb_matching_terms
        if nb_matching_terms == 1:
            assert matching_terms[0].term_id == term_id
