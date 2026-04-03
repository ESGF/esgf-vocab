"""
Model (i.e. schema/definition) of the axis_entry base data descriptor.

This module defines the base class for CMOR axis_entry items,
shared by both axis_dimension (dimension axes) and axis_coordinate (scalar coordinates).
"""

from typing import Literal

from pydantic import Field, field_validator

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class AxisEntry(PlainTermDataDescriptor):
    """
    Base class for CMOR axis_entry items.

    This class represents the common structure shared by both dimension axes
    (axes along which data varies, e.g., latitude, longitude, plev19, time)
    and scalar/fixed coordinates (single-value coordinates, e.g., depth100m, height2m, p500).

    The distinction between dimensions and coordinates is determined by whether
    the axis has multiple values (dimension) or a single fixed value (coordinate).
    """

    # Required fields
    long_name: str
    """
    Long descriptive name of the axis.

    Examples: "Latitude", "Pressure Levels (19)", "depth"
    """

    out_name: str
    """
    Output variable name used in NetCDF files.

    Examples: "lat", "plev", "depth"
    """

    units: str
    """
    Units of the axis values.

    Examples: "degrees_north", "Pa", "m", "days since ?"
    """

    # Optional CF/axis metadata
    standard_name: str | None = None
    """
    CF standard name for the axis.

    Examples: "latitude", "air_pressure", "depth"
    If None, no CF standard name is defined for this axis.
    """

    axis: Literal["X", "Y", "Z", "T", ""] | None = None
    """
    CF axis attribute indicating the coordinate type.

    - "X": longitude-like coordinate
    - "Y": latitude-like coordinate
    - "Z": vertical coordinate
    - "T": time coordinate
    - "" or None: no axis type defined
    """

    positive: Literal["up", "down", ""] | None = None
    """
    Direction of increasing coordinate values for vertical axes.

    - "up": values increase upward (e.g., height)
    - "down": values increase downward (e.g., pressure, depth)
    - "" or None: not applicable
    """

    stored_direction: Literal["increasing", "decreasing", ""] | None = None
    """
    Direction in which coordinate values are stored in the file.

    - "increasing": values increase with index
    - "decreasing": values decrease with index
    - "" or None: not specified
    """

    # Data type - uses Field with serialization_alias for CMOR JSON export
    data_type: Literal["double", "real", "integer", "character"] | None = Field(
        default=None,
        serialization_alias="type"
    )
    """
    Data type for the axis values.

    Note: In CMOR JSON this is serialized as "type".
    """

    # Bounds and values
    must_have_bounds: bool = False
    """
    Whether this axis requires bounds variables.

    In CMOR JSON this is represented as "yes"/"no" strings.
    """

    requested: list[str] | None = None
    """
    List of requested coordinate values as strings.

    Used for dimension axes with predefined values (e.g., pressure levels).
    """

    requested_bounds: list[str] | None = None
    """
    List of requested bounds values as strings.

    Pairs of values defining the boundaries for each requested value.
    """

    bounds_values: str | None = None
    """
    Bounds values specification.
    """

    value: str | None = None
    """
    Single coordinate value for scalar/fixed coordinates.

    Examples: "100." for depth100m, "2." for height2m
    If present, this axis represents a fixed coordinate rather than a dimension.
    """

    # Validation
    valid_min: str | None = None
    """
    Minimum valid value for the axis.
    """

    valid_max: str | None = None
    """
    Maximum valid value for the axis.
    """

    tolerance: str | None = None
    """
    Tolerance for coordinate value matching.
    """

    # Vertical coordinate formulas
    formula: str | None = None
    """
    Formula for parametric vertical coordinates.

    Examples: "p = ap + b*ps" for hybrid sigma-pressure coordinates.
    """

    z_factors: str | None = None
    """
    Formula terms required for computing the coordinate.

    Space-separated list of formula term variable names.
    """

    z_bounds_factors: str | None = None
    """
    Formula terms required for computing coordinate bounds.
    """

    generic_level_name: str | None = None
    """
    Generic level name for parametric coordinates.

    Examples: "alevel", "olevel"
    """

    # Special
    climatology: bool | str | None = None
    """
    Climatology indicator or bounds variable name.

    Can be:
    - True: indicates this is a climatology time axis
    - A string: the name of the climatology bounds variable
    - None: not a climatology axis
    """

    @field_validator("must_have_bounds", mode="before")
    @classmethod
    def convert_must_have_bounds(cls, v):
        """Convert CMOR 'yes'/'no' strings to boolean."""
        if isinstance(v, str):
            return v.lower() == "yes"
        return v

    @field_validator("positive", "stored_direction", "axis", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        """Convert empty strings to None for optional fields."""
        if v == "":
            return None
        return v

    @field_validator("units", mode="before")
    @classmethod
    def normalize_units(cls, v):
        """Normalize dimensionless units."""
        if v == "":
            return "1"
        return v
