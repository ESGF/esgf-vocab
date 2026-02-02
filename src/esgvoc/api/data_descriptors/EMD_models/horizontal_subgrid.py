"""
Horizontal subgrid description (EMD v1.0 Section 4.1.2).

A horizontal subgrid describes the grid cells at one of the stagger positions
of a horizontal computational grid.
"""

from __future__ import annotations

import warnings
from typing import List

from pydantic import BaseModel, Field, field_validator

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
        "E.g. ['mass'], ['x_velocity'], ['mass', 'x_velocity', 'y_velocity'], ['mass', 'velocity'].",
        default_factory=list,
    )

    horizontal_grid_cells: HorizontalGridCells = Field(
        description="A description of the characteristics and location of the grid cells of this subgrid."
    )

    @field_validator("cell_variable_type")
    @classmethod
    def validate_cell_variable_type_unique(cls, v):
        """Validate that cell_variable_type has 1+ different values (EMD Conformance Section 4.1.2) (warning mode)."""
        if not v:
            warnings.warn(
                "EMD Conformance: At least one cell_variable_type must be specified",
                UserWarning,
                stacklevel=2,
            )
            return v

        # Extract identifiers and check for duplicates
        seen = set()
        for item in v:
            item_id = item if isinstance(item, str) else getattr(item, "id", str(item))
            if item_id in seen:
                warnings.warn(
                    f"EMD Conformance: cell_variable_type values must be different, '{item_id}' appears multiple times",
                    UserWarning,
                    stacklevel=2,
                )
            seen.add(item_id)
        return v
