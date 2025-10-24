"""
Model (i.e. schema/definition) of the variable data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Variable(PlainTermDataDescriptor):
    """
    A climate-related quantity or measurement.

    Examples: "tas", "pr", "psl", "rlut"

    These quantities represent key physical, chemical or biological properties of the Earth system
    and can be the result of direct observation of the climate system or simulations.
    Variables cover a range of aspects of the climate system,
    such as temperature, precipitation, sea level, radiation, or atmospheric composition.
    Some more information for variables that have been used in CMIP:

    - *tas*: Near-surface air temperature (measured at 2 meters above the surface)
    - *pr*: Precipitation
    - *psl*: Sea-level pressure
    - *zg*: Geopotential height
    - *rlut*: Top-of-atmosphere longwave radiation
    - *siconc*: Sea-ice concentration
    - *co2*: Atmospheric CO2 concentration

    Since CMIP7, the concept of a variable has been augmented with the idea of 'branding',
    leading to the idea of a 'branded variable'.
    For details, see :py:class:`BrandedVariable`.

    Sometimes 'variable' is also referred to as 'root name' or 'out name'.
    There is mostly a one to one mapping between CF standard names and variables.
    However, this is not always possible so please don't assume this is always the case.
    """

    long_name: str
    """
    Long name of the variable

    This is free text and can take any value
    """

    standard_name: str | None
    """
    Standard name of the variable

    The standard names are defined by the CF-conventions.

    If `None`, this variable has no standard name according to the CF-conventions.
    """

    units: str
    """
    Units of the variable
    """
