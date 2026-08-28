"""
Model of the grid variable data descriptor.
"""

from typing import Literal

from pydantic import model_validator

from esgvoc.api.data_descriptors._validators import NonEmptyString, validate_valid_range
from esgvoc.api.data_descriptors.coordinate import DataCoordinate
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class GridVariable(PlainTermDataDescriptor):
    """
    A geographic coordinate variable for a non-regular grid.
    """

    data_type: Literal["double", "character", "integer", "real"]
    """
    Data type of the grid variable.
    """

    long_name: NonEmptyString | None = None
    """
    Human-readable name of the grid variable.
    """

    cf_standard_name: NonEmptyString | None = None
    """
    CF standard name associated with the grid variable.
    """

    out_name: NonEmptyString
    """
    Variable name written to the data file.
    """

    units: NonEmptyString
    """
    CF-compliant units string.
    """

    dimensions: list[DataCoordinate | NonEmptyString]
    """
    Coordinates that define the grid variable's dimensions.

    String entries reference :class:`DataCoordinate` terms by ID when they
    have not been resolved.
    """

    valid_min: float | None = None
    """
    Minimum valid value.
    """

    valid_max: float | None = None
    """
    Maximum valid value.
    """

    _validate_range = model_validator(mode="after")(validate_valid_range)
