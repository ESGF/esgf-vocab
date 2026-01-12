"""
EMD v1.0 Section 7.4 - cell_variable_type CV

Types of physical variables carried at grid cells.
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class CellVariableType(PlainTermDataDescriptor):
    """
    Cell variable type (EMD v1.0 Section 7.4).

    Options: mass, x_velocity, y_velocity, velocity

    Types of physical variables that are carried at, or representative of conditions at,
    cells of a horizontal subgrid.
    """

    pass
