"""Tests for coordinate-related data descriptor models."""

import pytest
from pydantic import ValidationError

from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING, DataCoordinate
from esgvoc.api.data_descriptors.coordinate_type import CoordinateType
from esgvoc.api.data_descriptors.EMD_models.coordinate import Coordinate as EMDCoordinate
from esgvoc.api.data_descriptors.formula_term import FormulaTerm
from esgvoc.api.data_descriptors.grid_axis import GridAxis
from esgvoc.api.data_descriptors.grid_variable import GridVariable
from esgvoc.api.data_descriptors.model_level_coordinate import ModelLevelCoordinate


def coordinate_data(**updates):
    """Return a complete coordinate record, optionally replacing fields."""
    record = {
        "id": "plev",
        "type": "coordinate",
        "drs_name": "plev",
        "description": "Pressure coordinate",
        "coordinate_type": "standard_1d",
        "long_name": "pressure",
        "cf_standard_name": "air_pressure",
        "units": "Pa",
        "axis": "Z",
        "out_name": "plev",
        "positive": "down",
        "stored_direction": "decreasing",
        "data_type": "double",
        "bounds_required": True,
        "tolerance": 0.0,
        "valid_min": 0.0,
        "valid_max": 110_000.0,
        "coordinate_values": [100_000.0, 85_000.0],
        "coordinate_bounds": None,
        "is_climatology": False,
        "is_generic_model_level_coordinate": False,
    }
    record.update(updates)
    return record


def formula_term_data(dimensions):
    """Return a complete formula-term record."""
    return {
        "id": "ap",
        "type": "formula_term",
        "drs_name": "ap",
        "description": "Hybrid pressure coefficient",
        "long_name": "vertical coordinate formula term: ap",
        "cf_standard_name": "atmosphere_hybrid_sigma_pressure_coordinate",
        "out_name": "ap",
        "dimensions": dimensions,
        "units": "Pa",
        "data_type": "double",
    }


def grid_axis_data(**updates):
    """
    Return a complete grid-axis record.
    """
    record = {
        "id": "i_index",
        "type": "grid_axis",
        "drs_name": "i",
        "description": "Horizontal grid index",
        "axis": "X",
        "long_name": "first horizontal grid index",
        "cf_standard_name": "projection_x_coordinate",
        "data_type": "integer",
        "units": "1",
        "out_name": "i",
    }
    record.update(updates)
    return record


def grid_variable_data(dimensions, **updates):
    """
    Return a complete grid-variable record.
    """
    record = {
        "id": "latitude",
        "type": "grid_variable",
        "drs_name": "latitude",
        "description": "Latitude on a non-regular grid",
        "long_name": "latitude",
        "cf_standard_name": "latitude",
        "out_name": "latitude",
        "dimensions": dimensions,
        "units": "degrees_north",
        "data_type": "double",
        "valid_min": -90.0,
        "valid_max": 90.0,
    }
    record.update(updates)
    return record


def model_level_coordinate_data(z_factors, **updates):
    """
    Return a complete model-level-coordinate record.
    """
    record = {
        "id": "alternate_hybrid_sigma",
        "type": "model_level_coordinate",
        "drs_name": "alternate_hybrid_sigma",
        "description": "Hybrid sigma pressure coordinate",
        "long_name": "hybrid sigma pressure",
        "cf_standard_name": "atmosphere_hybrid_sigma_pressure_coordinate",
        "units": "1",
        "axis": "Z",
        "out_name": "lev",
        "positive": "down",
        "stored_direction": "decreasing",
        "data_type": "double",
        "bounds_required": True,
        "valid_min": 0.0,
        "valid_max": 1.0,
        "formula": "p = ap + b*ps",
        "z_factors": z_factors,
        "z_bounds_factors": None,
        "generic_level_name": "alevel",
    }
    record.update(updates)
    return record


def test_coordinate_accepts_terms_or_ids_for_coordinate_type():
    coordinate_type = CoordinateType(
        id="standard_1d",
        type="coordinate_type",
        drs_name="standard_1d",
        description="One-dimensional coordinate",
    )

    assert DataCoordinate(**coordinate_data()).coordinate_type == "standard_1d"
    assert DataCoordinate(**coordinate_data(coordinate_type=coordinate_type)).coordinate_type == coordinate_type


