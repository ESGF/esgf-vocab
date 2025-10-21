"""
Model (i.e. schema/definition) of the conventions data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Convention(PlainTermDataDescriptor):
    """
    CF version governing the data

    Examples: "CF-1.10", "CF-1.12"

    Climate and forecast metadata conventions (https://cfconventions.org/)
    that the data follows.
    This data descriptor is actually defined by the CF-conventions.
    However, it is often used in a more specific and restrictive form
    within WCRP activities, which is why we have to define it within esgvoc.
    """

    # TODO: delete given we have description and drs_name
    label: str
