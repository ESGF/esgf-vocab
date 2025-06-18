from dataclasses import dataclass
from typing import Generator

import pytest

from esgvoc.api import projects
from esgvoc.apps.jsg import json_schema_generator as jsg

JSG_PROJECT_IDS = ["cmip6"]


def _provide_get_jsg_project_ids() -> Generator:
    for param in JSG_PROJECT_IDS:
        yield param


@pytest.fixture(params=_provide_get_jsg_project_ids())
def jsg_project_id(request) -> str:
    return request.param


@dataclass
class JSGParameter:
    project_id: str
    attribute_name: str
    expected_values: list[str]


JSG_PARAMETERS: list[JSGParameter] = [
    JSGParameter(
        "cmip6",
        "variable_id",
        ["airmass", "albc", "chlcalc"],
    ),
    JSGParameter(
        "cmip6",
        "grid_label",
        ["gr6g", "gr9a", "grz"],
    ),
    JSGParameter("cmip6", "sub_experiment_id", ["none", "s1976", "s1974"]),
    JSGParameter(
        "cmip6",
        "grid",
        [
            "data reported on a model's native grid",
            "global mean data",
            "regridded data reported on the data provider's preferred target grid",
        ],
    ),
    JSGParameter(
        "cmip6",
        "experiment",
        [
            "Perturbation from 1850 control using 2014 N2O concentrations",
            "Historical WMGHG concentrations and NTCF emissions, 1950 halocarbon concentrations",
            "Against a background of the ScenarioMIP high forcing, reduce cirrus cloud optical depth by a constant amount",
        ],
    ),
    JSGParameter("cmip6", "data_specs_version", ["^\\d{2}\\.\\d{2}\\.\\d{2}$"]),
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
    project_specs = projects.get_project(jsg_parameter.project_id)
    assert project_specs
    assert project_specs.global_attributes_specs
    with jsg.JsonPropertiesVisitor(jsg_parameter.project_id) as visitor:
        assert jsg_parameter.attribute_name in project_specs.global_attributes_specs
        attribute = project_specs.global_attributes_specs[jsg_parameter.attribute_name]
        attribute_key, attribute_properties = attribute.accept(jsg_parameter.attribute_name, visitor)
        for expected_value in jsg_parameter.expected_values:
            if "enum" in attribute_properties:
                assert "enum" in attribute_properties
                assert expected_value in attribute_properties["enum"]
            else:
                assert "pattern" in attribute_properties
                assert expected_value in attribute_properties["pattern"]
