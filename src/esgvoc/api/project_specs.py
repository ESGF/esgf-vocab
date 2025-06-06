from enum import Enum
from typing import Annotated, Literal, Optional

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
    BOOLEAN = "boolean"
    """Boolean value type."""
    DATETIME = "datetime"
    """Datetime value type."""
    LIST = "list"
    """List value type."""


class GlobalAttributeSourceKind(str, Enum):
    """
    The kinds of global attribute sources.
    """

    DIRECT = "direct"
    """Direct field specification."""
    COLLECTION = "collection"
    """Value from a collection."""
    CONSTANT = "constant"
    """Constant value."""
    COMPUTED = "computed"
    """Computed/derived value."""


class GlobalAttributeDirectSource(BaseModel):
    """
    A direct source for a global attribute (field-based with optional default).
    """

    default_value: Optional[str] = None
    """Optional default value if not provided elsewhere."""
    kind: Literal[GlobalAttributeSourceKind.DIRECT] = GlobalAttributeSourceKind.DIRECT
    """The source kind."""


class GlobalAttributeCollectionSource(BaseModel):
    """
    A collection source for a global attribute.
    """

    collection_id: str
    """The collection ID to reference."""
    kind: Literal[GlobalAttributeSourceKind.COLLECTION] = GlobalAttributeSourceKind.COLLECTION
    """The source kind."""


class GlobalAttributeConstantSource(BaseModel):
    """
    A constant source for a global attribute.
    """

    value: str
    """The constant value."""
    kind: Literal[GlobalAttributeSourceKind.CONSTANT] = GlobalAttributeSourceKind.CONSTANT
    """The source kind."""


class GlobalAttributeComputedSource(BaseModel):
    """
    A computed source for a global attribute.
    """

    computation_rule: str
    """The computation rule or formula."""
    kind: Literal[GlobalAttributeSourceKind.COMPUTED] = GlobalAttributeSourceKind.COMPUTED
    """The source kind."""


GlobalAttributeSource = Annotated[
    GlobalAttributeDirectSource
    | GlobalAttributeCollectionSource
    | GlobalAttributeConstantSource
    | GlobalAttributeComputedSource,
    Field(discriminator="kind"),
]
"""A source specification for a global attribute"""


class GlobalAttributeSpec(BaseModel):
    """
    Specification for a global attribute.
    """

    attribute_name: str
    """The name of the global attribute."""
    is_value_required: bool
    """Whether the attribute value is required."""
    source: GlobalAttributeSource
    """The source specification for the attribute value."""
    value_type: Optional[GlobalAttributeValueType] = None
    """The expected value type."""
    description: Optional[str] = None
    """Description of the attribute."""

    def __str__(self) -> str:
        return self.attribute_name


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
    global_attributes_specs: Optional[dict[str, GlobalAttributeSpec]] = None
    """The global attributes specifications of the project."""
    model_config = ConfigDict(extra="allow")
