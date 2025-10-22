from pydantic import Field

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Institution(PlainTermDataDescriptor):
    """
    An registered institution for WCRP modelisation MIP.
    """

    acronyms: list[str] = Field(
        default_factory=list, description="it is the acronym that btw doesnt belong here anymore"
    )
    aliases: list[str] = Field(default_factory=list)
    established: int | None
    labels: list[str] = Field(default_factory=list)
    location: dict = Field(default_factory=dict)
    name: str
    ror: str | None
    url: list[str] = Field(default_factory=list)
