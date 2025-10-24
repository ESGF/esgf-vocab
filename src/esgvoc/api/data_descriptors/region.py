from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Region(PlainTermDataDescriptor):
    """
    Region associated with the dataset

    Examples: antarctica", "global", "limited_area"

    In other words, the domain over which the dataset is provided.
    The names are defined by the
    CF standardised regions
    (
    https://cfconventions.org/Data/standardized-region-list/standardized-region-list.current.html
    ).
    """

    # Note: do not merge until the conversation about the naming convention
    # here is resolved:
    # https://github.com/ESGF/esgf-vocab/pull/156/files#r2453875274
    # Depending on which way this goes, we might need to introduce RegionEMD,
    # which will differ from Region (as used in the DR).
    # If we use CF standardised regions, make an issue
    # to decide how to validate that registered names are CF standard names
    # (same idea as this, but for regions instead of variables,
    # https://github.com/ESGF/esgf-vocab/issues/158)
