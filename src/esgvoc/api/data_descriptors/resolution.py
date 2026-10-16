from pydantic import model_validator

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Resolution(PlainTermDataDescriptor):
    value: str | None = None
    name: str
    unit: str | None = None

    @model_validator(mode="after")
    def validate_resolution_metadata(self):
        """Require value and unit except when resolution is not applicable."""
        metadata = {
            "value": self.value,
            "unit": self.unit,
        }

        if self.id == "none":
            supplied = [name for name, value in metadata.items() if value is not None]
            if supplied:
                msg = (
                    "the 'none' resolution must not define value or unit; "
                    f"received: {', '.join(supplied)}"
                )
                raise ValueError(msg)
            return self

        missing = [name for name, value in metadata.items() if value is None]
        if missing:
            msg = (
                "resolutions other than 'none' must define value and unit; "
                f"missing: {', '.join(missing)}"
            )
            raise ValueError(msg)

        return self
