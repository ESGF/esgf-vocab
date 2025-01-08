from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class DrsType(str, Enum):
    directory = "directory"
    filename = "filename"
    dataset_id = "dataset_id"


class DrsPartType(str, Enum):
    constant = "constant"
    collection = "collection"


class DrsConstant(BaseModel):
    value: str
    kind: Literal[DrsPartType.constant] = DrsPartType.constant


class DrsCollection(BaseModel):
    collection_id: str
    is_required: bool
    kind: Literal[DrsPartType.collection] = DrsPartType.collection


DrsPart = Annotated[DrsConstant | DrsCollection, Field(discriminator="kind")]


class DrsSpecification(BaseModel):
    type: DrsType
    separator: str
    properties: dict|None = None
    parts: list[DrsPart]


class ProjectSpecs(BaseModel):
    project_id: str
    description: str
    drs_specs: list[DrsSpecification]
    model_config = ConfigDict(extra = "allow")