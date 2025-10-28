"""
Model (i.e. schema/definition) of the grid data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


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

    # TODO: consider whether there is a tight coupling to region or not.
    # Let's see where https://github.com/WCRP-CMIP/CMIP7-CVs/issues/202#issuecomment-3455040709
    # goes.
    # Whatever the answer, we can't make this the same as HorizontalGrid.
    # If grid defines the region, then we need to use CMIP regions here,
    # not EMD regions.
    #    We can't use EMD regions because they can include "limited_area".
    #    If we forced EMD regions to be the same as CMIP regions,
    #    then we could make grid and horizontal grid the same
    #    (assuming that grid defines the region).
    # If grid does not define the region, then the data models
    # for grid and horizontal grid are simply different.
