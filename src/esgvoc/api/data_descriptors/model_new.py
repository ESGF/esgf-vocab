from typing import List, Optional
from pydantic import Field, field_validator
from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor, PlainTermDataDescriptor
from esgvoc.api.data_descriptors.reference_new import Reference
from esgvoc.api.data_descriptors.model_component_new import EMDModelComponent


class Model(PlainTermDataDescriptor):
    """
    The following properties provide a top-level description of the model as whole.
    In the property examples, underlined and italicised values are taken from section 7. Controlled vocabularies.
    """

    name: str = Field(
        description="The name of the top-level model. For CMIP7, this name will be registered as the model's source_id.",
        min_length=1,
    )
    family: str = Field(
        description="The top-level model's 'family' name. Use 'none' to indicate that there is no such family.",
        min_length=1,
    )
    dynamic_components: List[str] = Field(
        description="The model components that are dynamically simulated within the top-level model. Taken from a standardised list: 7.1 component CV.",
        min_length=1,
    )
    prescribed_components: List[str] = Field(
        description="The components that are represented in the top-level model with prescribed values. Taken from a standardised list: 7.1 component CV.",
        default_factory=list,
    )
    omitted_components: List[str] = Field(
        description="The components that are wholly omitted from the top-level model. Taken from a standardised list: 7.1 component CV.",
        default_factory=list,
    )
    description: str = Field(description="A brief, free-text scientific overview of the top-level model.", min_length=1)
    calendar: List[str] = Field(
        description="The calendar, or calendars, that define which dates are permitted in the top-level model. Taken from a standardised list: 7.2 calendar CV.",
        min_length=1,
    )
    release_year: int = Field(
        description="The year in which the top-level model being documented was released, or first used for published simulations.",
        ge=1900,
        le=2100,
    )
    references: List[Reference] = Field(
        description="One or more references to published work for the top-level model as a whole.", min_length=1
    )
    model_components: Optional[List[EMDModelComponent]] = Field(
        default=None, description="The model components that dynamically simulate processes within the model."
    )

    @field_validator("name", "family", "description")
    @classmethod
    def validate_non_empty_strings(cls, v):
        """Validate that string fields are not empty."""
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("dynamic_components", "prescribed_components", "omitted_components")
    @classmethod
    def validate_component_lists(cls, v):
        """Validate component lists contain valid strings."""
        if v is None:
            return []
        cleaned = [item.strip() for item in v if item.strip()]
        return cleaned

    @field_validator("calendar")
    @classmethod
    def validate_calendar_list(cls, v):
        """Validate calendar list contains valid strings."""
        if not v:
            raise ValueError("At least one calendar must be specified")
        cleaned = [item.strip() for item in v if item.strip()]
        if not cleaned:
            raise ValueError("Calendar list cannot be empty")
        return cleaned
