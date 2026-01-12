"""
Horizontal subgrid description (EMD v1.0 Section 4.1.2).

A horizontal subgrid describes the grid cells at one of the stagger positions
of a horizontal computational grid.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor

from .cell_variable_type import CellVariableType
from .horizontal_grid_cells import HorizontalGridCells


class HorizontalSubgrid(PlainTermDataDescriptor):
    """
    Horizontal subgrid description (EMD v1.0 Section 4.1.2).

    A horizontal subgrid describes the grid cells at one of the stagger positions
    of a horizontal computational grid. Often the locations of mass-related and
    velocity-related variables differ, so more than one horizontal subgrid will
    be defined as part of a horizontal computational grid.
    """

    cell_variable_type: List[str | CellVariableType] = Field(
        description="The types of physical variables that are carried at, or representative of conditions at, "
        "the cells described by this horizontal subgrid. Taken from 7.4 cell_variable_type CV. "
        "Options: 'mass', 'x_velocity', 'y_velocity', 'velocity'. "
        "E.g. ['mass'], ['x_velocity'], ['mass', 'x_velocity', 'y_velocity'], ['mass', 'velocity']. "
        "Can be an empty list in certain cases.",
        default_factory=list,
    )

    horizontal_grid_cells: HorizontalGridCells = Field(
        description="A description of the characteristics and location of the grid cells of this subgrid."
    )
