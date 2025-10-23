"""
Model (i.e. schema/definition) of the horizontal grid type data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class HorizontalGridType(PlainTermDataDescriptor):
    """
    Horizontal grid type

    Examples: "regular_latitude_longitude", "regular_gaussian", "rotated_pole"

    A grid type describes the method for distributing grid points over the Earth's surface
    (approximately a sphere).
    """
