from pydantic import Field
from esgvoc.api.data_descriptors.data_descriptor import DrsPlainTermDataDescriptor


class Table(DrsPlainTermDataDescriptor):
    product: str|None
    table_date: str|None
    variable_entry: list[str] = Field(default_factory=list)