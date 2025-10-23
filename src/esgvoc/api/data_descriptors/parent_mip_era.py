"""
Model (i.e. schema/definition) of the parent MIP era data descriptor
"""

from esgvoc.api.data_descriptors.mip_era import MipEra


class ParentMipEra(MipEra):
    """
    The MIP era of the parent dataset from which this dataset branched

    Examples: "CMIP6", "CMIP7"

    Only applies if the dataset has a parent (i.e. branched from another dataset).
    """
