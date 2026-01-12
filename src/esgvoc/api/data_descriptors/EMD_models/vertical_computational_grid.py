"""
Vertical computational grid description (EMD v1.0 Section 4.2).

The model component's vertical computational grid is described by a subset of the following properties.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field, field_validator

from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor

from .coordinate import Coordinate


class VerticalComputationalGrid(DataDescriptor):
    """
    Vertical computational grid description (EMD v1.0 Section 4.2).

    The model component's vertical computational grid is described by a subset of the following properties.
    """

    vertical_coordinate: str | Coordinate = Field(
        description="The coordinate type of the vertical grid. Taken from 7.11 vertical_coordinate CV. If there is no vertical grid, then the value 'none' must be selected."
    )
    description: Optional[str] = Field(
        default=None,
        description="A description of the vertical grid. A description is only required if there is information that is not covered by any of the other properties. Omit when not required.",
    )
    n_z: Optional[int] = Field(
        default=None,
        description="The number of layers (i.e. grid cells) in the Z direction. Omit when not applicable or not constant. If the number of layers varies in time or across the horizontal grid, then the n_z_range property may be used instead.",
        ge=1,
    )
    n_z_range: Optional[List[int]] = Field(
        default=None,
        description="The minimum and maximum number of layers for vertical grids with a time- or space-varying number of layers. Omit if the n_z property has been set.",
        min_length=2,
        max_length=2,
    )
    bottom_layer_thickness: Optional[float] = Field(
        default=None,
        description="The thickness of the bottom model layer (i.e. the layer closest to the centre of the Earth). The value should be reported as a dimensional (as opposed to parametric) quantity. All measurements are in metres (EMD v1.0).",
        gt=0,
    )
    top_layer_thickness: Optional[float] = Field(
        default=None,
        description="The thickness of the top model layer (i.e. the layer furthest away from the centre of the Earth). The value should be reported as a dimensional (as opposed to parametric) quantity. All measurements are in metres (EMD v1.0).",
        gt=0,
    )
    top_of_model: Optional[float] = Field(
        default=None,
        description="The upper boundary of the top model layer (i.e. the upper boundary of the layer that is furthest away from the centre of the Earth). The value should be relative to the lower boundary of the bottom layer of the model, or an appropriate datum (such as mean sea level). All measurements are in metres (EMD v1.0).",
    )

    @field_validator("vertical_coordinate", mode="before")
    @classmethod
    def validate_vertical_coordinate(cls, v):
        """Validate that vertical_coordinate is not empty if it's a string."""
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Vertical coordinate cannot be empty")
            return v.strip()
        return v

    @field_validator("n_z_range")
    @classmethod
    def validate_n_z_range(cls, v):
        """Validate that n_z_range has exactly 2 values and min <= max."""
        if v is not None:
            if len(v) != 2:
                raise ValueError("n_z_range must contain exactly 2 values [min, max]")
            if v[0] > v[1]:
                raise ValueError("n_z_range: minimum must be <= maximum")
            if any(val < 1 for val in v):
                raise ValueError("n_z_range values must be >= 1")
        return v

    @field_validator("n_z")
    @classmethod
    def validate_n_z_exclusivity(cls, v, info):
        """Validate that n_z and n_z_range are mutually exclusive."""
        if v is not None and info.data.get("n_z_range") is not None:
            raise ValueError("n_z and n_z_range cannot both be set")
        return v

    def accept(self, visitor):
        """Accept a data descriptor visitor."""
        return visitor.visit_plain_term(self)
