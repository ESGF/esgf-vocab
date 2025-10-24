"""
Model (i.e. schema/definition) of the branch time in child data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


# TODO: discuss - it's not a pattern, it's a float. Do we need a new DataDescriptor?
class BranchTimeInChild(PatternTermDataDescriptor):
    """
    The time, in the dataset, at which it branched from its parent dataset

    Examples: 0., 365., 10100.0, -100.

    Only applies if the dataset has a parent (i.e. branched from another dataset).
    The units and calendar which apply to this time
    must be the same as the dataset's time axis' units and calendar.
    """
