"""
Tests for the known branded variable data descriptor model.
"""

import pytest
from pydantic import TypeAdapter, ValidationError

from esgvoc.api.data_descriptors.area_label import AreaLabel
from esgvoc.api.data_descriptors.coordinate import DataCoordinate
from esgvoc.api.data_descriptors.horizontal_label import HorizontalLabel
from esgvoc.api.data_descriptors.known_branded_variable import (
    KnownBrandedVariable,
    KnownBrandedVariableLegacy,
    KnownBrandedVariableModel,
)
from esgvoc.api.data_descriptors.temporal_label import TemporalLabel
from esgvoc.api.data_descriptors.variable import Variable
from esgvoc.api.data_descriptors.vertical_label import VerticalLabel
from esgvoc.api.pydantic_handler import get_pydantic_class


def known_branded_variable_data(**updates):
    """
    Return a complete known branded variable record.
    """
    record = {
        "id": "ta_tavg-p19-hxy-air",
        "type": "known_branded_variable",
        "drs_name": "ta_tavg-p19-hxy-air",
        "description": "Air temperature on pressure levels",
        "cf_standard_name": "air_temperature",
        "long_name": "Air Temperature",
        "units": "K",
        "variable_root_name": "ta",
        "branding_suffix_name": "tavg-p19-hxy-air",
        "out_name": "ta",
        "dimensions": ["longitude", "latitude", "plev19", "time"],
        "realm": "atmos",
        "temporal_label": "tavg",
        "vertical_label": "p19",
        "horizontal_label": "hxy",
        "area_label": "air",
    }
    record.update(updates)
    return record


def data_coordinate():
    """
    Return a complete data-coordinate object.
    """
    return DataCoordinate(
        id="plev19",
        type="coordinate",
        drs_name="plev19",
        description="Pressure levels",
        coordinate_type="standard_1d",
        long_name="pressure levels",
        cf_standard_name="air_pressure",
        units="Pa",
        axis="Z",
        out_name="plev",
        positive="down",
        stored_direction="decreasing",
        data_type="double",
        bounds_required=True,
        tolerance=None,
        valid_min=0.0,
        valid_max=110_000.0,
        coordinate_values=None,
        coordinate_bounds=None,
        is_climatology=False,
        is_generic_model_level_coordinate=False,
    )


def root_variable():
    """
    Return the resolved root variable used by branded-variable tests.
    """
    return Variable(
        id="ta",
        type="variable",
        drs_name="Ta",
        description="Air temperature",
        long_name="Air Temperature",
        standard_name="air_temperature",
        units="K",
    )


def resolved_labels():
    """
    Return resolved labels in branding-suffix order.
    """
    base_fields = {"type": "label", "description": "Sampling label"}
    return (
        TemporalLabel(id="tavg", drs_name="tavg", **base_fields),
        VerticalLabel(id="p19", drs_name="p19", **base_fields),
        HorizontalLabel(id="hxy", drs_name="hxy", **base_fields),
        AreaLabel(id="air", drs_name="air", cf_area_type="air", **base_fields),
    )


def test_known_branded_variable_accepts_reference_ids():
    model = KnownBrandedVariable(**known_branded_variable_data())

    assert model.variable_root_name == "ta"
    assert model.out_name == "ta"
    assert model.dimensions == ["longitude", "latitude", "plev19", "time"]
    assert model.realm == "atmos"


def test_out_name_matches_resolved_variable_drs_name():
    variable = root_variable()
    model = KnownBrandedVariable(
        **known_branded_variable_data(
            drs_name="Ta_tavg-p19-hxy-air",
            variable_root_name=variable,
            out_name="Ta",
        )
    )

    assert model.variable_root_name == variable
    assert model.out_name == variable.drs_name


@pytest.mark.parametrize(
    ("updates", "error"),
    [
        (
            {"drs_name": "wrong", "out_name": "Ta"},
            "drs_name must equal variable_root_name.drs_name",
        ),
    ],
)
def test_resolved_root_metadata_must_be_consistent(updates, error):
    with pytest.raises(ValidationError, match=error):
        KnownBrandedVariable(
            **known_branded_variable_data(
                variable_root_name=root_variable(),
                **updates,
            )
        )


