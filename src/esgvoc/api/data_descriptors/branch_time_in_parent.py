"""
Model (i.e. schema/definition) of the branch time in parent data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


# TODO: discuss - it's not a pattern, it's a float. Do we need a new DataDescriptor?
class BranchTimeInParent(PatternTermDataDescriptor):
    """
    The time, in the parent dataset, at which this dataset branched from its parent dataset

    Examples: 0., 365., 10100.0, -500.0

    Only applies if the dataset has a parent (i.e. branched from another dataset).
    The units for this value are given in :py:class`ParentTimeUnits` and :py:class`ParentTimeCalendar`.
    """
