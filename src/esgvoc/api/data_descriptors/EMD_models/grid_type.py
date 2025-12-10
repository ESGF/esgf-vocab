"""
EMD v1.0 Section 7.6 - grid_type CV

Horizontal grid types.
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class GridType(PlainTermDataDescriptor):
    """
    Horizontal grid type (EMD v1.0 Section 7.6).

    Options: regular_latitude_longitude, regular_gaussian, reduced_gaussian, tripolar, etc.

    A grid type describes the method for distributing grid points over the sphere.
    """

    pass
