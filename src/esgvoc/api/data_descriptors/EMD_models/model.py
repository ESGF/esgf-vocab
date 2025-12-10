"""
Top-level model description (EMD v1.0 Section 2).

The following properties provide a top-level description of the model as a whole.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field, field_validator

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor

from .calendar import Calendar
from .component_type import ComponentType
from .model_component import EMDModelComponent
from .reference import Reference


class Model(PlainTermDataDescriptor):
    """
    Top-level model description (EMD v1.0 Section 2).

    The following properties provide a top-level description of the model as a whole.
    """

    name: str = Field(
        description="The name of the top-level model. For CMIP7, this name will be registered as the model's source_id.",
        min_length=1,
    )

    family: str = Field(
        description="The top-level model's 'family' name. Use 'none' to indicate that there is no such family.",
        min_length=1,
    )

    dynamic_components: List[str | ComponentType] = Field(
        description="The model components that are dynamically simulated within the top-level model. "
        "Taken from 7.1 component CV.",
        min_length=1,
    )

    prescribed_components: List[str | ComponentType] = Field(
        description="The components that are represented in the top-level model with prescribed values. "
        "Taken from 7.1 component CV.",
        default_factory=list,
    )

    omitted_components: List[str | ComponentType] = Field(
        description="The components that are wholly omitted from the top-level model. " "Taken from 7.1 component CV.",
        default_factory=list,
    )

    description: str = Field(
        description="A scientific overview of the top-level model. The description should include a brief mention "
        "of all the components listed in the 7.1 component CV, whether dynamically simulated, prescribed, or omitted.",
        min_length=1,
    )

    calendar: List[str | Calendar] = Field(
        description="The calendar, or calendars, that define which dates are permitted in the top-level model. "
        "Taken from 7.2 calendar CV.",
        min_length=1,
    )

    release_year: int = Field(
        description="The year in which the top-level model being documented was released, "
        "or first used for published simulations.",
        ge=1900,
        le=2100,
    )

    references: List[Reference] = Field(
        description="One or more references to published work for the top-level model as a whole.", min_length=1
    )

    model_components: Optional[List[EMDModelComponent]] = Field(
        default=None, description="The model components that dynamically simulate processes within the model."
    )

    @field_validator("name", "family", "description", mode="before")
    @classmethod
    def validate_non_empty_strings(cls, v):
        """Validate that string fields are not empty."""
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Field cannot be empty")
            return v.strip()
        return v

    @field_validator("dynamic_components", "prescribed_components", "omitted_components", mode="before")
    @classmethod
    def validate_component_lists(cls, v):
        """Validate component lists contain valid strings or ComponentType objects."""
        if v is None:
            return []
        # Filter out empty strings, keep ComponentType objects
        cleaned = []
        for item in v:
            if isinstance(item, str):
                if item.strip():
                    cleaned.append(item.strip())
            else:
                cleaned.append(item)
        return cleaned

    @field_validator("calendar", mode="before")
    @classmethod
    def validate_calendar_list(cls, v):
        """Validate calendar list contains valid strings or Calendar objects."""
        if not v:
            raise ValueError("At least one calendar must be specified")
        # Filter out empty strings, keep Calendar objects
        cleaned = []
        for item in v:
            if isinstance(item, str):
                if item.strip():
                    cleaned.append(item.strip())
            else:
                cleaned.append(item)
        if not cleaned:
            raise ValueError("Calendar list cannot be empty")
        return cleaned
