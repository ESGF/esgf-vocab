from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class DrsType(str, Enum):
    """
    The types of DRS specification (directory, file name and dataset id).
    """
    directory = "directory"
    """The DRS directory specification type."""
    file_name = "file_name"
    """The DRS file name specification type."""
    dataset_id = "dataset_id"
    """The DRS dataset id specification type."""


class DrsPartKind(str, Enum):
    """
    The kinds of DRS part (constant and collection).
    """
    constant = "constant"
    """The constant part type."""
    collection = "collection"
    """The collection part type."""


class DrsConstant(BaseModel):
    """
    A constant part of a DRS specification (e.g., cmip5).
    """
    value: str
    """The value of the a constant part."""
    kind: Literal[DrsPartKind.constant] = DrsPartKind.constant
    """The DRS part kind."""
    def __str__(self) -> str:
        return self.value


class DrsCollection(BaseModel):
    """
    A collection part of a DRS specification (e.g., institution_id for CMIP6).
    """
    collection_id: str
    """The collection id."""
    is_required: bool
    """Whether the collection is required for the DRS specification or not."""
    kind: Literal[DrsPartKind.collection] = DrsPartKind.collection
    """The DRS part kind."""
    def __str__(self) -> str:
        return self.collection_id


DrsPart = Annotated[DrsConstant | DrsCollection, Field(discriminator="kind")]
"""A fragment of a DRS specification"""


class DrsSpecification(BaseModel):
    """
    A DRS specification.
    """
    type: DrsType
    """The type of the specification."""
    separator: str
    """The textual separator string or character."""
    properties: dict|None = None
    """The other specifications (e.g., file name extension for file name DRS specification)."""
    parts: list[DrsPart]
    """The parts of the DRS specification."""

class ProjectSpecs(BaseModel):
    """
    A project specifications.
    """
    project_id: str
    """The project id."""
    description: str
    """The description of the project."""
    drs_specs: list[DrsSpecification]
    """The DRS specifications of the project (directory, file name and dataset id."""
    model_config = ConfigDict(extra = "allow")