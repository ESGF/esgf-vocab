"""
Model of the grid axis data descriptor.
"""

from typing import Literal

from esgvoc.api.data_descriptors._validators import NonEmptyString
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class GridAxis(PlainTermDataDescriptor):
    """
    An index axis used for an unstructured or non-standard grid.
    """

    axis: Literal["X", "Y"] | None = None
    """
    Horizontal axis represented by the grid index.
    """

    data_type: Literal["double", "character", "integer", "real"] | None = None
    """
    Data type of the grid axis variable.
    """

    long_name: NonEmptyString | None = None
    """
    Human-readable name of the grid axis.
    """

    cf_standard_name: NonEmptyString | None = None
    """
    CF standard name associated with the grid axis.
    """

    out_name: NonEmptyString | None = None
    """
    Index variable name written to the data file.
    """

    units: NonEmptyString | None = None
    """
    CF-compliant units string.
    """
