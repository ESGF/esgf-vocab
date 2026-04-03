"""
Model (i.e. schema/definition) of the axis_coordinate data descriptor.

Scalar/fixed value coordinates are single-value coordinates or reference points.
"""

from esgvoc.api.data_descriptors.axis_entry import AxisEntry


class AxisCoordinate(AxisEntry):
    """
    Scalar/fixed value coordinates.

    Examples: depth100m, height2m, p500, deltasigt, lambda550nm

    These are single-value coordinates (fixedScalar) or reference points that
    represent a specific location along an axis rather than a dimension along
    which data varies. They typically have a `value` field specifying the
    fixed coordinate value.

    Common scalar coordinates include:
    - *depth100m*, *depth1000m*: Fixed ocean depth levels
    - *height2m*, *height10m*, *height100m*: Fixed heights above surface
    - *p500*, *p700*, *p850*: Fixed pressure levels
    - *lambda550nm*: Fixed wavelength for radiation variables
    - *sdepth*: Soil depth reference points

    Note: This collection is distinct from the EMD_models/coordinate.py which
    defines vertical coordinate *types* (e.g., `depth`, `air_pressure`).
    This collection defines specific axis *instances* with fixed values.
    """

    pass  # Inherits all fields from AxisEntry
