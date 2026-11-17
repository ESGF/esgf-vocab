"""
Model (i.e. schema/definition) of the nominal resolution data descriptor
"""

from pydantic import field_validator, model_validator

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
    magnitude: float | None = None
    """
    Magnitude of the nominal resolution.

    This is omitted for the ``none`` term, for which nominal resolution is
    not applicable.
    """

    range: tuple[float, float] | None = None
    """
    Range of mean resolutions to which this nominal resolution applies.

    This is omitted for the ``none`` term.
    """

    units: str | None = None
    """
    Units of the nominal resolution and range.

    This is omitted for the ``none`` term.
    """

    @field_validator("range")
    @classmethod
    def validate_range(cls, v):
        """Validate that range has exactly 2 values and min <= max."""
        if v is None:
            return v

        if len(v) != 2:
            msg = f"range must contain exactly 2 values [min, max]. Received: {v}"
            raise ValueError(msg)

        if v[0] > v[1]:
            msg = f"range[0] must be <= range[1]. Received: {v}"
            raise ValueError(msg)

        return v

    @model_validator(mode="after")
    def validate_resolution_metadata(self):
        """Require numerical metadata except when resolution is not applicable."""
        metadata = {
            "magnitude": self.magnitude,
            "range": self.range,
            "units": self.units,
        }

        if self.id == "none":
            supplied = [name for name, value in metadata.items() if value is not None]
            if supplied:
                msg = (
                    "the 'none' nominal resolution must not define numerical metadata; "
                    f"received: {', '.join(supplied)}"
                )
                raise ValueError(msg)
            return self

        missing = [name for name, value in metadata.items() if value is None]
        if missing:
            msg = (
                "nominal resolutions other than 'none' must define magnitude, range, "
                f"and units; missing: {', '.join(missing)}"
            )
            raise ValueError(msg)

        return self
