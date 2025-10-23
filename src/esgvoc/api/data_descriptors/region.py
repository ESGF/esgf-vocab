"""
Model (i.e. schema/definition) of the region data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Region(PlainTermDataDescriptor):
    """
    Region associated with the dataset

    Examples: "GLB", "GRL", "ATA"

    In other words, the domain over which the dataset is provided.
    This is intended as a rough categorisation only
    and is not precisely defined.
    """
