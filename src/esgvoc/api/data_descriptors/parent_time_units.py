"""
Model (i.e. schema/definition) of the parent time units data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


class ParentTimeUnits(PatternTermDataDescriptor):
    """
    The time units in the parent dataset from which this dataset branched

    Examples: "days since 1850-01-01", "days-since-0001-01-01"

    Only applies if the dataset has a parent (i.e. branched from another dataset).
    The value is given in :py:class`BranchTimeInParent` and the calendar in :py:class`ParentTimeCalendar`.

    The rules governing these values are set by the CF-conventions, see
    https://cfconventions.org/Data/cf-conventions/cf-conventions-1.12/cf-conventions.html#time-coordinate-units.
    """
