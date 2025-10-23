"""
Model (i.e. schema/definition) of the time range data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


class TimeRange(PatternTermDataDescriptor):
    """
    Time range spanned by the data

    Examples: "185001-202112", "18500101-20211231", "203101010130-203112312230", "185001-186412-clim"

    The right choice of time range is tightly coupled to the frequency of the data.
    This coupling is captured via the `time_range` attribute of :py:class:`Frequency`.
    """