def test_nullable_coordinate_collections_default_to_none():
    data = coordinate_data()
    del data["coordinate_values"]
    del data["coordinate_bounds"]
    data["tolerance"] = None

    coordinate = DataCoordinate(**data)

    assert coordinate.coordinate_values is None
    assert coordinate.coordinate_bounds is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("axis", "Q"),
        ("positive", "left"),
        ("stored_direction", "unordered"),
        ("data_type", "float32"),
    ],
)
def test_coordinate_rejects_values_outside_literal_contracts(field, value):
    with pytest.raises(ValidationError):
        DataCoordinate(**coordinate_data(**{field: value}))


@pytest.mark.parametrize(
    "descriptor_class",
    [FormulaTerm, GridAxis, GridVariable, ModelLevelCoordinate],
)
def test_coordinate_related_descriptors_reject_invalid_data_types(descriptor_class):
    coordinate = DataCoordinate(**coordinate_data())
    formula_term = FormulaTerm(**formula_term_data([coordinate]))
    valid_records = {
        FormulaTerm: formula_term_data([coordinate]),
        GridAxis: grid_axis_data(),
        GridVariable: grid_variable_data([coordinate]),
        ModelLevelCoordinate: model_level_coordinate_data([formula_term]),
    }

    with pytest.raises(ValidationError, match="data_type"):
        descriptor_class(**(valid_records[descriptor_class] | {"data_type": "float32"}))


def test_climatology_is_only_allowed_for_time_axis():
    with pytest.raises(ValidationError, match="is_climatology can only be True"):
        DataCoordinate(**coordinate_data(is_climatology=True))

    coordinate = DataCoordinate(**coordinate_data(axis="T", is_climatology=True))
    assert coordinate.is_climatology is True


def test_generic_model_level_coordinate_is_only_allowed_for_vertical_axis():
    with pytest.raises(ValidationError, match="is_generic_model_level_coordinate can only be True"):
        DataCoordinate(
            **coordinate_data(
                axis="X",
                is_generic_model_level_coordinate=True,
            )
        )

    coordinate = DataCoordinate(
        **coordinate_data(
            axis="Z",
            is_generic_model_level_coordinate=True,
        )
    )
    assert coordinate.is_generic_model_level_coordinate is True


@pytest.mark.parametrize("coordinate_values", ["land", ["land", "sea"], [], None])
def test_character_coordinate_values_accept_strings(coordinate_values):
    coordinate = DataCoordinate(
        **coordinate_data(
            data_type="character",
            coordinate_values=coordinate_values,
            coordinate_bounds=None,
            bounds_required=False,
            tolerance=None,
            valid_min=None,
            valid_max=None,
        )
    )

    assert coordinate.coordinate_values == coordinate_values


@pytest.mark.parametrize("coordinate_values", ["", " ", ["land", ""]])
def test_character_coordinate_values_reject_empty_strings(coordinate_values):
    with pytest.raises(ValidationError, match="cannot be empty"):
        DataCoordinate(
            **coordinate_data(
                data_type="character",
                coordinate_values=coordinate_values,
                coordinate_bounds=None,
                bounds_required=False,
                tolerance=None,
                valid_min=None,
                valid_max=None,
            )
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("bounds_required", True),
        ("coordinate_bounds", [0, 1]),
        ("coordinate_values", [1]),
        ("tolerance", 1.0),
        ("valid_min", 0.0),
        ("valid_max", 1.0),
    ],
)
def test_character_coordinates_reject_numeric_values_and_bounds(field, value):
    record = {
        "data_type": "character",
        "coordinate_values": ["land"],
        "coordinate_bounds": None,
        "bounds_required": False,
        "tolerance": None,
        "valid_min": None,
        "valid_max": None,
        field: value,
    }
    with pytest.raises(ValidationError, match="character coordinate"):
        DataCoordinate(**coordinate_data(**record))


def test_integer_coordinate_values_and_bounds_remain_integers():
    coordinate = DataCoordinate(
        **coordinate_data(
            data_type="integer",
            coordinate_values=[1, 2],
            coordinate_bounds=[0, 1, 3],
            tolerance=0.0,
        )
    )

    assert all(type(value) is int for value in coordinate.coordinate_values)
    assert all(type(bound) is int for bound in coordinate.coordinate_bounds)


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("coordinate_values", [1.5], "integer coordinate values"),
        ("coordinate_bounds", [0.0, 2.0], "integer coordinate bounds"),
    ],
)
def test_integer_coordinates_reject_float_values_and_bounds(field, value, error):
    record = {
        "data_type": "integer",
        "coordinate_values": [1, 2],
        "coordinate_bounds": [0, 1, 3],
        "tolerance": 0.0,
        field: value,
    }
    with pytest.raises(ValidationError, match=error):
        DataCoordinate(**coordinate_data(**record))


