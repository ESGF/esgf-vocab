"""
Model (i.e. schema/definition) of the grid_axis data descriptor.

Grid axes are axis definitions specific to non-rectilinear grids
(rotated pole, projected, unstructured).
"""

from typing import Literal

from pydantic import Field, field_validator

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class GridAxis(PlainTermDataDescriptor):
    """
    Grid-specific axis definitions for non-rectilinear grids.

    Examples: grid_latitude, grid_longitude, x, y, i_index, j_index

    These are axis definitions used with rotated pole grids, map projections,
    or unstructured grids. They differ from the standard coordinate axes
    in that they may use different coordinate systems or indexing.

    Common grid axes include:
    - *grid_latitude*/*grid_longitude*: Coordinates in rotated pole grids
    - *x*/*y*: Projection coordinates in meters
    - *x_deg*/*y_deg*: Projection coordinates in degrees
    - *i_index*, *j_index*, *k_index*: Spatial indices for unstructured grids
    - *vertices*: Vertex index for cell boundaries
    """

    long_name: str
    """
    Long descriptive name of the grid axis.

    Examples: "latitude in rotated pole grid", "x coordinate of projection"
    """

    out_name: str | None = None
    """
    Output variable name used in NetCDF files.

    Examples: "rlat", "rlon", "i", "j"
    May be empty for some axes.
    """

    standard_name: str | None = None
    """
    CF standard name for the grid axis.

    Examples: "grid_latitude", "projection_x_coordinate"
    If None, no CF standard name is defined.
    """

    axis: Literal["X", "Y", "Z", ""] | None = None
    """
    CF axis attribute indicating the coordinate type.

    - "X": longitude-like coordinate
    - "Y": latitude-like coordinate
    - "Z": vertical coordinate (rare for grid axes)
    - "" or None: no axis type (e.g., for indices)
    """

    # Data type - uses Field with serialization_alias for CMOR JSON export
    data_type: Literal["double", "integer", ""] | None = Field(
        default=None,
        serialization_alias="type"
    )
    """
    Data type for the grid axis values.

    Note: In CMOR JSON this is serialized as "type".
    """

    units: str
    """
    Units of the grid axis values.

    Examples: "degrees", "m", "1"
    """

    @field_validator("standard_name", "axis", "out_name", mode="before")
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

    @field_validator("data_type", mode="before")
    @classmethod
    def empty_data_type_to_none(cls, v):
        """Convert empty strings to None for data_type."""
        if v == "":
            return None
        return v
