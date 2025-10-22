from pydantic import Field, field_validator

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Table(PlainTermDataDescriptor):
    product: str | None
    table_date: str | None
    variable_entry: list[str] = Field(default_factory=list)

    @field_validator("variable_entry", mode="before")
    @classmethod
    def normalize_variable_entry(cls, v):
        """
        Normalize variable_entry to ensure all items are strings.
        If items are dicts (resolved references), extract the 'id' field.
        """
        if not isinstance(v, list):
            return v

        result = []
        for item in v:
            if isinstance(item, dict):
                # Extract the id from the resolved object
                result.append(item.get("id", str(item)))
            else:
                result.append(item)
        return result
