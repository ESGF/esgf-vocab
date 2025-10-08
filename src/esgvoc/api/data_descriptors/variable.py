from pydantic import Field

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Variable(PlainTermDataDescriptor):
    """
    A climate-related quantity or measurement.

    These quantities represent key physical, chemical or biological properties of the Earth system
    and can be the result of direct observation of the climate system or simulations.
    Variables cover a range of aspects of the climate system,
    such as temperature, precipitation, sea level, radiation, or atmospheric composition.
    Some examples of variables that have been used in CMIP:

    - *tas*: Near-surface air temperature (often measured at 2 meters above the surface)
    - *pr*: Precipitation
    - *psl*: Sea-level pressure
    - *zg*: Geopotential height
    - *rlut*: Top-of-atmosphere longwave radiation
    - *siconc*: Sea-ice concentration
    - *co2*: Atmospheric CO2 concentration

    Since CMIP7, the concept of a variable has been augmented with the idea of 'branding',
    leading to the idea of a 'branded variable'.
    For details, see :py:class:`BrandedVariable`.
    """

    validation_method: str = Field(default="list")
    long_name: str
    standard_name: str | None
    units: str | None
