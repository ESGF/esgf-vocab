"""
Model (i.e. schema/definition) of the horizontal grid temporal refinement data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class HorizontalGridTemporalRefinement(PlainTermDataDescriptor):
    """
    Horizontal grid temporal refinement

    Examples: "static", "adaptive", "dynamically_stretched"

    This indicates how the distribution of grid cells varies with time.
    """
