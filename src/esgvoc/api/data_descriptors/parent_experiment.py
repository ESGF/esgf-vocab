"""
Model (i.e. schema/definition) of the parent experiment data descriptor
"""

from esgvoc.api.data_descriptors.parent import Experiment


class ParentExperiment(Experiment):
    """
    The experiment of the parent dataset from which this dataset branched

    Examples: "historical", "piControl", "ssp245"

    Only applies if the dataset has a parent (i.e. branched from another dataset).
    """
