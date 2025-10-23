from typing import Optional, List
from pydantic import Field, field_validator

from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor, PlainTermDataDescriptor


class NativeHorizontalGrid(PlainTermDataDescriptor):
    """
    The model component’s native horizontal grid is described by a subset of the following properties:

    • Grid label
        ◦ A free-text identifier that is intended to characterize all of the other grid properties.
        ◦ The identifier may be used for any purpose, but note that the EMD does not guarantee that grids with the same grid_label are identical, nor that grids with different labels are different.
        ◦ For CMIP7, however, it will be the case that grids with the same grid_label may be assumed to be identical, and grids with different labels may be assumed to be different.
        ◦ Omit when not required.
    • Description
        ◦ A free-text description of the grid.
        ◦ A description is only required if there is information that is not covered by any of the other properties.
        ◦ Omit if not needed.
    • Type
        ◦ The horizontal grid type, i.e. the method of distributing grid points over the sphere.
        ◦ Taken from a standardised list: 7.3. Native horizontal grid Type CV.
        ◦ If there is no horizontal grid, then the value "none" must be selected, and no other properties should be set.
        ◦ E.g. regular_latitude_longitude
        ◦ E.g. tripolar
    • Grid mapping
        ◦ The name of the coordinate reference system of the horizontal coordinates.
        ◦ Taken from a standardised list: 7.4. Native horizontal grid Grid Mapping CV.
        ◦ E.g. latitude_longitude
    • Region
        ◦ The geographical region, or regions, over which the component is simulated.
        ◦ A region is a contiguous part of the Earth's surface, and may include areas for which no calculations are made (such as ocean areas for a land surface component).
        ◦ Taken from a standardised list: 7.5. Native horizontal grid Region CV.
        ◦ E.g. global
        ◦ E.g. antarctica, greenland
    • Temporal refinement
        ◦ The grid temporal refinement, indicating how the distribution of grid cells varies with time.
        ◦ Taken from a standardised list: 7.6. Native horizontal grid Temporal refinement CV.
        ◦ E.g. static
    • Arrangement
        ◦ A characterisation of the relative positions on a grid of mass-, velocity- or flux-related fields.
        ◦ Taken from a standardised list: 7.7. Native horizontal grid Arrangement CV.
        ◦ E.g. arakawa_B
    • Cell variable type
        ◦ The type, or types, of physical variables that are carried on the cells described by the horizontal grid.
        ◦ The grid arrangement may define different cells for different types of physical variables, but only the cells that carry the specified physical variable types are described here.
        ◦ Taken from a standardised list: 7.8 cell_variable_type CV.
        ◦ Omit when not applicable.
        ◦ E.g. mass
        ◦ E.g. velocity_x
        ◦ E.g. mass, velocity_x, velocity_y
    • Mesh location
        ◦ The mesh location of cells on an unstructured grid.
        ◦ Taken from a standardised list: 7.9 mesh_location CV.
        ◦ Omit when not applicable.
        ◦ E.g. face
    • Resolution X
        ◦ The size of grid cells in the X direction.
        ◦ The value’s physical units are given by the Units property.
        ◦ Report only when cell sizes are identical or else reasonably uniform (in their given units). When cells sizes are not identical, a representative value should be provided and this fact noted in the Description property, but only if the cell sizes vary by less than 25%.
        ◦ Omit when not applicable.
        ◦ E.g. 3.75
    • Resolution Y
        ◦ The size of grid cells in the Y direction.
        ◦ The value’s physical units are given by the Units property.
        ◦ Report only when cell sizes are identical or else reasonably uniform (in their given units). When cells sizes are not identical, a representative value should be provided and this fact noted in the Description property, but only if the cell sizes vary by less than 25%.
        ◦ Omit when not applicable.
        ◦ E.g. 2.5
    • Units
        ◦ The physical units of the Resolution X and Resolution Y property values.
        ◦ The only acceptable units are  "km" (kilometre, unit for length) or "degree" (unit for angular measure).
        ◦ Omit when not applicable.
        ◦ E.g. km
        ◦ E.g. degree
    • Southernmost latitude
        ◦ The southernmost grid cell latitude, in degrees north.
        ◦ Must be greater than or equal to -90 and less than or equal to 90.
        ◦ Cells for which no calculations are made are included.
        ◦ The southernmost latitude may be shared by multiple cells.
        ◦ Omit when not applicable.
        ◦ E.g. -89.5
    • Westernmost longitude
        ◦ The westernmost longitude, in degrees east, of the southernmost grid cells.
        ◦ Must be greater than or equal to 0 and strictly less than 360.
        ◦ Cells for which no calculations are made are included.
        ◦ The westernmost longitude is the smallest longitude value of the cells that share the latitude given by the southernmost_latitude property.
        ◦ Omit when not applicable.
        ◦ E.g. 0.5
    • N cells
        ◦ The total number of cells in the horizontal grid.
        ◦ If the horizontal grid is unstructured and utilises primal and dual meshes (i.e. when each vertex of a primal mesh cell is uniquely associated with the centre of a dual mesh cell, and vice versa), then the number of cells for the primal mesh should be provided.
        ◦ Omit when not applicable or not constant.
        ◦ E.g. 265160
    • Truncation method
        ◦ The method for truncating the spherical harmonic representation of a spectral model.
        ◦ Taken from a standardised list: 7.11 truncation_method CV.
        ◦ Omit when not applicable.
        ◦ E.g. triangular
    • Truncation number
        ◦ The zonal (east-west) wave number at which a spectral model is truncated.
        ◦ Omit when not applicable.
        ◦ E.g. 63
    • Resolution range km
        ◦ The minimum and maximum resolution (in km) of cells of the native horizontal grid.
        ◦ Calculate as described in this documented Python code, which can be used to obtain the maximum, minimum and mean resolution.
        ◦ E.g. 57.0, 290
    • Mean resolution km
        ◦ The mean resolution (in km) of the native horizontal grid on which the mass-related quantities are carried by the model.
        ◦ Calculate as described in this documented Python code, which can be used to obtain the maximum, minimum, and mean resolution.
        ◦ E.g. 234.8
    • Nominal resolution
        ◦ The nominal resolution characterises the approximate resolution of a model's native horizontal grid.
        ◦ The nominal resolution is obtained (once the Mean resolution km property is calculated) by looking it up in the table at 7.12 nominal_resolution CV.
        ◦ E.g. A grid with mean resolution of 82 will have a nominal resolution of 100 km
    """

    grid_label: Optional[str] = Field(
        default=None,
        description="A free-text identifier that is intended to characterize all of the other grid properties. For CMIP7, grids with the same grid_label may be assumed to be identical. Omit when not required."
    )
    grid: str = Field(
        description="The horizontal grid type, i.e. the method of distributing grid points over the sphere. Taken from a standardised list: 7.3 grid CV. If there is no horizontal grid, then the value 'none' must be selected."
    )
    grid_mapping: str = Field(
        description="The name of the coordinate reference system of the horizontal coordinates. Taken from a standardised list: 7.4 grid_mapping CV."
    )
    region: str = Field(
        description="The geographical region, or regions, over which the component is simulated. Taken from a standardised list: 7.5 region CV."
    )
    temporal_refinement: str = Field(
        description="The grid temporal refinement, indicating how the distribution of grid cells varies with time. Taken from a standardised list: 7.6 temporal_refinement CV."
    )
    arrangement: str = Field(
        description="A characterisation of the relative positions on a grid of mass-, velocity- or flux-related fields. Taken from a standardised list: 7.7 arrangement CV."
    )
    cell_variable_type: Optional[List[str]] = Field(
        default=None,
        description="The type, or types, of physical variables that are carried on the cells described by the horizontal grid. Taken from a standardised list: 7.8 cell_variable_type CV. Omit when not applicable."
    )
    mesh_location: Optional[str] = Field(
        default=None,
        description="The mesh location of cells on an unstructured grid. Taken from a standardised list: 7.9 mesh_location CV. Omit when not applicable."
    )
    resolution_x: Optional[float] = Field(
        default=None,
        description="The size of grid cells in the X direction. The value's physical units are given by the horizontal_units property. Report only when cell sizes are identical or else reasonably uniform.",
        gt=0,
    )
    resolution_y: Optional[float] = Field(
        default=None,
        description="The size of grid cells in the Y direction. The value's physical units are given by the horizontal_units property. Report only when cell sizes are identical or else reasonably uniform.",
        gt=0,
    )
    horizontal_units: Optional[str] = Field(
        default=None,
        description="The physical units of the resolution_x and resolution_y property values. Taken from a standardised list: 7.10 horizontal_units CV.",
    )
    southernmost_latitude: Optional[float] = Field(
        default=None,
        description="The southernmost grid cell latitude, in degrees north. Must be >= -90 and <= 90. Cells for which no calculations are made are included. Omit when not applicable.",
        ge=-90,
        le=90,
    )
    westernmost_longitude: Optional[float] = Field(
        default=None,
        description="The westernmost longitude, in degrees east, of the southernmost grid cells. Must be >= 0 and < 360. Omit when not applicable.",
        ge=0,
        lt=360,
    )
    n_cells: int = Field(
        description="The total number of cells in the horizontal grid.", ge=1)
    truncation_method: Optional[str] = Field(
        default=None,
        description="The method for truncating the spherical harmonic representation of a spectral model. Taken from a standardised list: 7.11 truncation_method CV.",
    )
    truncation_number: Optional[int] = Field(
        default=None, description="The zonal (east-west) wave number at which a spectral model is truncated.", ge=1
    )
    resolution_range_km: List[float] = Field(
        description="The minimum and maximum resolution (in km) of cells of the horizontal grid.",
        min_length=2,
        max_length=2,
    )
    mean_resolution_km: float = Field(
        description="The mean resolution (in km) of cells of the horizontal grid.", gt=0)
    nominal_resolution: str = Field(
        description="The nominal resolution characterises the approximate resolution of a horizontal grid. Taken from a standardised list: 7.12 nominal_resolution CV."
    )

    @field_validator("grid", "grid_mapping", "region", "temporal_refinement", "arrangement", "nominal_resolution")
    @classmethod
    def validate_required_strings(cls, v):
        """Validate that required string fields are not empty."""
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("horizontal_units")
    @classmethod
    def validate_units_requirement(cls, v, info):
        """Validate that horizontal_units is provided when resolution values are set."""
        has_resolution = any(info.data.get(field) is not None for field in [
                             "resolution_x", "resolution_y"])

        if has_resolution and not v:
            raise ValueError(
                "horizontal_units is required when resolution_x or resolution_y are set")
        return v

    @field_validator("resolution_range_km")
    @classmethod
    def validate_resolution_range(cls, v):
        """Validate that resolution range has exactly 2 values and min <= max."""
        if len(v) != 2:
            raise ValueError(
                "resolution_range_km must contain exactly 2 values [min, max]")
        if v[0] > v[1]:
            raise ValueError("resolution_range_km: minimum must be <= maximum")
        if any(val <= 0 for val in v):
            raise ValueError("resolution_range_km values must be > 0")
        return v

    @field_validator("mean_resolution_km")
    @classmethod
    def validate_mean_resolution_in_range(cls, v, info):
        """Validate that mean resolution is within the resolution range."""
        if "resolution_range_km" in info.data and info.data["resolution_range_km"]:
            range_km = info.data["resolution_range_km"]
            if not (range_km[0] <= v <= range_km[1]):
                raise ValueError(
                    f"mean_resolution_km ({v}) must be between resolution_range_km min ({
                        range_km[0]}) and max ({range_km[1]})"
                )
        return v