@pytest.mark.parametrize("data_type", ["real", "double"])
def test_real_and_double_coordinate_values_and_bounds_are_floats(data_type):
    coordinate = DataCoordinate(
        **coordinate_data(
            data_type=data_type,
            coordinate_values=[1, 2.5],
            coordinate_bounds=[0, 2, 3],
            tolerance=0.0,
        )
    )

    assert all(type(value) is float for value in coordinate.coordinate_values)
    assert all(type(bound) is float for bound in coordinate.coordinate_bounds)


@pytest.mark.parametrize("data_type", ["real", "double"])
def test_real_and_double_coordinates_reject_character_values(data_type):
    with pytest.raises(ValidationError, match="must be numeric"):
        DataCoordinate(**coordinate_data(data_type=data_type, coordinate_values=["land"]))


@pytest.mark.parametrize(
    ("coordinate_values", "coordinate_bounds"),
    [
        ([1.0], None),
        (None, [0.0, 2.0]),
        (None, None),
    ],
)
def test_tolerance_rejects_scalar_or_missing_requests(coordinate_values, coordinate_bounds):
    with pytest.raises(ValidationError, match="tolerance requires multiple"):
        DataCoordinate(
            **coordinate_data(
                tolerance=1.0,
                coordinate_values=coordinate_values,
                coordinate_bounds=coordinate_bounds,
            )
        )


def test_tolerance_accepts_multiple_requested_bounds_in_m_plus_one_format():
    coordinate = DataCoordinate(
        **coordinate_data(
            tolerance=1.0,
            coordinate_values=None,
            coordinate_bounds=[0.0, 1.0, 2.0],
        )
    )

    assert coordinate.coordinate_bounds == [0.0, 1.0, 2.0]


def test_coordinate_bounds_use_m_plus_one_format():
    with pytest.raises(ValidationError, match=r"m \+ 1 values"):
        DataCoordinate(
            **coordinate_data(
                tolerance=None,
                coordinate_values=[1.0, 2.0],
                coordinate_bounds=[0.0, 3.0],
            )
        )


def test_coordinate_values_must_lie_between_corresponding_bounds():
    with pytest.raises(ValidationError, match="must lie between its corresponding bounds"):
        DataCoordinate(
            **coordinate_data(
                tolerance=None,
                coordinate_values=[1.0, 4.0],
                coordinate_bounds=[0.0, 2.0, 3.0],
            )
        )


@pytest.mark.parametrize(
    ("updates", "error"),
    [
        ({"coordinate_values": [-1.0, 1.0]}, "below valid_min"),
        (
            {
                "coordinate_values": [1.0, 2.0],
                "coordinate_bounds": [0.0, 1.0, 110_001.0],
            },
            "exceed valid_max",
        ),
        ({"valid_min": 2.0, "valid_max": 1.0}, "valid_min cannot be greater"),
    ],
)
def test_requested_values_and_bounds_stay_within_valid_range(updates, error):
    with pytest.raises(ValidationError, match=error):
        DataCoordinate(**coordinate_data(**updates))


@pytest.mark.parametrize(
    ("valid_min", "valid_max"),
    [
        (None, 110_000.0),
        (0.0, None),
        (None, None),
    ],
)
def test_data_coordinate_allows_partially_defined_valid_ranges(valid_min, valid_max):
    coordinate = DataCoordinate(**coordinate_data(valid_min=valid_min, valid_max=valid_max))

    assert coordinate.valid_min == valid_min
    assert coordinate.valid_max == valid_max


def test_formula_term_dimensions_accept_coordinates_and_ids():
    coordinate = DataCoordinate(**coordinate_data())
    formula_term = FormulaTerm(**formula_term_data([coordinate]))

    assert formula_term.dimensions == [coordinate]

    formula_term = FormulaTerm(**formula_term_data(["plev"]))
    assert formula_term.dimensions == ["plev"]


