"""
Model (i.e. schema/definition) of the horizontal grid arrangement data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class HorizontalGridArrangement(PlainTermDataDescriptor):
    """
    Horizontal grid arrangement

    Examples: "arakawa_a", "arakawa_b", "arakawa_e"

    A grid arrangement describes the relative locations of mass- and velocity-related quantities
    on the computed grid (for instance
    [Collins et al. (2013)](http://dx.doi.org/10.5772/55922),
    and for unstructured grids
    [Thuburn et al. (2009)](https://doi.org/10.1016/j.jcp.2009.08.006)).
    """
