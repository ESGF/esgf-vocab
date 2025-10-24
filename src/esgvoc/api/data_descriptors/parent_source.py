"""
Model (i.e. schema/definition) of the parent source data descriptor
"""

from esgvoc.api.data_descriptors.source import Source


class ParentSource(Source):
    """
    The source of the parent dataset from which this dataset branched

    Examples: "CanESM6-MR", "UKESM1-0-LL"

    Only applies if the dataset has a parent (i.e. branched from another dataset).
    """
