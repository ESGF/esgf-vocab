from typing import Generator

import pytest

import esgvoc.api.projects as projects
from esgvoc.api._utils import ItemKind

_SOME_PROJECT_IDS = ['cmip6plus', 'cmip6']
_SOME_COLLECTION_IDS = ['institution_id', 'time_range', 'source_id']
_SOME_DATA_DESCRIPTOR_IDS = ['organisation', 'time_range', 'source']
_SOME_PROJ_DD_COL_IDS = [(_SOME_PROJECT_IDS[0], _SOME_DATA_DESCRIPTOR_IDS[0], _SOME_COLLECTION_IDS[0]),
                         (_SOME_PROJECT_IDS[0], _SOME_DATA_DESCRIPTOR_IDS[1], _SOME_COLLECTION_IDS[1]),
                         (_SOME_PROJECT_IDS[0], _SOME_DATA_DESCRIPTOR_IDS[2], _SOME_COLLECTION_IDS[2]),
                         (_SOME_PROJECT_IDS[1], _SOME_DATA_DESCRIPTOR_IDS[0], _SOME_COLLECTION_IDS[0]),
                         (_SOME_PROJECT_IDS[1], _SOME_DATA_DESCRIPTOR_IDS[1], _SOME_COLLECTION_IDS[1]),
                         (_SOME_PROJECT_IDS[1], _SOME_DATA_DESCRIPTOR_IDS[2], _SOME_COLLECTION_IDS[2])]
_SOME_TERM_IDS = ['ipsl', 'daily', 'miroc6']
_SOME_PROJ_COL_TERM_IDS = [(_SOME_PROJECT_IDS[0], _SOME_COLLECTION_IDS[0], _SOME_TERM_IDS[0]),
                      (_SOME_PROJECT_IDS[0], _SOME_COLLECTION_IDS[1], _SOME_TERM_IDS[1]),
                      (_SOME_PROJECT_IDS[0], _SOME_COLLECTION_IDS[2], _SOME_TERM_IDS[2])]
_SOME_ITEM_IDS = list(zip(_SOME_COLLECTION_IDS, [ItemKind.COLLECTION for _ in _SOME_COLLECTION_IDS])) + \
                 list(zip(_SOME_TERM_IDS, [ItemKind.TERM for _ in _SOME_TERM_IDS]))


def _provide_proj_dd_col_ids() -> Generator:
    for combo in _SOME_PROJ_DD_COL_IDS:
        yield combo


@pytest.fixture(params=_provide_proj_dd_col_ids())
def proj_dd_col_id(request) -> str:
    return request.param


def _provide_item_ids() -> Generator:
    for item_id in _SOME_ITEM_IDS:
        yield item_id


@pytest.fixture(params=_provide_item_ids())
def item_id(request) -> str:
    return request.param


def _provide_proj_col_term_ids() -> Generator:
    for combo in _SOME_PROJ_COL_TERM_IDS:
        yield combo


@pytest.fixture(params=_provide_proj_col_term_ids())
def proj_col_term_ids(request) -> tuple[str, str]:
    return request.param


def _provide_data_descriptor_ids() -> Generator:
    for combo in _SOME_DATA_DESCRIPTOR_IDS:
        yield combo


@pytest.fixture(params=_provide_data_descriptor_ids())
def data_descriptor_id(request) -> str:
    return request.param


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


def _provide_term_ids() -> Generator:
    for term_id in _SOME_TERM_IDS:
        yield term_id


@pytest.fixture(params=_provide_term_ids())
def term_id(request) -> str:
    return request.param


def test_get_all_projects() -> None:
    prjs = projects.get_all_projects()
    assert len(prjs) > 0


def test_get_all_terms_in_project(project_id) -> None:
    terms = projects.get_all_terms_in_project(project_id)
    assert len(terms) > 0


def test_get_all_terms_in_all_projects() -> None:
    terms = projects.get_all_terms_in_all_projects()
    assert len(terms) >= 2


def test_get_all_collections_in_project(project_id) -> None:
    collections = projects.get_all_collections_in_project(project_id)
    assert len(collections) > 0


def test_get_all_terms_in_collection(project_id, collection_id) -> None:
    terms = projects.get_all_terms_in_collection(project_id, collection_id)
    assert len(terms) > 0


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


def test_get_project(project_id) -> None:
    project = projects.find_project(project_id)
    assert project
    assert project.project_id == project_id


def test_get_term_in_project(project_id, term_id) -> None:
    term_found = projects.get_term_in_project(project_id, term_id, [])
    assert term_found
    assert term_found.id == term_id


def test_get_term_in_collection(proj_col_term_ids) -> None:
    term_found = projects.get_term_in_collection(proj_col_term_ids[0], proj_col_term_ids[1],
                                                 proj_col_term_ids[2], [])
    assert term_found
    assert term_found.id == proj_col_term_ids[2]


def test_get_collection_in_project(project_id, collection_id) -> None:
    collection_found = projects.get_collection_in_project(project_id, collection_id)
    assert collection_found
    assert collection_found[0] == collection_id


def test_get_collection_from_data_descriptor_in_project(proj_dd_col_id) -> None:
    collection_found = projects.get_collection_from_data_descriptor_in_project(proj_dd_col_id[0],
                                                                               proj_dd_col_id[1])
    assert collection_found
    assert collection_found[0] == proj_dd_col_id[2]


def test_get_collection_from_data_descriptor_in_all_projects(data_descriptor_id):
    collections_found = projects.get_collection_from_data_descriptor_in_all_projects(data_descriptor_id)
    assert len(collections_found) == len(_SOME_PROJECT_IDS)
