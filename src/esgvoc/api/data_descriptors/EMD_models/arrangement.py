"""
EMD v1.0 Section 7.3 - arrangement CV

Horizontal grid arrangement types (Arakawa grids).
"""

from pydantic import Field
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Arrangement(PlainTermDataDescriptor):
    """
    Horizontal grid arrangement (EMD v1.0 Section 7.3).

    Options: arakawa_a, arakawa_b, arakawa_c, arakawa_d, arakawa_e

    A grid arrangement describes the relative locations of mass- and velocity-related quantities
    on the computed grid (for instance Collins et al. (2013), and for unstructured grids
    Thuburn et al. (2009)).
    """

    n_sub_grid: int = Field(description="maximum number of sub_grids for this arrangement")
