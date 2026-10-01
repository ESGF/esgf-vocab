"""
Model (i.e. schema/definition) of the grid data descriptor
"""

from pydantic import Field, field_validator

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
from esgvoc.api.data_descriptors.EMD_models.grid_mapping import GridMapping
from esgvoc.api.data_descriptors.EMD_models.grid_type import GridType
from esgvoc.api.data_descriptors.region import Region


class Grid(PlainTermDataDescriptor):
    """
    Grid (horizontal) on which the data is reported

    Examples: "g1", "g2", "g33"

    The value has no intrinsic meaning within the CVs.
    However, the other attributes of this model
    provide information about the grid
    and in other external sources (to be confirmed which)
    further resources can be found e.g. cell areas.

    Grids with the same id (also referred to as 'grid label')
    are identical (details on how we check identical are to come, for discussion,
    see https://github.com/WCRP-CMIP/CMIP7-CVs/issues/202)
    and can be used by more than one model
    (also referred to as 'source' in CMIP language).
    Grids with different labels are different.
    """

    # Note: Allowing str is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    region: Region | str
    """
    Region represented by this grid
    """
    # Developer note:
    # There is a tight coupling to region
    # (see https://github.com/WCRP-CMIP/CMIP7-CVs/issues/202#issue-3084934841).
    # However, this region can't be the same as the regions used by EMD,
    # as EMD has the 'limited_area' region, but that's not something
    # which makes sense in the CMIP context (it's too vague).
    # As a result, we need to have both Grid (CMIP) and HorizontalGrid (EMD)
    # and both Region (CMIP) and HorizontalGridRegion (EMD).

    # The fields below are copied from the EMD horizontal_grid_cell
    # with the same id (see the EMD sync script in CMIP7-CVs).
    # They are optional because grids which are not described in EMD
    # (e.g. the CMIP6-style labels "gn", "gr1") don't have them.
    grid_type: GridType | str | None = None
    """
    Horizontal grid type, i.e. the method of distributing grid cells over the region

    Taken from the grid_type CV (EMD v1.0 Section 7.6).
    E.g. 'regular_latitude_longitude', 'tripolar'
    """

    n_cells: int | None = Field(default=None, ge=1)
    """
    Total number of cells in the horizontal grid

    None if the number of grid cells is not constant or not known.
    """

    grid_mapping: GridMapping | str | None = None
    """
    Name of the coordinate reference system of the horizontal coordinates

    Taken from the grid_mapping CV (EMD v1.0 Section 7.7).
    E.g. 'latitude_longitude', 'polar_stereographic'
    """

    @field_validator("grid_type", "n_cells", "grid_mapping", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        """EMD uses empty strings for values which are not applicable."""
        if v == "":
            return None
        return v
