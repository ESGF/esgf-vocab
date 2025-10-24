"""
Model (i.e. schema/definition) of the contributor member data descriptor
"""

from pydantic import BaseModel, Field, HttpUrl

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Location(BaseModel):
    """Location"""

    city: str
    """
    City
    """

    country: str
    """
    Country
    """

    lat: float = Field(ge=-90.0, le=90.0)
    """
    Latitude in degrees north
    """

    lon: float = Field(ge=0.0, le=360.0)
    """
    Longitude in degrees east
    """


class ContributorMember(PlainTermDataDescriptor):
    """
    A registered contributor member

    Examples: "IPSL", "CR", "NCAR", "CNRM"

    Unlike :py:class:`Contributor`, this can only refer to a single entity
    (institute, group, person).
    """

    acronyms: list[str]
    """
    Known acronyms for this member/entity apart from the registered one

    The registered/official acronym is given in `self.drs_name`.
    """

    labels: list[str]
    """
    Labels that can be used for this institute

    These are free-text and can be used when the member/entity needs to be referred to in full,
    rather than by its acronym.
    This can also be thought of as 'long names'.
    """
    # TODO: discuss whether there is any meaning to the order of these
    # and what it means to have more than one label.
    # TODO: discuss whether we should just call this long_names
    # for consistency with other conventions.

    location: list[Location]
    """
    Location(s) of the institute
    """

    ror: str | None
    """
    Research organisation registry (https://ror.org/) ID

    If `None`, this organisation is not registered with ROR
    or the ROR was not supplied at the time of registration.
    """

    urls: list[HttpUrl]
    """
    URL(s) relevant for finding out more information about this member/entity
    """
