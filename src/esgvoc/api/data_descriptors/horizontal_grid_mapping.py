"""
Model (i.e. schema/definition) of the horizontal grid mapping data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class HorizontalGridMapping(PlainTermDataDescriptor):
    """
    Horizontal grid mapping

    Examples: "albers_conical_equal_area", "lambert_cylindrical_equal_area", "transverse_mercator"

    The horizontal grid mapping describes the horizontal coordinate reference system.
    The grid mappings are all CF grid mapping names
    (e.g.
    https://cfconventions.org/Data/cf-conventions/cf-conventions-1.12/cf-conventions.html#grid-mappings-and-projections
    )
    with the same definitions.
    """