def test_resolved_root_allows_branded_variable_units_to_be_absent():
    model = KnownBrandedVariable(
        **known_branded_variable_data(
            drs_name="Ta_tavg-p19-hxy-air",
            variable_root_name=root_variable(),
            out_name="Ta",
            units=None,
        )
    )

    assert model.units is None


def test_branding_suffix_matches_resolved_label_drs_names():
    temporal, vertical, horizontal, area = resolved_labels()
    model = KnownBrandedVariable(
        **known_branded_variable_data(
            temporal_label=temporal,
            vertical_label=vertical,
            horizontal_label=horizontal,
            area_label=area,
        )
    )

    assert model.branding_suffix_name == "tavg-p19-hxy-air"


def test_branding_suffix_rejects_mismatching_resolved_labels():
    temporal, vertical, horizontal, area = resolved_labels()

    with pytest.raises(ValidationError, match="branding_suffix_name must equal"):
        KnownBrandedVariable(
            **known_branded_variable_data(
                branding_suffix_name="wrong",
                temporal_label=temporal,
                vertical_label=vertical,
                horizontal_label=horizontal,
                area_label=area,
            )
        )


def test_project_metadata_may_differ_from_resolved_root():
    model = KnownBrandedVariable(
        **known_branded_variable_data(
            drs_name="Ta_tavg-p19-hxy-air",
            variable_root_name=root_variable(),
            out_name="historicalTa",
            cf_standard_name="project_specific_air_temperature",
            units="degC",
        )
    )

    assert model.out_name == "historicalTa"
    assert model.cf_standard_name == "project_specific_air_temperature"
    assert model.units == "degC"


def test_out_name_may_differ_from_unresolved_variable_id():
    model = KnownBrandedVariable(**known_branded_variable_data(out_name="historicalTa"))

    assert model.variable_root_name == "ta"
    assert model.out_name == "historicalTa"


def test_known_branded_variable_requires_out_name():
    record = known_branded_variable_data()
    del record["out_name"]

    with pytest.raises(ValidationError, match="out_name"):
        KnownBrandedVariable(**record)


def test_known_branded_variable_accepts_resolved_data_coordinates():
    coordinate = data_coordinate()
    model = KnownBrandedVariable(**known_branded_variable_data(dimensions=[coordinate]))

    assert model.dimensions == [coordinate]


def test_known_branded_variable_accepts_missing_long_name():
    record = known_branded_variable_data()
    del record["long_name"]

    assert KnownBrandedVariable(**record).long_name is None


def test_description_remains_the_inherited_scalar_field():
    model = KnownBrandedVariable(**known_branded_variable_data(description="Canonical project description"))

    assert model.description == "Canonical project description"
    with pytest.raises(ValidationError, match="description"):
        KnownBrandedVariable(**known_branded_variable_data(description=["First", "Second"]))


def test_cell_metadata_and_flags_have_proposal_defaults():
    model = KnownBrandedVariable(**known_branded_variable_data())

    assert model.cell_methods is None
    assert model.cell_measures is None
    assert model.flag_values is None
    assert model.flag_meanings is None


def test_additional_text_metadata_has_proposal_defaults():
    model = KnownBrandedVariable(**known_branded_variable_data())

    assert model.var_def_qualifier is None
    assert model.history is None
    assert model.bn_status is None
    assert model.cf_sn_status is None
    assert model.compound_name is None
    assert model.table_id is None
    assert model.frequency is None


def test_additional_text_metadata_is_preserved():
    model = KnownBrandedVariable(
        **known_branded_variable_data(
            var_def_qualifier="at 2 m",
            history="Added for CMIP7",
            bn_status="accepted",
            cf_sn_status="current",
        )
    )

    assert model.var_def_qualifier == "at 2 m"
    assert model.history == "Added for CMIP7"
    assert model.bn_status == "accepted"
    assert model.cf_sn_status == "current"


def test_project_specific_legacy_metadata_is_preserved():
    model = KnownBrandedVariable(
        **known_branded_variable_data(
            compound_name=["ta19", "ta27"],
            table_id=["Amon", "CFmon"],
            frequency=["mon", "day"],
        )
    )

    assert model.compound_name == ["ta19", "ta27"]
    assert model.table_id == ["Amon", "CFmon"]
    assert model.frequency == ["mon", "day"]


