"""
Model of the coordinate type data descriptor.
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class CoordinateType(PlainTermDataDescriptor):
    """
    Classification of coordinates by their structural role in a data file.

    Coordinate types are governed vocabulary terms rather than a Python enum.
    They tell consumers what kind of validation or generation logic applies to
    a coordinate, independently of its physical meaning.
    """
