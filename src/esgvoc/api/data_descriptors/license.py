

from __future__ import annotations 
from typing import (
    Optional
)
from pydantic.version import VERSION  as PYDANTIC_VERSION 
if int(PYDANTIC_VERSION[0])>=2:
    from pydantic import (
        BaseModel,
        ConfigDict,
        Field
    )
else:
    from pydantic import (
        BaseModel,
        Field
    )

metamodel_version = "None"
version = "None"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        validate_assignment = True,
        validate_default = True,
        extra = "allow",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )
    pass



class License(ConfiguredBaseModel):

    id: str 
    validation_method: str = Field(default = "list")
    kind: str 
    license: Optional[str] 
    url: Optional[str] 

# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
License.model_rebuild()
