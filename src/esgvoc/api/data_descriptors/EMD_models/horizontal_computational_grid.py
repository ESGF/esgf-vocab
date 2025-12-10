"""
Horizontal computational grid description (EMD v1.0 Section 4.1.1).

A model component's horizontal computational grid is composed of one or more
horizontal subgrids, on which different sets of variables are calculated.
"""

from __future__ import annotations

from typing import List

from pydantic import Field, field_validator

from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor

from .horizontal_subgrid import HorizontalSubgrid


class HorizontalComputationalGrid(DataDescriptor):
    """
    Horizontal computational grid description (EMD v1.0 Section 4.1.1).

    A model component's horizontal computational grid is composed of one or more
    horizontal subgrids, on which different sets of variables are calculated.
    When the computational grid relies on more than one subgrid, it is referred to
    as a "staggered" grid. For most staggered grids, the velocity-related variables
    are calculated on a subgrid offset from the mass-related variables (e.g. pressure,
    temperature, water vapour and other mass constituents).
    """

    arrangement: str = Field(
        description="A characterisation of the grid staggering defining the relative positions of computed "
        "mass-related and velocity-related variables. Taken from 7.3 arrangement CV. "
        "Options: 'arakawa_a', 'arakawa_b', 'arakawa_c', 'arakawa_d', 'arakawa_e'. "
        "E.g. 'arakawa_c'"
    )

    horizontal_subgrids: List[HorizontalSubgrid] = Field(
        description="All of the subgrids, of which there must be at least one, used to construct the "
        "horizontal computational grid. Each subgrid is associated with one or more variable types "
        "(mass-related, velocity-related, etc.), consistent with the arrangement property.",
        min_length=1,
    )

    @field_validator("horizontal_subgrids")
    @classmethod
    def validate_at_least_one_subgrid(cls, v):
        """Validate that there is at least one horizontal subgrid."""
        if not v or len(v) < 1:
            raise ValueError("At least one horizontal subgrid must be provided")
        return v

    def accept(self, visitor):
        """Accept a data descriptor visitor."""
        return visitor.visit_plain_term(self)
