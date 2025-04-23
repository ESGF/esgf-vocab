from typing import Optional

from pydantic import Field

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Source(PlainTermDataDescriptor):
    """
    A 'source' refers to a numerical representations of the Earth's climate system. They simulate \
    the interactions between the atmosphere, oceans, land surface, and ice. These models are based \
    on fundamental physical, chemical, and biological processes and are used to understand past, \
    present, and future climate conditions. Each source or model is typically associated with a \
    specific research institution, center, or group. For instance, models like 'EC-Earth' are \
    developed by a consortium of European institutes, while 'GFDL-CM4' is developed by the \
    Geophysical Fluid Dynamics Laboratory (GFDL) in the United States.
    """

    activity_participation: list[str] | None
    cohort: list[str] = Field(default_factory=list)
    organisation_id: list[str] = Field(default_factory=list)
    label: str
    label_extended: Optional[str] = None
    license: dict = Field(default_factory=dict)
    model_component: Optional[dict] = None
    release_year: Optional[int] = None
