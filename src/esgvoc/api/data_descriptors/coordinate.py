"""
Model of the CV coordinate data descriptor.
"""

from typing import Literal

from pydantic import model_validator

from esgvoc.api.data_descriptors._validators import NonEmptyString, validate_coordinate_data_type
from esgvoc.api.data_descriptors.coordinate_type import CoordinateType
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class DataCoordinate(PlainTermDataDescriptor):
    """
    A coordinate or dimension definition for climate data files.

    Coordinates describe how spatial, temporal, and other axes are represented
    in a data file. Each coordinate is a standalone vocabulary term identified
    by its ``id``; consumers can use ``coordinate_type`` and other attributes
    to determine which validation or generation rules apply.

    Branded variables reference coordinates by ID in their ``dimensions`` field.

    Examples: "latitude", "longitude", "time", "plev19", "height2m", "basin"
    """

    coordinate_type: CoordinateType | NonEmptyString
    """
    Structural classification of this coordinate.

    References a :class:`CoordinateType` term by ID when it has not been
    resolved.
    """

    axis: Literal["T", "X", "Y", "Z"] | None = None
    """
    CF coordinate axis identifier, when applicable.
    """

    data_type: Literal["character", "double", "integer", "real"]
    """
    Data type expected for the coordinate variable.
    """

    long_name: NonEmptyString | None = None
    """
    Human-readable name / title of the coordinate.
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
    Units of the coordinate.
    """

    positive: Literal["up", "down"] | None = None
    """
    Direction of increasing coordinate values, when applicable.
    """

    stored_direction: Literal["increasing", "decreasing"] | None = None
    """
    Expected storage order of coordinate values, when applicable.
    """

    coordinate_values: list[float | int | NonEmptyString] | NonEmptyString | None = None
    """
    Expected coordinate values, or ``None`` when values are model-dependent.
    """

    coordinate_bounds: list[float | int] | None = None
    """
    Expected coordinate bounds, or ``None`` when not applicable or when bounds are model-dependent.
    """

    bounds_required: bool | None = None
    """
    Whether an associated bounds variable is required.
    """

    tolerance: float | None = None
    """
    Relative tolerance used when matching requested coordinates against values
    and bounds stored in a data file.

    Tolerance applies only to one-dimensional numerical coordinates for which
    multiple values or multiple bound intervals have been requested. It does
    not apply to scalar coordinates: when a single value or a single pair of
    bounds is requested, only ``valid_min`` and ``valid_max`` constrain it.

    Using zero-based Python/C ordering, ``coordinate_values`` is a flat vector
    of shape ``(m,)``. For requested value ``coordinate_values[i]``, the
    permitted absolute difference from the corresponding stored value is the
    smaller of 0.1 percent times ``tolerance`` times its absolute value and
    ``tolerance`` times the adjacent requested-value spacing. The following
    value supplies the spacing for ``i == 0``; the preceding value supplies it
    for subsequent indices.

    ``coordinate_bounds`` is a flat edge vector of shape ``(m + 1,)`` in
    Python/C order, defining interval ``i`` as
    ``[coordinate_bounds[i], coordinate_bounds[i + 1]]``. Each requested bound
    is matched using the smaller of ``tolerance`` times the interval width and
    0.1 percent times ``tolerance`` times the bound's absolute value.

    For example, a tolerance of ``1`` permits deviations of no more than 0.1 percent.
    """

    valid_min: float | None = None
    """
    Minimum valid coordinate value, when defined.
    """

    valid_max: float | None = None
    """
    Maximum valid coordinate value, when defined.
    """

    is_climatology: bool | None = None
    """
    Only applicable for time coordinates (axis == "T"). Whether this time coordinate uses a
    climatology attribute instead of bounds.
    """

    is_generic_model_level_coordinate: bool | None = None
    """
    Only applicable for vertical coordinates (axis == "Z"). Whether this is a generic,
    model-dependent vertical level coordinate.
    """

    @model_validator(mode="after")
    def validate_coordinate_constraints(self):
        """
        Validate relationships between coordinate fields.
        """
        if self.is_climatology and self.axis != "T":
            raise ValueError("is_climatology can only be True when axis is 'T'")
        if self.is_generic_model_level_coordinate and self.axis != "Z":
            raise ValueError("is_generic_model_level_coordinate can only be True when axis is 'Z'")
        return validate_coordinate_data_type(self)
