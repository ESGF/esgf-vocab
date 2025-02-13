from pydantic import Field
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Variable(PlainTermDataDescriptor):
    """
    A variable refers to a specific type of climate-related quantity or measurement that is \
    simulated and stored in a data file. These variables represent key physical, chemical, or \
    biological properties of the Earth system and are outputs from climate models.
    Each variable captures a different aspect of the climate system, such as temperature, \
    precipitation, sea level, radiation, or atmospheric composition.
    Examples of Variables: tas: Near-surface air temperature (often measured at 2 meters above \
    the surface) pr: Precipitation psl: Sea level pressure zg: Geopotential height rlut: \
    Top-of-atmosphere longwave radiation siconc: Sea ice concentration co2: Atmospheric CO2 concentration
    """
    validation_method: str = Field(default = "list")
    long_name: str 
    standard_name: str|None
    units: str|None