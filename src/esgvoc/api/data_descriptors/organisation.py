"""
Model (i.e. schema/definition) of the organisation data descriptor
"""

from typing import List

from pydantic import Field

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
from esgvoc.api.data_descriptors.EMD_models.model import Model
from esgvoc.api.data_descriptors.institution import Institution


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

    publishable_models: List[Model | str] = Field(
        default_factory=list, description="Models that this organisation can publish"
    )
