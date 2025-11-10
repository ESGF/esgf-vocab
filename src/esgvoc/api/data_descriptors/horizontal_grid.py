"""
Model (i.e. schema/definition) of the horizontal grid data descriptor
"""

import re
import textwrap

from pydantic import Field, validator

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
from esgvoc.api.data_descriptors.horizontal_grid_arrangement import HorizontalGridArrangement
from esgvoc.api.data_descriptors.horizontal_grid_cell_variable_type import HorizontalGridCellVariableType
from esgvoc.api.data_descriptors.horizontal_grid_mapping import HorizontalGridMapping
from esgvoc.api.data_descriptors.horizontal_grid_region import HorizontalGridRegion
from esgvoc.api.data_descriptors.horizontal_grid_temporal_refinement import HorizontalGridTemporalRefinement
from esgvoc.api.data_descriptors.horizontal_grid_truncation_method import HorizontalGridTruncationMethod
from esgvoc.api.data_descriptors.horizontal_grid_type import HorizontalGridType
from esgvoc.api.data_descriptors.nominal_resolution import NominalResolution


class HorizontalGrid(PlainTermDataDescriptor):
    """
    Horizontal grid

    Examples: [TODO: discuss what these should be.
    They shouldn't be the same as :py:class:`Grid`
    because :py:class:`Grid` and :py:class:`Region`
    aren't linked, whereas EMD has to enforce that link.]

    Horizontal grids with the same id
    are identical (details on how we check identical are to come, for discussion,
    see https://github.com/WCRP-CMIP/CMIP7-CVs/issues/202)
    and can be used by more than one model or model component.
    Horizontal grids with different labels are different.
    """

    # Note: Allowing str is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    grid: HorizontalGridType | str
    """
    Horizontal grid type
    """

    # Note: Allowing str is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    grid_mapping: HorizontalGridMapping | str
    """
    Horizontal grid mapping
    """

    # Note: Allowing str is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    region: HorizontalGridRegion | str
    """
    Horizontal grid region
    """

    # Note: Allowing str is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    temporal_refinement: HorizontalGridTemporalRefinement | str
    """
    Temporal refinement
    """

    # Note: Allowing str is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    arrangement: HorizontalGridArrangement | str
    """
    Grid arrangement
    """

    # Note: Allowing str is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    cell_variable_type: list[HorizontalGridCellVariableType] | str
    """
    Cell variable type

    The grid arrangement may define different cells
    for different types of physical variables, but only those cells
    that carry all of the specified physical variable types are described here.
    """

    resolution_x: float | None = Field(
        description=textwrap.dedent(
            """
            The size of grid cells in the 'X' direction

            The X direction for a grid defined by spherical polar coordinates is longitude.

            The value’s physical units are given by the `horizontal_units` property.

            Report only when cell sizes are identical or else reasonably uniform (in their given units).
            When cells sizes are not identical, a representative value should be provided
            and this fact noted in the description property of the `Grid`.
            If the cell sizes vary by more than 25%, set this to `None`.
            """
        ),
        gt=0,
    )

    resolution_y: float | None = Field(
        description=textwrap.dedent(
            """
            The size of grid cells in the 'Y' direction

            The Y direction for a grid defined by spherical polar coordinates is longitude.

            The value’s physical units are given by the `horizontal_units` property.

            Report only when cell sizes are identical or else reasonably uniform (in their given units).
            When cells sizes are not identical, a representative value should be provided
            and this fact noted in the description property of the `Grid`.
            If the cell sizes vary by more than 25%, set this to `None`.
            """
        ),
        gt=0,
    )

    horizontal_units: str | None = Field(
        description=textwrap.dedent(
            """
            The physical units of the `resolution_x` and `resolution_y` property values

            If `resolution_x` and `resolution_y` are `None`, set this to `None`.
            """
        ),
        gt=0,
    )

    southernmost_latitude: float | None = Field(
        description=textwrap.dedent(
            """
            The southernmost grid cell latitude, in degrees north

            Cells for which no calculations are made are included.
            The southernmost latitude may be shared by multiple cells.

            If the southernmost latitude is not known
            (e.g. the grid is adaptive), use `None`.
            """
        ),
        ge=-90.0,
        le=90.0,
    )

    westernmost_latitude: float | None = Field(
        description=textwrap.dedent(
            """
            The westernmost grid cell latitude, in degrees east, of the southernmost grid cell(s)

            Cells for which no calculations are made are included.
            The westernmost longitude is the smallest longitude value of the cells
            that share the latitude given by the `southernmost_latitude`.

            If the westernmost latitude is not known
            (e.g. the grid is adaptive), use `None`.
            """
        ),
        ge=0.0,
        le=360.0,
    )

    n_cells: int | None = Field(
        description=textwrap.dedent(
            """
            The total number of cells in the horizontal grid.

            If the total number of grid cells is not constant, set to `None`.
            """
        ),
        ge=1,
    )

    # Note: Allowing str is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    truncation_method: HorizontalGridTruncationMethod | str | None
    """
    The method for truncating the spherical harmonic representation of a spectral model when reporting on this grid

    If the grid is not used for reporting spherical harmonic representations, set to `None`.
    """

    truncation_number: int | None
    """
    The zonal (east-west) wave number at which a spectral model is truncated when reporting on this grid

    If the grid is not used for reporting spectral models, set to `None`.
    """

    resolution_range_km: list[float] = Field(
        description=textwrap.dedent(
            """
            The minimum and maximum resolution (in km) of cells of the horizontal grid

            Should be calculated according to the algorithm implemented by
            [this code](https://github.com/PCMDI/nominal_resolution/blob/master/lib/api.py).
            You need to take the min and max of the array that is returned
            when using the `returnMaxDistance` of the `mean_resolution` function.
            (Of course, using other implementations of the same algorithm is fine,
            if you're confident they give the same results.)
            """
        ),
        min_items=2,
        max_items=2,
    )

    mean_resolution_km: float = Field(
        description=textwrap.dedent(
            """
            The mean resolution (in km) of cells of the horizontal grid

            Should be calculated according to the algorithm implemented by
            [this code](https://github.com/PCMDI/nominal_resolution/blob/master/lib/api.py).
            (Of course, using other implementations of the same algorithm is fine,
            if you're confident they give the same results.)
            """
        ),
        gt=0.0,
    )

    # Note: Allowing str is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    nominal_resolution: NominalResolution | str
    """
    Nominal resolution of the grid
    """

    @validator("drs_name")
    def validate_drs_name(cls, v):
        r"""Validate that the drs_name is `g\d*`"""
        if not re.match(r"^g\d*$", v):
            msg = rf"`drs_name` for {cls} must be of the form `g\d*` i.e. g followed by an integer. Received: {v}"
            raise ValueError(msg)

        return v

    @validator("horizontal_units")
    def validate_horizontal_units(cls, v, values):
        """
        Validate horizontal_units
        """
        resolution_fields = {"resolution_x", "resolution_y"}
        has_resolution = any(values.get(field) is not None for field in resolution_fields)
        if has_resolution:
            if not v:
                raise ValueError("horizontal_units is required when resolution_x or resolution_y are set")

            allowed_values = {"km", "degree"}
            if v not in allowed_values:
                msg = f"horizontal_units must be one of {allowed_values}. Received: {v}"
                raise ValueError(msg)
        elif v:
            msg = (
                f"If all of {resolution_fields} are `None`, then `horizontal_units` must also be `None`. "
                f"Received: {v}"
            )
            raise ValueError(msg)

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
    # TODO: double check that this is correct.
    # The function signature looks wrong, why does it take `v` and `values`,
    # rather than just `v`?
    def validate_mean_resolution_in_range(cls, v, values):
        """Validate that mean resolution is within the resolution range."""
        if v is not None and "resolution_range_km" in values and values["resolution_range_km"]:
            range_km = values["resolution_range_km"]
            if not (range_km[0] <= v <= range_km[1]):
                raise ValueError(
                    f"mean_resolution_km ({v}) must be between "
                    f"resolution_range_km min ({range_km[0]}) and max ({range_km[1]})"
                )

        return v
