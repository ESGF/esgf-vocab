"""
EMD (Essential Model Documentation) Pydantic Models - Version 1.0

This package implements the EMD v1.0 specification.
For specification details, see: Essential Model Documentation (EMD) - version 1.0.docx

Major changes from v0.993:
- Horizontal grid changed from flat to nested 3-level structure
  (HorizontalComputationalGrid → HorizontalSubgrid → HorizontalGridCells)
- Field renames: coordinate → vertical_coordinate, native_*_grid → *_computational_grid
- New required description fields in Model, ModelComponent, and grids
- New spatial_refinement field in HorizontalGridCells
"""

# Core EMD models
from .model import Model
from .model_component import EMDModelComponent
from .reference import Reference

# Grid models (v1.0 nested structure)
from .horizontal_computational_grid import HorizontalComputationalGrid
from .horizontal_grid_cells import HorizontalGridCells
from .horizontal_subgrid import HorizontalSubgrid
from .vertical_computational_grid import VerticalComputationalGrid
from .vertical_units import VerticalUnits

# Supporting models
from .resolution import EMDResolution

# Controlled Vocabulary (CV) models - EMD Section 7
from .arrangement import Arrangement
from .calendar import Calendar
from .cell_variable_type import CellVariableType
from .component_type import ComponentType
from .coordinate import Coordinate
from .grid_mapping import GridMapping
from .grid_region import GridRegion
from .grid_type import GridType
from .temporal_refinement import TemporalRefinement
from .truncation_method import TruncationMethod

__all__ = [
    # Core models
    "Model",
    "EMDModelComponent",
    "Reference",
    # Grid models
    "HorizontalComputationalGrid",
    "HorizontalSubgrid",
    "HorizontalGridCells",
    "VerticalComputationalGrid",
    "VerticalUnits",
    # Supporting
    "EMDResolution",
    # CV models (Section 7)
    "Arrangement",
    "Calendar",
    "CellVariableType",
    "ComponentType",
    "Coordinate",
    "GridMapping",
    "GridRegion",
    "GridType",
    "TemporalRefinement",
    "TruncationMethod",
]
