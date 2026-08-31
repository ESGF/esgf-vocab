"""
Model of the model-level coordinate data descriptor.
"""

from typing import Literal

from pydantic import model_validator

from esgvoc.api.data_descriptors._validators import NonEmptyString, validate_valid_range
from esgvoc.api.data_descriptors.coordinate import DataCoordinate
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
from esgvoc.api.data_descriptors.formula_term import FormulaTerm


class ModelLevelCoordinate(PlainTermDataDescriptor):
    """
    A model-dependent vertical coordinate and its CF formula metadata.
    """

    axis: Literal["Z"]
    """
    CF vertical axis identifier.
    """

    data_type: Literal["double", "integer", "real"]
    """
    Data type of the coordinate variable.
    """

    long_name: NonEmptyString | None = None
    """
    Human-readable name of the coordinate.
    """

    cf_standard_name: NonEmptyString | None = None
    """
    CF standard name associated with the coordinate.
    """

    out_name: NonEmptyString
    """
    Variable or dimension name written to the data file.
    """

    units: NonEmptyString | None = None
    """
    CF-compliant units string.
    """

    positive: Literal["up", "down"]
    """
    Direction of increasing coordinate values.
    """

    stored_direction: Literal["increasing", "decreasing"]
    """
    Expected storage order of coordinate values.
    """

    bounds_required: bool | None = None
    """
    Whether an associated bounds variable is required.
    """

    valid_min: float | None = None
    """
    Minimum valid coordinate value.
    """

    valid_max: float | None = None
    """
    Maximum valid coordinate value.
    """

    formula: NonEmptyString | None = None
    """
    CF parametric vertical coordinate formula.
    """

    z_factors: list[FormulaTerm | NonEmptyString] | None = None
    """
    Formula terms used to calculate coordinate values.
    """

    z_bounds_factors: list[FormulaTerm | NonEmptyString] | None = None
    """
    Formula terms used to calculate coordinate bounds.
    """

    generic_level_name: DataCoordinate | NonEmptyString
    """
    Generic data coordinate to which this model-level coordinate belongs.
    """

    _validate_range = model_validator(mode="after")(validate_valid_range)

    @model_validator(mode="after")
    def validate_generic_level_coordinate(self):
        """
        Require a resolved generic level to be marked as model-dependent.
        """
        if (
            isinstance(self.generic_level_name, DataCoordinate)
            and not self.generic_level_name.is_generic_model_level_coordinate
        ):
            raise ValueError(
                "generic_level_name must reference a DataCoordinate with is_generic_model_level_coordinate=True"
            )
        return self
