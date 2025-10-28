"""
Model (i.e. schema/definition) of the grid data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
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

    region: Region
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
