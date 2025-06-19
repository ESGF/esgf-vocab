from pydantic import Field

from esgvoc.api.data_descriptors.data_descriptor import ConfiguredBaseModel, PlainTermDataDescriptor


class Dates(ConfiguredBaseModel):
    phase: str
    from_: int = Field(..., alias="from")  # Cause from is a keyword
    to: int | str


class Member(ConfiguredBaseModel):
    type: str
    institution: str  # id
    dates: list[Dates] = Field(default_factory=list)
    membership_type: str  # prior, current


class Consortium(PlainTermDataDescriptor):
    validation_method: str = Field(default="list")
    name: str | None = None
    status: str | None = None
    changes: str | None
    members: list[Member] = Field(default_factory=list)
    url: str | None
    # TODO: remove default value when all json will have their description.
    description: str = Field(default="")
