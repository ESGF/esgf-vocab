


from __future__ import annotations 
from pydantic.version import VERSION  as PYDANTIC_VERSION 
if int(PYDANTIC_VERSION[0])>=2:
    from pydantic import (
        BaseModel,
        ConfigDict
    )
else:
    from pydantic import (
        BaseModel
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





class ModelComponent(ConfiguredBaseModel):



    id: str 
    description :str
    name : str 
    type : str
    realm : dict
    nominal_resolution : dict
# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
ModelComponent.model_rebuild()
