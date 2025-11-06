"""
Model (i.e. schema/definition) of the frequency data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Frequency(PlainTermDataDescriptor):
    """
    Reporting/temporal sampling interval used when creating the dataset

    Examples: "mon", "day", "3hr", "monC"

    This is a bit of a trickier concept than it first appears.
    For time average data, it is effectively the size of each time cell
    (e.g. if each time point is the average of a month's worth of data,
    then the data is assigned the term "mon").
    For time point data, it is the time interval between each reported point
    (e.g. if the data is reported at midday each day,
    then the data is assigned the term "day",
    although in practice the size of each time cell works in this case too).

    This can usually be validated against the actual data in the file,
    but it can be complicated with some calendars
    (e.g. the Julian-Gregorian calendar which has 15 missing days in 1582),
    reporting intervals (e.g. "mon", which changes length at each interval)
    and when climatologies are involved
    (as identifying these follows special rules covered by the CF conventions).
    """

    interval: float
    """
    Size of the interval

    See `self.units` for units.
    """

    units: str
    """Units of the interval"""
