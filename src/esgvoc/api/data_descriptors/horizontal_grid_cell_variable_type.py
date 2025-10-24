"""
Model (i.e. schema/definition) of the horizontal grid cell variable data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class HorizontalGridCellVariableType(PlainTermDataDescriptor):
    """
    Horizontal grid cell variable type

    Examples: "mass", "velocity_x", "velocity_y"


    The type of physical variables
    that are carried at, or representative of conditions at,
    the cells described by the horizontal grid.
    A variable type comprises a class of physical quantities
    that are typically found at the same grid location,
    i.e. one of the locations defined by the horizontal grid arrangement property. See section 4.1 Horizontal grid.
    """
