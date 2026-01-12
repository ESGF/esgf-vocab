"""
EMD v1.0 Section 7.7 - grid_mapping CV

Grid mapping (coordinate reference system) types.
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class GridMapping(PlainTermDataDescriptor):
    """
    Grid mapping (EMD v1.0 Section 7.7).

    Options: latitude_longitude, lambert_conformal_conic, etc.

    The name of the coordinate reference system of the horizontal coordinates.
    """

    pass
