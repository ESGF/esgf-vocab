"""
Model (i.e. schema/definition) of the horizontal grid region data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
from esgvoc.api.data_descriptors.region import Region


class HorizontalGridRegion(PlainTermDataDescriptor):
    """
    Horizontal grid region

    Examples: "global", "global_land", "limited_area"

    Native horizontal grid region types,
    i.e. the portion of the globe where horizontal grid calculations are performed.
    """

    cf_standard_region: str | None
    """
    CF standard region
    See https://cfconventions.org/Data/standardized-region-list/standardized-region-list.current.html
    If `None`, there is no CF standard region for this region
    """

    # Note: ongoing discussion about whether we need `| str` in the type hint
    region: Region | str | None
    """
    Equivalent region

    If `None`, there is no equivalent :py:class:`Region`.
    There is a difference between region and horizontal grid region
    because of the context in which they are used.
    It's debatable whether this is helpful or not,
    but on the timescales we were working to we needed to differentiate them,
    in essence to allow EMD to use limited area
    while avoiding such a vague definition leaking into the region definitions.
    """
