"""
Model (i.e. schema/definition) of the formula_term data descriptor.

Formula terms are variables used in parametric vertical coordinate formulas.
"""

from typing import Literal

from pydantic import Field, field_validator

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class FormulaTerm(PlainTermDataDescriptor):
    """
    Variables for parametric vertical coordinate formulas.

    Examples: ps, ap, b, orog, depth_c, eta

    These are auxiliary variables required to compute the actual coordinate
    values for parametric vertical coordinates like hybrid sigma-pressure
    or ocean sigma coordinates. They appear in formulas like:
    - "p = ap + b*ps" (hybrid sigma-pressure)
    - "z = eta + sigma*(depth+eta)" (ocean sigma-z)

    Common formula terms include:
    - *ps*: Surface air pressure
    - *ap*, *b*: Hybrid sigma-pressure coefficients
    - *orog*: Surface altitude/orography
    - *depth*: Sea floor depth
    - *eta*: Sea surface height
    - *p0*: Reference pressure
    - *ptop*: Pressure at top of model
    """

    long_name: str
    """
    Long descriptive name of the formula term.

    Examples: "Surface Air Pressure", "vertical coordinate formula term: ap"
    """

    out_name: str
    """
    Output variable name used in NetCDF files.

    Examples: "ps", "ap", "b", "orog"
    """

    dimensions: str
    """
    Dimensions of the formula term variable.

    Space-separated dimension names.
    Examples: "longitude latitude time", "alevel", ""
    """

    units: str
    """
    Units of the formula term values.

    Examples: "Pa", "m", "1"
    """

    # Data type - uses Field with serialization_alias for CMOR JSON export
    data_type: Literal["double", "real", "integer"] | None = Field(
        default=None,
        serialization_alias="type"
    )
    """
    Data type for the formula term values.

    Note: In CMOR JSON this is serialized as "type".
    """

    standard_name: str | None = None
    """
    CF standard name for the formula term.

    Examples: "air_pressure", "reference_air_pressure_for_atmosphere_vertical_coordinate"
    If None, no CF standard name is defined.
    """

    @field_validator("standard_name", mode="before")
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
