"""
Model (i.e. schema/definition) of the variable data descriptor
"""

from typing import Union

from pydantic import Field

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class CoordinateCore(PlainTermDataDescriptor):
    """
    A coordinate variable and auxiliary variable describes how climate data are
    located in space, time, or along other physical or categorical axes.

    Examples: "latitude", "longitude", "time", "plev", "height2m", "basin"

    Coordinates define the reference system used to interpret the values of
    climate variables. They provide information about where and when data are
    valid, and how values are organised along physical, temporal, vertical,
    spectral, or categorical dimensions.

    Unlike variables, coordinates do not represent measured quantities themselves;
    they describe the domain over which variables are defined. There is generally
    a close relationship between CF standard names and coordinates, but multiple
    coordinates may exist for a similar physical concept (e.g. model levels,
    pressure levels, scalar heights, projected axes), so this mapping should not
    be assumed to be one-to-one.

    """

    data_type: str
    """
    Data type expected for the coordinate.

    """

    cf_standard_name: str | None = None
    """
    CF standard name associated with the coordinate.

    """

    long_name: str | None = None
    """
    Human-readable long name of the coordinate.
    """

    description: str | None = None
    """
    Free-text description of the coordinate.
    """

    axis: str | None = Field(default=None, pattern=r"^[XYZT]$")
    """
    Coordinate axis when applicable.

    Allowed values are "X", "Y", "Z" and "T".
    """

    positive: str | None = None
    """
    Positive direction for vertical coordinates when applicable.

    Allowed values are "up" or "down".
    """

    direction: str | None = None
    """
    Expected storage direction of coordinate values when applicable.

    Allowed values are "increasing" or "decreasing".
    """

    units: str | None = None
    """
    Units of the coordinate.

    """

    has_bounds: bool | None = None
    """
    Whether coordinate bounds are expected.
    """

    value: Union[int, float, str] | None = None
    """
    Scalar coordinate value.

    """

    lower_bound: Union[float, int] | None = None
    """
    Lower scalar bound when the coordinate defines a single bounded value.
    """

    upper_bound: Union[float, int] | None = None
    """
    Upper scalar bound when the coordinate defines a single bounded value.
    """

    values: list[Union[int, float, str]] | None = None
    """
    Requested coordinate values.

    This comes from the DReq `requested_values` column.
    """

    bounds: list[Union[float, int]] | None = None
    """
    Requested coordinate bounds.

    This comes from the DReq `requested_bounds` column.
    """

    valid_min: Union[float, int] | None = None
    """
    Minimum valid value, when defined.
    """

    valid_max: Union[float, int] | None = None
    """
    Maximum valid value, when defined.
    """

    size: int | None = None
    """
    Declared coordinate size, when defined.
    """

    is_climatology: bool | None = None
    """
    Whether the coordinate represents climatological time.
    """
