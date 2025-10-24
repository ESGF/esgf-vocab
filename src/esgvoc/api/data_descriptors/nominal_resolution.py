"""
Model (i.e. schema/definition) of the nominal resolution data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class NominalResolution(PlainTermDataDescriptor):
    """
    Approximate horizontal resolution of a dataset

    Examples: "1 km", "250 km", "500 km"

    This should be calculated following the algorithm implemented by
    [https://github.com/PCMDI/nominal_resolution/blob/master/lib/api.py]()
    (although, of course, other implementations of the same algorithm could be used).
    """

    # Developer note: given this isn't a pattern term data descriptor,
    # these are split so people don't have to parse the drs_name themselves.
    magnitude: float
    """
    Magnitude of the nominal resolution
    """

    unit: str
    """
    Unit of the nominal resolution
    """
