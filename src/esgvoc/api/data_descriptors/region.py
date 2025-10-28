"""
Model (i.e. schema/definition) of the region data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Region(PlainTermDataDescriptor):
    """
    Region associated with the dataset

    Examples: "glb", "30s-90s", "grl"

    In other words, the domain over which the dataset is provided.
    This is intended as a rough categorisation only
    and is not precisely defined.
    """

    cf_standard_region: str | None
    """
    CF standard region

    See https://cfconventions.org/Data/standardized-region-list/standardized-region-list.current.html

    If `None`, there is no CF standard region for this region
    """

    iso_region: str | None
    """
    ISO 3166-1 alpha-3 region code

    See https://www.iso.org/iso-3166-country-codes.html

    If `None`, there is no ISO region code for this region
    """
