"""
Model (i.e. schema/definition) of the axis_dimension data descriptor.

Dimension axes are axes along which data varies (multiple values per axis).
"""

from esgvoc.api.data_descriptors.axis_entry import AxisEntry


class AxisDimension(AxisEntry):
    """
    Dimension axes - axes along which data varies.

    Examples: latitude, longitude, plev19, time, depth, basin, iceband

    These define the shape of data arrays, representing axes with multiple values.
    Dimension axes typically have a `requested` field listing their coordinate values,
    and do not have a single `value` field (unlike scalar coordinates).

    Common dimension axes include:
    - *latitude*/*longitude*: Spatial grid coordinates
    - *plev19*, *plev7*, etc.: Pressure level coordinates with specific level sets
    - *time*: Temporal coordinate
    - *depth*: Ocean depth levels
    - *basin*: Ocean basin index
    - *alt16*, *alt40*: Altitude levels for specific instruments
    """

    pass  # Inherits all fields from AxisEntry
