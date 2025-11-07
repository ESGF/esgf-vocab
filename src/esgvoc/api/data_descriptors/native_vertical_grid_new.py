from typing import Any, Optional, List
from pydantic import Field, field_validator

from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor, DataDescriptorVisitor


class NativeVerticalGrid(DataDescriptor):
    """
    4.2. Vertical grid
    The model component's native vertical grid is described by a subset of the following properties:
        • Description
            ◦ A free-text description of the vertical grid.
            ◦ A description is only required if there is information that is not covered by any of the other properties.
            ◦ Omit if not needed.
        • Coordinate
            ◦ The coordinate type of the vertical grid.
            ◦ Taken from a standardised list: 7.11. coordinate CV.
            ◦ If there is no vertical grid, then the value "none" must be selected, and no other properties should be set.
            ◦ E.g. height
            ◦ E.g. none
        • N z
            ◦ The number of layers (i.e. grid cells) in the Z direction.
            ◦ Omit when not applicable or not constant.
            ◦ If the number of layers varies in time or across the horizontal grid, then the N z range property may be used instead.
            ◦ E.g. 70
        • N z range
            ◦ The minimum and maximum number of layers for vertical grids with a time- or space-varying number of layers.
            ◦ Omit if the N z property has been set.
            ◦ E.g. 5, 15
        • Bottom layer thickness
            ◦ The thickness of the bottom model layer (i.e. the layer closest to the centre of the Earth).
            ◦ The value should be reported as a dimensional (as opposed to parametric) quantity.
            ◦ If the value varies in time or across the horizontal grid, then provide a nominal or typical value.
            ◦ The value's physical units are given by the vertical_units property.
            ◦ Omit when not applicable.
            ◦ E.g. 10
        • Top layer thickness
            ◦ The thickness of the top model layer (i.e. the layer furthest away from the centre of the Earth).
            ◦ The value should be reported as a dimensional (as opposed to parametric) quantity.
            ◦ If the value varies in time or across the horizontal grid, then provide a nominal or typical value.
            ◦ The value's physical units are given by the vertical_units property.
            ◦ Omit when not applicable.
            ◦ E.g. 10
        • Top of model
            ◦ The upper boundary of the top model layer (i.e. the upper boundary of the layer that is furthest away from the centre of the Earth).
            ◦ The value should be relative to the lower boundary of the bottom layer of the model, or an appropriate datum (such as mean sea level).
            ◦ The value should be reported as a dimensional (as opposed to parametric) quantity.
            ◦ The value's physical units are given by the vertical_units property.
            ◦ Omit when not applicable or not constant.
            ◦ E.g. 85003.5
        • Vertical units
            ◦ The physical units of the bottom_layer_thickness, top_layer_thickness, and top_of_model property values.
            ◦ Taken from a standardised list: 7.12. vertical_units CV.
            ◦ Omit when not applicable.
            ◦ E.g. m
    """

    coordinate: str = Field(
        description="The coordinate type of the vertical grid. Taken from a standardised list: 7.11 coordinate CV. If there is no vertical grid, then the value 'none' must be selected."
    )
    description: Optional[str] = Field(
        default=None,
        description="A free-text description of the vertical grid. A description is only required if there is information that is not covered by any of the other properties.",
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
        description="The thickness of the bottom model layer (i.e. the layer closest to the centre of the Earth). The value should be reported as a dimensional (as opposed to parametric) quantity. The value's physical units are given by the vertical_units property.",
        gt=0,
    )
    top_layer_thickness: Optional[float] = Field(
        default=None,
        description="The thickness of the top model layer (i.e. the layer furthest away from the centre of the Earth). The value should be reported as a dimensional (as opposed to parametric) quantity. The value's physical units are given by the vertical_units property.",
        gt=0,
    )
    top_of_model: Optional[float] = Field(
        default=None,
        description="The upper boundary of the top model layer (i.e. the upper boundary of the layer that is furthest away from the centre of the Earth). The value should be relative to the lower boundary of the bottom layer of the model, or an appropriate datum (such as mean sea level). The value's physical units are given by the vertical_units property.",
    )
    vertical_units: Optional[str] = Field(
        default=None,
        description="The physical units of the bottom_layer_thickness, top_layer_thickness, and top_of_model property values. Taken from a standardised list: 7.12 vertical_units CV.",
    )

    @field_validator("coordinate")
    @classmethod
    def validate_coordinate(cls, v):
        """Validate that coordinate is not empty."""
        if not v.strip():
            raise ValueError("Coordinate cannot be empty")
        return v.strip()

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

    @field_validator("vertical_units")
    @classmethod
    def validate_units_requirement(cls, v, info):
        """Validate that vertical_units is provided when thickness/top_of_model values are set."""
        thickness_fields = ["bottom_layer_thickness", "top_layer_thickness", "top_of_model"]
        has_thickness_values = any(info.data.get(field) is not None for field in thickness_fields)

        if has_thickness_values and not v:
            raise ValueError(
                "vertical_units is required when bottom_layer_thickness, top_layer_thickness, or top_of_model are set"
            )
        return v

    @field_validator("n_z")
    @classmethod
    def validate_n_z_exclusivity(cls, v, info):
        """Validate that n_z and n_z_range are mutually exclusive."""
        if v is not None and info.data.get("n_z_range") is not None:
            raise ValueError("n_z and n_z_range cannot both be set")
        return v

    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        """Accept a data descriptor visitor."""
        return visitor.visit_plain_term(self)
