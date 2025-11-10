"""
Model (i.e. schema/definition) of the conventions data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


# TODO: revert to PlainTermDataDescriptor.
# See https://github.com/ESGF/esgf-vocab/pull/168#discussion_r2499193117
class Convention(PatternTermDataDescriptor):
    """
    CF version governing the data

    Examples: "CF-1.10", "CF-1.12"

    Climate and forecast metadata conventions (https://cfconventions.org/)
    that the data follows.
    This data descriptor is actually defined by the CF-conventions.
    However, it is often used in a more specific and restrictive form
    within WCRP activities.
    To support this possibility, this data descriptor must also be defined within esgvoc.
    """
