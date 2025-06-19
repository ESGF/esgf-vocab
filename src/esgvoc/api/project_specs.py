from enum import Enum
from typing import Annotated, Any, Literal, Optional, Protocol

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


class GlobalAttributeValueType(str, Enum):
    """
    The types of global attribute values.
    """

    STRING = "string"
    """String value type."""
    INTEGER = "integer"
    """Integer value type."""
    FLOAT = "float"
    """Float value type."""


class GlobalAttributeVisitor(Protocol):
    """
    Specifications for a global attribute visitor.
    """
    def visit_base_attribute(self,
                             attribute_name: str,
                             attribute: "GlobalAttributeSpecBase") -> Any:
        """Visit a base global attribute."""
        pass

    def visit_specific_attribute(self,
                                 attribute_name: str,
                                 attribute: "GlobalAttributeSpecSpecific") -> Any:
        """Visit a specific global attribute."""
        pass


class GlobalAttributeSpecBase(BaseModel):
    """
    Specification for a global attribute.
    """

    source_collection: str
    """the source_collection to get the term from"""
    value_type: GlobalAttributeValueType
    """The expected value type."""

    def accept(self, attribute_name: str, visitor: GlobalAttributeVisitor) -> Any:
        return visitor.visit_base_attribute(attribute_name, self)


class GlobalAttributeSpecSpecific(GlobalAttributeSpecBase):
    """
    Specification for a global attribute.
    with a specific key
    """

    specific_key: str
    """If the validation is for the value of a specific key, for instance description or ui-label """

    def accept(self, attribute_name: str, visitor: GlobalAttributeVisitor) -> Any:
        """
        Accept a global attribute visitor.

        :param attribute_name: The attribute name.
        :param visitor: The global attribute visitor.
        :type visitor: GlobalAttributeVisitor
        :return: Depending on the visitor.
        :rtype: Any
        """
        return visitor.visit_specific_attribute(attribute_name, self)


GlobalAttributeSpec = GlobalAttributeSpecSpecific | GlobalAttributeSpecBase


class GlobalAttributeSpecs(BaseModel):
    """
    Container for global attribute specifications.
    """

    specs: dict[str, GlobalAttributeSpec] = Field(default_factory=dict)
    """The global attributes specifications dictionary."""

    def __str__(self) -> str:
        """Return all keys when printing."""
        return str(list(self.specs.keys()))

    def __repr__(self) -> str:
        """Return all keys when using repr."""
        return f"GlobalAttributeSpecs(keys={list(self.specs.keys())})"

    # Dictionary-like access methods
    def __getitem__(self, key: str) -> GlobalAttributeSpec:
        return self.specs[key]

    def __setitem__(self, key: str, value: GlobalAttributeSpec) -> None:
        self.specs[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self.specs

    def keys(self):
        return self.specs.keys()

    def values(self):
        return self.specs.values()

    def items(self):
        return self.specs.items()


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
    global_attributes_specs: Optional[GlobalAttributeSpecs] = None
    """The global attributes specifications of the project."""
    model_config = ConfigDict(extra="allow")
