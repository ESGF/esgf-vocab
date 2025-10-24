"""
Model (i.e. schema/definition) of the grid data descriptor
"""

from esgvoc.api.data_descriptors.horizontal_grid import HorizontalGrid


# Developer note: deliberately just subclassing HorizontalGrid.
# These two ideas are meant to be the same,
# we just support both names:
# - Grid: the CVs name
# - HorizontalGrid: the EMD name
class Grid(HorizontalGrid):
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
