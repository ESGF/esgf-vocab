from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class DrsType(str, Enum):
    """
    The types of DRS specification (directory, file name and dataset id).
    """

    DIRECTORY = "directory"
    """The DRS directory specification type."""
    FILE_NAME = "file_name"
    """The DRS file name specification type."""
    DATASET_ID = "dataset_id"
    """The DRS dataset id specification type."""


class DrsPartKind(str, Enum):
    """
    The kinds of DRS part (constant and collection).
    """

    CONSTANT = "constant"
    """The constant part type."""
    COLLECTION = "collection"
    """The collection part type."""


class DrsConstant(BaseModel):
    """
    A constant part of a DRS specification (e.g., cmip5).
    """

    value: str
    """The value of the a constant part."""
    kind: Literal[DrsPartKind.CONSTANT] = DrsPartKind.CONSTANT
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
    kind: Literal[DrsPartKind.COLLECTION] = DrsPartKind.COLLECTION
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
    properties: dict | None = None
    """The other specifications (e.g., file name extension for file name DRS specification)."""
    parts: list[DrsPart]
    """The parts of the DRS specification."""


class FileProperty(BaseModel):
    """
    A file property described in a catalog.
    """

    source_collection: str
    "The project collection that originated the property."
    catalog_field_value_type: str
    "The type of the field value."
    is_required: bool
    "Specifies if the property must be present in the file properties."


class DatasetProperty(BaseModel):
    """
    A dataset property described in a catalog.
    """

    source_collection: str
    "The project collection that originated the property."
    catalog_field_value_type: str
    "The type of the field value."
    is_required: bool
    "Specifies if the property must be present in the dataset properties."
    source_collection_term: str | None = None
    "Specifies a specific term in the collection."
    catalog_field_name: str | None = None
    "The field name of the collection referenced in the catalog."


class CatalogSpecification(BaseModel):
    """
    A catalog specifications.
    """

    dataset_properties: list[DatasetProperty]
    "The properties of the dataset described in a catalog."
    file_properties: list[FileProperty]
    "The properties of the files described in a catalog."


class ProjectSpecs(BaseModel):
    """
    A project specifications.
    """

    project_id: str
    """The project id."""
    description: str
    """The description of the project."""
    drs_specs: list[DrsSpecification]
    """The DRS specifications of the project (directory, file name and dataset id)."""
    # TODO: release = None when all projects have catalog_specs.yaml.
    catalog_specs: CatalogSpecification | None = None
    """The catalog specifications of the project."""
    model_config = ConfigDict(extra="allow")
