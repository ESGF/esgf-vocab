"""
Model (i.e. schema/definition) of the MIP era data descriptor
"""

from pydantic import HttpUrl

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class MipEra(PlainTermDataDescriptor):
    """
    Label that identifies the MIP era to which a dataset belongs

    Examples: "CMIP6", "CMIP7"

    The MIP era is useful to distinguish among experiments performed during different CMIP phases
    but with differences in experimental protocol in each phase.
    For example, the "historical" experiments appear in multiple phases of CMIP
    but have different input forcings in each.
    This difference can be identified using the MIP era data descriptor.
    """

    url: HttpUrl
    """
    URL that links to further information about the MIP era
    """
