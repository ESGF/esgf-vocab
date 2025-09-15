from enum import Enum

from pydantic import BaseModel, ConfigDict


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


class DrsPart(BaseModel):
    """A fragment of a DRS specification"""

    collection_id: str
    """The collection id."""
    source_collection_term: str | None = None
    "Specifies a specific term in the collection."
    is_required: bool
    """Whether the collection is required for the DRS specification or not."""

    def __str__(self) -> str:
        return self.collection_id


class DrsSpecification(BaseModel):
    """
    A DRS specification.
    """

    type: DrsType
    """The type of the specification."""
    regex: str
    """General pattern for simples checks"""
    separator: str
    """The textual separator string or character."""
    properties: dict | None = None
    """The other specifications (e.g., file name extension for file name DRS specification)."""
    parts: list[DrsPart]
    """The parts of the DRS specification."""


class CatalogProperty(BaseModel):
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
    "The name of the collection referenced in the catalog."
    source_collection_key: str | None = None
    "Specifies a key other than drs_name in the collection."


class CatalogExtension(BaseModel):
    name: str
    """The name of the extension"""
    version: str
    """The version of the extension"""


class CatalogProperties(BaseModel):
    name: str
    """The name of the catalog system."""
    url_template: str
    """The URI template of the catalog system."""
    extensions: list[CatalogExtension]
    """The extensions of the catalog."""


class CatalogSpecification(BaseModel):
    """
    A catalog specifications.
    """

    version: str
    """The version of the catalog."""

    catalog_properties: CatalogProperties
    """The properties of the catalog."""

    dataset_properties: list[CatalogProperty]
    "The properties of the dataset described in a catalog."
    file_properties: list[CatalogProperty]
    "The properties of the files described in a catalog."


class ProjectSpecs(BaseModel):
    """
    A project specifications.
    """

    project_id: str
    """The project id."""
    description: str
    """The description of the project."""
    drs_specs: dict[DrsType, DrsSpecification]
    """The DRS specifications of the project (directory, file name and dataset id)."""
    # TODO: release = None when all projects have catalog_specs.yaml.
    catalog_specs: CatalogSpecification | None = None
    """The catalog specifications of the project."""
    model_config = ConfigDict(extra="allow")
