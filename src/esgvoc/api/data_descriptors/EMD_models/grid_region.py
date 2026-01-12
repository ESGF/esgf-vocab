"""
EMD v1.0 Section 7.5 - region CV

Horizontal grid region types.
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class GridRegion(PlainTermDataDescriptor):
    """
    Horizontal grid region (EMD v1.0 Section 7.5).

    Options: global, antarctica, greenland, limited_area, 30S-90S, etc.

    A region is a contiguous part of the Earth's surface which spans the horizontal grid cells.
    """

    pass
