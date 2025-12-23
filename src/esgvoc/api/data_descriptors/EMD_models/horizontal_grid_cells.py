"""
Horizontal grid cells description (EMD v1.0 Section 4.1.3).

Horizontal grid cells are described by a coordinate system, cell resolutions,
as well as a number of other grid features.
"""

from __future__ import annotations

import textwrap
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from esgvoc.api.data_descriptors.region import Region

from .truncation_method import TruncationMethod


class HorizontalGridCells(BaseModel):
    """
    Horizontal grid cells description (EMD v1.0 Section 4.1.3).

    Horizontal grid cells are described by a coordinate system, cell resolutions,
    as well as a number of other grid features. The description does not include
    any information on whether or not the grid cells form part of a model component's
    computational grid, and so may be used to describe an arbitrary output grid.
    """

    region: Region | str = Field(
        description="The geographical region, or regions, over which the component is simulated. "
        "A region is a contiguous part of the Earth's surface, and may include areas for which "
        "no calculations are made (such as ocean areas for a land surface component). "
        "Taken from 7.5 region CV. E.g. 'global', 'antarctica', 'greenland', 'limited_area'"
    )

    grid_type: str = Field(
        description="The horizontal grid type, i.e. the method of distributing grid cells over the region. "
        "Taken from 7.6 grid_type CV. E.g. 'regular_latitude_longitude', 'tripolar'"
    )

    description: Optional[str] = Field(
        default=None,
        description="A description of the grid. A description is only required if there is information "
        "that is not covered by any of the other properties. Omit when not required.",
    )

    grid_mapping: str = Field(
        description="The name of the coordinate reference system of the horizontal coordinates. "
        "Taken from 7.7 grid_mapping CV. E.g. 'latitude_longitude', 'lambert_conformal_conic'"
    )

    temporal_refinement: str = Field(
        description="The grid temporal refinement, indicating how the distribution of grid cells varies with time. "
        "Taken from 7.8 temporal_refinement CV. E.g. 'static'"
    )

    spatial_refinement: Optional[str] = Field(
        default=None,
        description="The grid spatial refinement, indicating how the distribution of grid cells varies with space. "
        "NEW in EMD v1.0. Omit when not applicable.",
    )

    x_resolution: Optional[float] = Field(
        default=None,
        description=textwrap.dedent(
            """
            The size of grid cells in the X direction.

            Cells for which no calculations are made are included (such as ocean areas
            for a land surface component).

            The X direction for a grid defined by spherical polar coordinates is longitude.

            The value's physical units are given by the horizontal_units property.

            Report only when cell sizes are identical or else reasonably uniform (in their given units).
            When cells sizes in the X direction are not identical, a representative value should be
            provided and this fact noted in the description property.
            If the cell sizes vary by more than 25%, set this to None.
            """
        ),
        gt=0,
    )

    y_resolution: Optional[float] = Field(
        default=None,
        description=textwrap.dedent(
            """
            The size of grid cells in the Y direction.

            Cells for which no calculations are made are included (such as ocean areas
            for a land surface component).

            The Y direction for a grid defined by spherical polar coordinates is latitude.

            The value's physical units are given by the horizontal_units property.

            Report only when cell sizes are identical or else reasonably uniform (in their given units).
            When cells sizes in the Y direction are not identical, a representative value should be
            provided and this fact noted in the description property.
            If the cell sizes vary by more than 25%, set this to None.
            """
        ),
        gt=0,
    )

    horizontal_units: Optional[str] = Field(
        default=None,
        description=textwrap.dedent(
            """
            The physical units of the x_resolution and y_resolution property values.

            If x_resolution and y_resolution are None, set this to None.
            """
        ),
    )

    southernmost_latitude: Optional[float] = Field(
        default=None,
        description=textwrap.dedent(
            """
            The southernmost grid cell latitude, in degrees north.

            Cells for which no calculations are made are included.
            The southernmost latitude may be shared by multiple cells.

            If the southernmost latitude is not known (e.g. the grid is adaptive), use None.
            """
        ),
        ge=-90.0,
        le=90.0,
    )

    westernmost_longitude: Optional[float] = Field(
        default=None,
        description=textwrap.dedent(
            """
            The westernmost grid cell longitude, in degrees east, of the southernmost grid cell(s).

            Cells for which no calculations are made are included.
            The westernmost longitude is the smallest longitude value of the cells
            that share the latitude given by the southernmost_latitude.

            If the westernmost longitude is not known (e.g. the grid is adaptive), use None.
            """
        ),
        ge=0.0,
        le=360.0,
    )

    n_cells: Optional[int] = Field(
        default=None,
        description=textwrap.dedent(
            """
            The total number of cells in the horizontal grid.

            If the total number of grid cells is not constant, set to None.
            """
        ),
        ge=1,
    )

    truncation_method: Optional[str | TruncationMethod] = Field(
        default=None,
        description="The method for truncating the spherical harmonic representation of a spectral model "
        "when reporting on this grid. If the grid is not used for reporting spherical harmonic "
        "representations, set to None.",
    )

    truncation_number: Optional[int] = Field(
        default=None,
        description="The zonal (east-west) wave number at which a spectral model is truncated when "
        "reporting on this grid. If the grid is not used for reporting spectral models, set to None.",
    )

    resolution_range_km: Optional[list[float]] = Field(
        default=None,
        description=textwrap.dedent(
            """
            The minimum and maximum resolution (in km) of cells of the horizontal grid.

            Should be calculated according to the algorithm implemented by
            https://github.com/PCMDI/nominal_resolution/blob/master/lib/api.py
            You need to take the min and max of the array that is returned
            when using the returnMaxDistance of the mean_resolution function.
            """
        ),
        min_length=2,
        max_length=2,
    )

    @field_validator("horizontal_units", mode="after")
    @classmethod
    def validate_horizontal_units(cls, v, info):
        """Validate horizontal_units."""
        resolution_fields = {"x_resolution", "y_resolution"}
        has_resolution = any(info.data.get(field) is not None for field in resolution_fields)
        if has_resolution:
            if not v:
                raise ValueError("horizontal_units is required when x_resolution or y_resolution are set")

            allowed_values = {"km", "degree"}
            if v not in allowed_values:
                msg = f"horizontal_units must be one of {allowed_values}. Received: {v}"
                raise ValueError(msg)
        elif v:
            msg = f"If all of {resolution_fields} are None, then horizontal_units must also be None. Received: {v}"
            raise ValueError(msg)

        return v

    @field_validator("resolution_range_km")
    @classmethod
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