def test_flag_values_and_meanings_must_have_equal_lengths():
    model = KnownBrandedVariable(
        **known_branded_variable_data(
            flag_values=[0, 1],
            flag_meanings=["clear", "cloudy"],
        )
    )
    assert model.flag_values == [0, 1]
    assert model.flag_meanings == ["clear", "cloudy"]

    with pytest.raises(ValidationError, match="must have equal lengths"):
        KnownBrandedVariable(
            **known_branded_variable_data(
                flag_values=[0, 1],
                flag_meanings=["clear"],
            )
        )


def test_flag_meanings_must_not_contain_empty_strings():
    with pytest.raises(ValidationError):
        KnownBrandedVariable(
            **known_branded_variable_data(
                flag_values=[0],
                flag_meanings=[""],
            )
        )


@pytest.mark.parametrize(
    ("flag_values", "flag_meanings"),
    [
        ([0], None),
        (None, ["clear"]),
    ],
)
def test_flag_values_and_meanings_must_be_provided_together(flag_values, flag_meanings):
    with pytest.raises(ValidationError, match="must be provided together"):
        KnownBrandedVariable(
            **known_branded_variable_data(
                flag_values=flag_values,
                flag_meanings=flag_meanings,
            )
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cf_standard_name", ""),
        ("long_name", " "),
        ("branding_suffix_name", " "),
        ("out_name", ""),
        ("variable_root_name", ""),
        ("temporal_label", ""),
        ("vertical_label", ""),
        ("horizontal_label", ""),
        ("area_label", ""),
        ("dimensions", []),
        ("dimensions", [""]),
        ("compound_name", [""]),
        ("table_id", [" "]),
        ("frequency", [""]),
    ],
)
def test_known_branded_variable_rejects_empty_metadata(field, value):
    with pytest.raises(ValidationError):
        KnownBrandedVariable(**known_branded_variable_data(**{field: value}))


@pytest.mark.parametrize(
    "field",
    [
        "units",
        "cell_methods",
        "cell_measures",
        "realm",
        "var_def_qualifier",
        "history",
        "bn_status",
        "cf_sn_status",
    ],
)
def test_known_branded_variable_rejects_empty_optional_text(field):
    with pytest.raises(ValidationError, match="cannot be empty"):
        KnownBrandedVariable(**known_branded_variable_data(**{field: ""}))


def test_known_branded_variable_fields_match_proposal():
    inherited_fields = {"id", "type", "drs_name", "description"}
    proposal_fields = {
        "cf_standard_name",
        "long_name",
        "units",
        "var_def_qualifier",
        "history",
        "bn_status",
        "cf_sn_status",
        "variable_root_name",
        "branding_suffix_name",
        "out_name",
        "dimensions",
        "cell_methods",
        "cell_measures",
        "realm",
        "temporal_label",
        "vertical_label",
        "horizontal_label",
        "area_label",
        "flag_values",
        "flag_meanings",
        "compound_name",
        "table_id",
        "frequency",
    }

    assert set(KnownBrandedVariable.model_fields) == inherited_fields | proposal_fields


def test_legacy_database_record_uses_legacy_model():
    record = {
        "id": "mrro_tavg-u-hxy-lnd",
        "type": "known_branded_variable",
        "drs_name": "mrro_tavg-u-hxy-lnd",
        "description": "Total runoff",
        "cf_standard_name": "runoff_flux",
        "cf_units": "kg m-2 s-1",
        "cf_sn_status": "approved",
        "variable_root_name": "mrro",
        "var_def_qualifier": "",
        "branding_suffix_name": "tavg-u-hxy-lnd",
        "dimensions": ["longitude", "latitude", "time"],
        "cell_methods": "area: mean where land time: mean",
        "cell_measures": "area: areacella",
        "history": ": registered",
        "realm": "land",
        "temporal_label": "tavg",
        "vertical_label": "u",
        "horizontal_label": "hxy",
        "area_label": "lnd",
        "bn_status": "accepted",
        "positive_direction": "",
    }

    registered_model = get_pydantic_class("known_branded_variable")
    model = TypeAdapter(registered_model).validate_python(record)

    assert registered_model is KnownBrandedVariableModel
    assert isinstance(model, KnownBrandedVariableLegacy)
    assert model.var_def_qualifier == ""
    assert not hasattr(model, "out_name")


def test_current_database_record_uses_current_model():
    model = TypeAdapter(KnownBrandedVariableModel).validate_python(
        known_branded_variable_data()
    )

    assert type(model) is KnownBrandedVariable
