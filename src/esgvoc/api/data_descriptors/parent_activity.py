"""
Model (i.e. schema/definition) of the parent activity data descriptor
"""

from esgvoc.api.data_descriptors.activity import Activity


class ParentActivity(Activity):
    """
    The activity of the parent dataset from which this dataset branched

    Examples: "ScenarioMIP", "CMIP", "C4MIP"

    Only applies if the dataset has a parent (i.e. branched from another dataset).
    """
