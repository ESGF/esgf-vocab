from pydantic import BaseModel, ConfigDict

class DataDescriptor(BaseModel):
    """
    Generic class for the data descriptor classes.
    """
    id: str
    """The identifier of the terms"""
    type: str
    """The data descriptor to which the term belongs."""
    model_config = ConfigDict(
        validate_assignment = True,
        validate_default = True,
        extra = "allow",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )