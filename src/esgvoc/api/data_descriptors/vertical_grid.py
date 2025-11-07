from typing import Optional, List, Any
from pydantic import Field, validator
from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor, DataDescriptorVisitor


class VerticalGrid(DataDescriptor):
    """
    Standalone vertical grid CV term that can be referenced by model components.
    This represents a reusable vertical grid definition that can be shared across multiple models.
    """

    coordinate: str = Field(
        description="The coordinate type of the vertical grid. If there is no vertical grid, then the value 'none' must be selected."
    )
    description: Optional[str] = Field(
        default=None,
        description="A free-text description of the vertical grid.",
    )
    n_z: Optional[int] = Field(
        default=None,
        description="The number of layers (i.e. grid cells) in the Z direction.",
        ge=1,
    )
    n_z_range: Optional[List[int]] = Field(
        default=None,
        description="The minimum and maximum number of layers for vertical grids with a time- or space-varying number of layers.",
        min_items=2,
        max_items=2,
    )
    bottom_layer_thickness: Optional[float] = Field(
        default=None,
        description="The thickness of the bottom model layer.",
        gt=0,
    )
    top_layer_thickness: Optional[float] = Field(
        default=None,
        description="The thickness of the top model layer.",
        gt=0,
    )
    top_of_model: Optional[float] = Field(
        default=None,
        description="The upper boundary of the top model layer.",
    )
    vertical_units: Optional[str] = Field(
        default=None,
        description="The physical units of the bottom_layer_thickness, top_layer_thickness, and top_of_model property values.",
    )

    @validator("coordinate")
    def validate_coordinate(cls, v):
        """Validate that coordinate is not empty."""
        if not v.strip():
            raise ValueError("coordinate cannot be empty")
        return v.strip()

    @validator("n_z_range")
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

    @validator("vertical_units")
    def validate_units_requirement(cls, v, values):
        """Validate that vertical_units is provided when thickness/top_of_model values are set."""
        thickness_fields = ["bottom_layer_thickness", "top_layer_thickness", "top_of_model"]
        has_thickness_values = any(values.get(field) is not None for field in thickness_fields)
        if has_thickness_values and not v:
            raise ValueError(
                "vertical_units is required when bottom_layer_thickness, top_layer_thickness, or top_of_model are set"
            )
        return v

    @validator("n_z")
    def validate_n_z_exclusivity(cls, v, values):
        """Validate that n_z and n_z_range are mutually exclusive."""
        if v is not None and values.get("n_z_range") is not None:
            raise ValueError("n_z and n_z_range cannot both be set")
        return v

    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        """Accept a data descriptor visitor."""
        return visitor.visit_plain_term(self)
