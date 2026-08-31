"""
Model of the formula term data descriptor.
"""

from typing import Literal

from esgvoc.api.data_descriptors._validators import NonEmptyString
from esgvoc.api.data_descriptors.coordinate import DataCoordinate
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class FormulaTerm(PlainTermDataDescriptor):
    """
    A variable used in a parametric vertical coordinate formula.

    Formula terms are the individual variables, such as ``ap``, ``b``, ``ps``,
    or ``orog``, that appear in CF parametric vertical coordinate formulas.
    """

    data_type: Literal["double", "character", "integer", "real"]
    """
    Data type of the formula term variable.
    """

    long_name: NonEmptyString | None = None
    """
    Human-readable name of the formula term.
    """

    cf_standard_name: NonEmptyString | None = None
    """
    CF standard name associated with the formula term.
    """

    out_name: NonEmptyString
    """
    Variable name written to the data file.
    """

    units: NonEmptyString | None = None
    """
    CF-compliant units string.
    """

    dimensions: list[DataCoordinate | NonEmptyString] | None = None
    """
    Coordinates that define the formula term's dimensions.

    String entries reference :class:`DataCoordinate` terms by ID when they
    have not been resolved.
    """
