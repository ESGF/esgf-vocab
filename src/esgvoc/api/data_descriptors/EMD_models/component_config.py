"""
Component configuration

Links a model component to its horizontal and vertical computational grids,
forming a complete configuration used within a top-level model / source_id.

This allows us to find the geneology of a model, and its components. 
"""

from __future__ import annotations
from pydantic import Field

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor

from .horizontal_computational_grid import HorizontalComputationalGrid
from .model_component import EMDModelComponent
from .vertical_computational_grid import VerticalComputationalGrid


class ComponentConfig(PlainTermDataDescriptor):
    """
    A component configuration binds a specific model component to a horizontal and
    vertical computational grid. It represents a named configuration that
    can be referenced when documenting how a source is assembled.

    Examples: atmosphere with h100 and v100, ocean with h101 and v102.
    """

    model_component: str | EMDModelComponent = Field(
        description="The model component that this configuration applies to. "
        "Referenced by its ID (e.g. 'arpege-climat-version-6-3') or as a full EMDModelComponent object."
    )

    horizontal_computational_grid: str | HorizontalComputationalGrid = Field(
        description="The horizontal computational grid used by this component configuration. "
        "Referenced by its ID (e.g. 'h100') or as a full HorizontalComputationalGrid object."
    )

    vertical_computational_grid: str | VerticalComputationalGrid = Field(
        description="The vertical computational grid used by this component configuration. "
        "Referenced by its ID (e.g. 'v100') or as a full VerticalComputationalGrid object."
    )
