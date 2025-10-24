"""
Model (i.e. schema/definition) of the horizontal grid truncation method data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class HorizontalGridTruncationMethod(PlainTermDataDescriptor):
    """
    Horizontal grid truncation method

    Examples: "triangular", "rhomboidal"

    A truncation method describes the technique
    used to truncate the spherical harmonic representation of a spectral model.
    This is then made a property of the grid
    i.e. the grid is coupled to the truncation method used for reporting on the grid.
    """
