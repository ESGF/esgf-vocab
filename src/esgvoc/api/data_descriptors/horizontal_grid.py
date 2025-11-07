from typing import Optional, List, Any
from pydantic import Field, validator
from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor, DataDescriptorVisitor


class HorizontalGrid(DataDescriptor):
    """
    Standalone horizontal grid CV term that can be referenced by model components.
    This represents a reusable grid definition that can be shared across multiple models.
    """

    grid: str = Field(
        description="The horizontal grid type, i.e. the method of distributing grid points over the sphere. If there is no horizontal grid, then the value 'none' must be selected."
    )
    description: Optional[str] = Field(
        default=None,
        description="A free-text description of the grid.",
    )
    grid_mapping: Optional[str] = Field(
        default=None, description="The name of the coordinate reference system of the horizontal coordinates."
    )
    region: Optional[str] = Field(default=None, description="The geographical region over which the grid is defined.")
    temporal_refinement: Optional[str] = Field(
        default=None,
        description="The grid temporal refinement, indicating how the distribution of grid cells varies with time.",
    )
    arrangement: Optional[str] = Field(
        default=None,
        description="A characterisation of the relative positions on a grid of mass-, velocity- or flux-related fields.",
    )
    resolution_x: Optional[float] = Field(
        default=None,
        description="The size of grid cells in the X direction.",
        gt=0,
    )
    resolution_y: Optional[float] = Field(
        default=None,
        description="The size of grid cells in the Y direction.",
        gt=0,
    )
    horizontal_units: Optional[str] = Field(
        default=None,
        description="The physical units of the resolution_x and resolution_y property values.",
    )
    n_cells: Optional[int] = Field(default=None, description="The total number of cells in the horizontal grid.", ge=1)
    n_sides: Optional[int] = Field(
        default=None, description="For unstructured horizontal grids only, the total number of unique cell sides.", ge=1
    )
    n_vertices: Optional[int] = Field(
        default=None, description="For unstructured horizontal grids only, the number of unique cell vertices.", ge=1
    )
    truncation_method: Optional[str] = Field(
        default=None,
        description="The method for truncating the spherical harmonic representation of a spectral model.",
    )
    truncation_number: Optional[int] = Field(
        default=None, description="The zonal (east-west) wave number at which a spectral model is truncated.", ge=1
    )
    resolution_range_km: Optional[List[float]] = Field(
        default=None,
        description="The minimum and maximum resolution (in km) of cells of the horizontal grid.",
        min_items=2,
        max_items=2,
    )
    mean_resolution_km: Optional[float] = Field(
        default=None, description="The mean resolution (in km) of cells of the horizontal grid.", gt=0
    )
    nominal_resolution: Optional[str] = Field(
        default=None,
        description="The nominal resolution characterises the approximate resolution of a horizontal grid.",
    )

    @validator("grid")
    def validate_grid(cls, v):
        """Validate that grid is not empty."""
        if not v.strip():
            raise ValueError("grid cannot be empty")
        return v.strip()

    @validator("horizontal_units")
    def validate_units_requirement(cls, v, values):
        """Validate that horizontal_units is provided when resolution values are set."""
        has_resolution = any(values.get(field) is not None for field in ["resolution_x", "resolution_y"])
        if has_resolution and not v:
            raise ValueError("horizontal_units is required when resolution_x or resolution_y are set")
        return v

    @validator("resolution_range_km")
    def validate_resolution_range(cls, v):
        """Validate that resolution range has exactly 2 values and min <= max."""
        if v is not None:
            if len(v) != 2:
                raise ValueError("resolution_range_km must contain exactly 2 values [min, max]")
            if v[0] > v[1]:
                raise ValueError("resolution_range_km: minimum must be <= maximum")
            if any(val <= 0 for val in v):
                raise ValueError("resolution_range_km values must be > 0")
        return v

    @validator("mean_resolution_km")
    def validate_mean_resolution_in_range(cls, v, values):
        """Validate that mean resolution is within the resolution range."""
        if v is not None and "resolution_range_km" in values and values["resolution_range_km"]:
            range_km = values["resolution_range_km"]
            if not (range_km[0] <= v <= range_km[1]):
                raise ValueError(
                    f"mean_resolution_km ({v}) must be between resolution_range_km min ({range_km[0]}) and max ({
                        range_km[1]
                    })"
                )
        return v

    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        """Accept a data descriptor visitor."""
        return visitor.visit_plain_term(self)
