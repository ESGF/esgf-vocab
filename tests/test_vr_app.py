"""Tests for list-valued known-branded-variable metadata in the VR app."""

from esgvoc.api.data_descriptors.known_branded_variable import KnownBrandedVariable
from esgvoc.apps.vr.vr_app import VRApp, create_nested_structure


def _branded_variable(identifier: str, realms: list[str]) -> KnownBrandedVariable:
    return KnownBrandedVariable.model_construct(
        id=identifier,
        cf_standard_name="air_temperature",
        variable_root_name="ta",
        realm=realms,
        bn_status="accepted",
    )


def test_nested_structure_groups_term_under_each_realm():
    term = _branded_variable("ta", ["atmos", "land"])

    result = create_nested_structure([term], ["realm"])

    assert result["atmos"][0]["id"] == "ta"
    assert result["land"][0]["id"] == "ta"


def test_subset_filter_matches_any_realm():
    terms = [_branded_variable("ta", ["atmos", "land"]), _branded_variable("tos", ["ocean"])]
    app = object.__new__(VRApp)
    app.get_all_branded_variables = lambda: terms

    assert app.get_branded_variables_subset({"realm": "land"}) == [terms[0]]
    assert app.get_branded_variables_subset({"realm": ["land", "ocean"]}) == terms


def test_statistics_flattens_realm_lists():
    terms = [_branded_variable("ta", ["atmos", "land"]), _branded_variable("tas", ["atmos"])]
    app = object.__new__(VRApp)

    result = app.get_statistics(terms)

    assert result["unique_realms"] == 2
    assert result["realm_distribution"] == {"atmos": 2, "land": 1}