def test_grid_variable_dimensions_accept_coordinates_and_ids():
    coordinate = DataCoordinate(**coordinate_data())
    grid_variable = GridVariable(**grid_variable_data([coordinate]))

    assert grid_variable.dimensions == [coordinate]

    grid_variable = GridVariable(**grid_variable_data(["plev"]))
    assert grid_variable.dimensions == ["plev"]


def test_grid_variable_allows_both_names_to_be_absent():
    coordinate = DataCoordinate(**coordinate_data())
    record = grid_variable_data([coordinate])
    del record["long_name"]
    del record["cf_standard_name"]
    grid_variable = GridVariable(**record)

    assert grid_variable.long_name is None
    assert grid_variable.cf_standard_name is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("out_name", ""),
        ("units", " "),
        ("long_name", ""),
        ("cf_standard_name", " "),
        ("dimensions", [""]),
    ],
)
def test_grid_variable_rejects_empty_strings(field, value):
    record = grid_variable_data(["plev"])
    record[field] = value

    with pytest.raises(ValidationError, match="cannot be empty"):
        GridVariable(**record)


@pytest.mark.parametrize(
    ("valid_min", "valid_max"),
    [
        (None, 90.0),
        (-90.0, None),
        (None, None),
    ],
)
def test_grid_variable_allows_partially_defined_valid_ranges(valid_min, valid_max):
    coordinate = DataCoordinate(**coordinate_data())
    grid_variable = GridVariable(
        **grid_variable_data(
            [coordinate],
            valid_min=valid_min,
            valid_max=valid_max,
        )
    )

    assert grid_variable.valid_min == valid_min
    assert grid_variable.valid_max == valid_max


def test_grid_variable_rejects_reversed_valid_range():
    coordinate = DataCoordinate(**coordinate_data())

    with pytest.raises(ValidationError, match="valid_min cannot be greater"):
        GridVariable(**grid_variable_data([coordinate], valid_min=90.0, valid_max=-90.0))


def test_model_level_coordinate_uses_structured_formula_terms():
    coordinate = DataCoordinate(**coordinate_data(is_generic_model_level_coordinate=True))
    formula_term = FormulaTerm(**formula_term_data([coordinate]))
    model_level = ModelLevelCoordinate(**model_level_coordinate_data([formula_term]))

    assert model_level.z_factors == [formula_term]
    assert model_level.generic_level_name == "alevel"


def test_model_level_coordinate_accepts_resolved_generic_coordinate():
    coordinate = DataCoordinate(**coordinate_data(is_generic_model_level_coordinate=True))
    model_level = ModelLevelCoordinate(**model_level_coordinate_data(None, generic_level_name=coordinate))

    assert model_level.generic_level_name == coordinate


def test_model_level_coordinate_rejects_resolved_non_generic_coordinate():
    coordinate = DataCoordinate(**coordinate_data(is_generic_model_level_coordinate=False))

    with pytest.raises(
        ValidationError,
        match="is_generic_model_level_coordinate=True",
    ):
        ModelLevelCoordinate(**model_level_coordinate_data(None, generic_level_name=coordinate))


def test_model_level_coordinate_rejects_non_vertical_axes():
    coordinate = DataCoordinate(**coordinate_data(is_generic_model_level_coordinate=True))
    formula_term = FormulaTerm(**formula_term_data([coordinate]))

    with pytest.raises(ValidationError, match="axis"):
        ModelLevelCoordinate(**model_level_coordinate_data([formula_term], axis="X"))


@pytest.mark.parametrize(
    ("valid_min", "valid_max"),
    [
        (None, 1.0),
        (0.0, None),
        (None, None),
    ],
)
def test_model_level_coordinate_allows_partially_defined_valid_ranges(valid_min, valid_max):
    coordinate = DataCoordinate(**coordinate_data(is_generic_model_level_coordinate=True))
    formula_term = FormulaTerm(**formula_term_data([coordinate]))
    model_level = ModelLevelCoordinate(
        **model_level_coordinate_data(
            [formula_term],
            valid_min=valid_min,
            valid_max=valid_max,
        )
    )

    assert model_level.valid_min == valid_min
    assert model_level.valid_max == valid_max


