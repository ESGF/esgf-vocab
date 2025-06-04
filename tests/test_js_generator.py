from dataclasses import dataclass
from typing import Generator

import pytest

from esgvoc.api import projects
from esgvoc.api.search import get_universe_session
from esgvoc.apps.jsg import json_schema_generator as jsg

JSG_PROJECT_IDS = ['cmip6']


def _provide_get_jsg_project_ids() -> Generator:
    for param in JSG_PROJECT_IDS:
        yield param


@pytest.fixture(params=_provide_get_jsg_project_ids())
def jsg_project_id(request) -> str:
    return request.param


@dataclass
class JSGParameter:
    project_id: str
    schema_field: str
    expected_values: list[str]


JSG_PARAMETERS: list[JSGParameter] = [
    JSGParameter('cmip6', 'variable_id_long_name', ['Total Odd Oxygen (Ox) Production Rate',
                                                    'Carbon Mass in Soil on Grass Tiles',
                                                    'Percentage Cover of Stratiform Cloud']),
    JSGParameter('cmip6', 'sub_experiment_id', ['none', 's1976', 's1974']),
    JSGParameter('cmip6', 'grid', [
        "data reported on a model's native grid",
        'global mean data',
        "regridded data reported on the data provider's preferred target grid"]),
    JSGParameter('cmip6', 'experiment', [
        'Perturbation from 1850 control using 2014 N2O concentrations',
        'Historical WMGHG concentrations and NTCF emissions, 1950 halocarbon concentrations',
        'Against a background of the ScenarioMIP high forcing, reduce cirrus cloud optical depth by a constant amount']),
    JSGParameter('cmip6', 'variant_label', ['^r\\di\\dp\\df\\d$'])
]


def _provide_get_jsg_parameters() -> Generator:
    for param in JSG_PARAMETERS:
        yield param


@pytest.fixture(params=_provide_get_jsg_parameters())
def jsg_parameter(request) -> JSGParameter:
    return request.param


def test_cmip6_js_generation(jsg_project_id) -> None:
    js = jsg.generate_json_schema(jsg_project_id)
    assert js


def test_generate_property(jsg_parameter) -> None:
    with get_universe_session() as universe_session, \
         projects._get_project_session_with_exception(project_id=jsg_parameter.project_id) as project_session:
        collections = projects._get_all_collections_in_project(project_session)
        js = jsg._generate_property(project_id=jsg_parameter.project_id,
                                collections=collections,
                                schema_field=jsg_parameter.schema_field,
                                universe_session=universe_session,
                                project_session=project_session)
        print(js)
        for expected_value in jsg_parameter.expected_values:
            if 'enum' in js[1]:
                assert expected_value in js[1]['enum']
            else:
                assert expected_value in js[1]['pattern']
