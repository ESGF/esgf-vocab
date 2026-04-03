"""
Model (i.e. schema/definition) of the grid_variable data descriptor.

Grid variables are auxiliary coordinate variables for non-rectilinear grids,
typically 2D arrays of latitude and longitude values.
"""

from typing import Literal

from pydantic import Field, field_validator

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class GridVariable(PlainTermDataDescriptor):
    """
    Grid auxiliary coordinate variables (2D lat/lon arrays).

    Examples: latitude, longitude, vertices_latitude, vertices_longitude

    These are variables that provide geographic coordinates for non-rectilinear
    grids where latitude and longitude vary as 2D functions of the grid indices.
    Used with rotated pole grids, curvilinear grids, and unstructured grids.

    Common grid variables include:
    - *latitude*/*longitude*: 2D arrays of geographic coordinates
    - *vertices_latitude*/*vertices_longitude*: Cell vertex coordinates
    """

    long_name: str | None = None
    """
    Long descriptive name of the grid variable.

    Examples: "latitude", "longitude"
    May be None for auxiliary variables like vertices.
    """

    out_name: str
    """
    Output variable name used in NetCDF files.

    Examples: "latitude", "longitude", "vertices_latitude"
    """

    dimensions: str
    """
    Dimensions of the grid variable.

    Space-separated dimension names.
    Examples: "longitude latitude", "vertices longitude latitude"
    """

    units: str
    """
    Units of the grid variable values.

    Examples: "degrees_north", "degrees_east"
    """

    # Data type - uses Field with serialization_alias for CMOR JSON export
    data_type: Literal["double", "real"] | None = Field(
        default=None,
        serialization_alias="type"
    )
    """
    Data type for the grid variable values.

    Note: In CMOR JSON this is serialized as "type".
    """

    standard_name: str | None = None
    """
    CF standard name for the grid variable.

    Examples: "latitude", "longitude"
    If None, no CF standard name is defined.
    """

    valid_min: str | None = None
    """
    Minimum valid value for the variable.

    Examples: "-90.0" for latitude, "0.0" for longitude
    """

    valid_max: str | None = None
    """
    Maximum valid value for the variable.

    Examples: "90.0" for latitude, "360.0" for longitude
    """

    @field_validator("standard_name", "long_name", mode="before")
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
