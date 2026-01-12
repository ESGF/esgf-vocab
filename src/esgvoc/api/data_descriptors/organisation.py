"""
Model (i.e. schema/definition) of the organisation data descriptor
"""

from esgvoc.api.data_descriptors.institution import Institution
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Organisation(PlainTermDataDescriptor):
    """
    A registered organisation

    Examples: "IPSL", "NCAR", "CNRM-CERFACS", "SOLARIS-HEPPA"
    """

    # Note: Allowing str is under discussion.
    # Using this to get things working.
    # Long-term, we might do something different.
    members: list[Institution | str]
    """
    Members associated with this organisation
    """
