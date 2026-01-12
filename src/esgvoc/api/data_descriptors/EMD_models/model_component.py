"""
Model component description (EMD v1.0 Section 3).

Properties that provide a description of individual model components.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field, field_validator

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor

from .component_type import ComponentType
from .horizontal_computational_grid import HorizontalComputationalGrid
from .reference import Reference
from .vertical_computational_grid import VerticalComputationalGrid


class EMDModelComponent(PlainTermDataDescriptor):
    """
    Model component description (EMD v1.0 Section 3).

    Properties that provide a description of individual model components.

    Eight model components are defined that somewhat independently account for different
    sets of interactive processes: aerosol, atmosphere, atmospheric chemistry, land surface,
    land ice, ocean, ocean biogeochemistry, and sea ice.
    """

    component: str | ComponentType = Field(description="The type of the model component. Taken from 7.1 component CV.")

    name: str = Field(description="The name of the model component.", min_length=1)

    family: str = Field(
        description="The model component's 'family' name. Use 'none' to indicate that there is no such family.",
        min_length=1,
    )

    description: str = Field(
        description="A scientific overview of the model component. The description should summarise the key "
        "processes simulated by the model component.",
        min_length=1,
    )

    references: List[str | Reference] = Field(
        description="One or more references to published work for the model component.", min_length=1
    )

    code_base: str = Field(
        description="A URL (preferably for a DOI) for the source code for the model component. "
        "Set to 'private' if not publicly available.",
        min_length=1,
    )

    embedded_in: Optional[str | ComponentType] = Field(
        default=None,
        description="The host model component (identified by its component property) in which this component "
        "is 'embedded'. Taken from 7.1 component CV. Omit when this component is coupled with other components.",
    )

    coupled_with: Optional[List[str | ComponentType]] = Field(
        default=None,
        description="The model components (identified by their component properties) with which this component "
        "is 'coupled'. Taken from 7.1 component CV. Omit when this component is embedded in another component.",
    )

    horizontal_computational_grid: HorizontalComputationalGrid = Field(
        description="A standardised description of the model component's horizontal computational grid."
    )

    vertical_computational_grid: VerticalComputationalGrid = Field(
        description="A standardised description of the model component's vertical computational grid."
    )

    @field_validator("component", "name", "family", "code_base", "description", mode="before")
    @classmethod
    def validate_non_empty_strings(cls, v):
        """Validate that string fields are not empty."""
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Field cannot be empty")
            return v.strip()
        return v

    @field_validator("coupled_with")
    @classmethod
    def validate_coupling_exclusivity(cls, v, info):
        """Validate that a component cannot be both embedded and coupled."""
        if v is not None and info.data.get("embedded_in") is not None:
            raise ValueError(
                "A component cannot be both embedded_in another component and coupled_with other components"
            )
        return v

    @field_validator("embedded_in")
    @classmethod
    def validate_embedding_exclusivity(cls, v, info):
        """Validate that a component cannot be both embedded and coupled."""
        if v is not None and info.data.get("coupled_with") is not None:
            raise ValueError(
                "A component cannot be both embedded_in another component and coupled_with other components"
            )
        return v

    @field_validator("code_base", mode="before")
    @classmethod
    def validate_code_base_format(cls, v):
        """Validate code_base is either 'private' or a URL."""
        if isinstance(v, str):
            v = v.strip()
            if v.lower() != "private" and not (v.startswith("http://") or v.startswith("https://")):
                raise ValueError('code_base must be either "private" or a valid URL starting with http:// or https://')
        return v
