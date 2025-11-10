"""
Model (i.e. schema/definition) of the conventions data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Convention(PlainTermDataDescriptor):
    """
    Conventions governing the data

    Examples: "CF-1.10", "CF-1.12"

    This data descriptor is actually defined by the CF-conventions.
    However, it is often used in a more specific and restrictive form
    within WCRP activities.
    To support this possibility, this data descriptor must also be defined within esgvoc.

    The most commonly specified conventions are the
    climate and forecast metadata conventions (https://cfconventions.org/).
    Other conventions can also be specified in the 'Conventions'
    attribute of netCDF files/other metadata.
    The different conventions are usually separated by a whitespace.
    Within esgvoc, the 'components' (i.e. whitespace separated bits)
    are all that is specified.
    If users wish to combine them, they can,
    but esgvoc does not treat this as either a pattern or composite term.
    """
