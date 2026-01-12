"""
Model (i.e. schema/definition) of the nominal resolution data descriptor
"""

from pydantic import field_validator

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class NominalResolution(PlainTermDataDescriptor):
    """
    Approximate horizontal resolution of a dataset

    Examples: "1 km", "250 km", "500 km"

    This should be calculated following the algorithm implemented by
    [https://github.com/PCMDI/nominal_resolution/blob/master/lib/api.py]()
    (although, of course, other implementations of the same algorithm could be used).
    """

    # Developer note: given this isn't a pattern term data descriptor,
    # these are split so people don't have to parse the drs_name themselves.
    magnitude: float
    """
    Magnitude of the nominal resolution
    """

    range: tuple[float, float]
    """
    Range of mean resolutions to which this nominal resolution applies
    """

    units: str
    """
    Units of the nominal resolution and range
    """

    @field_validator("range")
    @classmethod
    def validate_range(cls, v):
        """Validate that range has exactly 2 values and min <= max."""
        if len(v) != 2:
            msg = f"range must contain exactly 2 values [min, max]. Received: {v}"
            raise ValueError(msg)

        if v[0] > v[1]:
            msg = f"range[0] must be <= range[1]. Received: {v}"
            raise ValueError(msg)

        return v