def test_model_level_coordinate_rejects_reversed_valid_range():
    coordinate = DataCoordinate(**coordinate_data(is_generic_model_level_coordinate=True))
    formula_term = FormulaTerm(**formula_term_data([coordinate]))

    with pytest.raises(ValidationError, match="valid_min cannot be greater"):
        ModelLevelCoordinate(
            **model_level_coordinate_data(
                [formula_term],
                valid_min=1.0,
                valid_max=0.0,
            )
        )


def test_grid_axis_is_limited_to_horizontal_axes():
    with pytest.raises(ValidationError, match="axis"):
        GridAxis(**grid_axis_data(axis="Z"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("long_name", ""),
        ("cf_standard_name", " "),
        ("units", ""),
        ("out_name", " "),
    ],
)
def test_grid_axis_rejects_empty_strings(field, value):
    with pytest.raises(ValidationError, match="cannot be empty"):
        GridAxis(**grid_axis_data(**{field: value}))


def test_data_coordinate_accepts_missing_long_name():
    record = coordinate_data()
    del record["long_name"]

    assert DataCoordinate(**record).long_name is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("coordinate_type", ""),
        ("long_name", " "),
        ("cf_standard_name", ""),
        ("units", " "),
        ("out_name", ""),
    ],
)
def test_data_coordinate_rejects_empty_strings(field, value):
    with pytest.raises(ValidationError, match="cannot be empty"):
        DataCoordinate(**coordinate_data(**{field: value}))


def test_formula_term_accepts_missing_long_name():
    record = formula_term_data(["plev"])
    del record["long_name"]

    assert FormulaTerm(**record).long_name is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("long_name", ""),
        ("cf_standard_name", " "),
        ("out_name", " "),
        ("units", ""),
        ("dimensions", [""]),
    ],
)
def test_formula_term_rejects_empty_strings(field, value):
    with pytest.raises(ValidationError, match="cannot be empty"):
        FormulaTerm(**(formula_term_data(["plev"]) | {field: value}))


def test_model_level_coordinate_accepts_missing_long_name():
    record = model_level_coordinate_data(None)
    del record["long_name"]

    assert ModelLevelCoordinate(**record).long_name is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("long_name", ""),
        ("cf_standard_name", " "),
        ("units", ""),
        ("out_name", " "),
        ("formula", ""),
        ("z_factors", [""]),
        ("z_bounds_factors", [" "]),
        ("generic_level_name", ""),
    ],
)
def test_model_level_coordinate_rejects_empty_strings(field, value):
    record = model_level_coordinate_data(None)
    record[field] = value

    with pytest.raises(ValidationError, match="cannot be empty"):
        ModelLevelCoordinate(**record)


def test_grid_axis_accepts_missing_names_before_project_resolution():
    grid_axis = GridAxis(**grid_axis_data(long_name=None, cf_standard_name=None))

    assert grid_axis.long_name is None
    assert grid_axis.cf_standard_name is None


def test_grid_axis_allows_base_only_records_without_names():
    grid_axis = GridAxis(
        id="unused",
        type="grid_axis",
        drs_name="unused",
        description="Placeholder grid axis",
    )

    assert grid_axis.long_name is None
    assert grid_axis.cf_standard_name is None


def test_data_coordinate_accepts_absent_standard_name():
    record = coordinate_data()
    del record["cf_standard_name"]

    assert DataCoordinate(**record).long_name == "pressure"


def test_formula_term_accepts_absent_standard_name():
    record = formula_term_data(["plev"])
    del record["cf_standard_name"]

    assert FormulaTerm(**record).long_name


def test_model_level_coordinate_accepts_absent_standard_name():
    record = model_level_coordinate_data(None)
    del record["cf_standard_name"]

    assert ModelLevelCoordinate(**record).long_name == "hybrid sigma pressure"


def test_new_coordinate_descriptor_models_are_registered():
    assert {
        key: DATA_DESCRIPTOR_CLASS_MAPPING[key]
        for key in (
            "data_coordinate",
            "coordinate_type",
            "model_level_coordinate",
            "formula_term",
            "grid_axis",
            "grid_variable",
        )
    } == {
        "data_coordinate": DataCoordinate,
        "coordinate_type": CoordinateType,
        "model_level_coordinate": ModelLevelCoordinate,
        "formula_term": FormulaTerm,
        "grid_axis": GridAxis,
        "grid_variable": GridVariable,
    }


def test_emd_coordinate_registry_mapping_is_unchanged():
    assert DATA_DESCRIPTOR_CLASS_MAPPING["coordinate"] is EMDCoordinate
