"""
Model (i.e. schema/definition) of the contributor data descriptor
"""

from esgvoc.api.data_descriptors.contributor_member import ContributorMember
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Contributor(PlainTermDataDescriptor):
    """
    A registered contributor

    Examples: "IPSL", "NCAR", "CNRM-CERFACS", "SOLARIS-HEPPA"
    """

    members: list[ContributorMember]
    """
    Members associated with this contributor
    """
