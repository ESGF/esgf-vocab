from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Frequency(PlainTermDataDescriptor):
    """
    Frequency options

    This is actually a misnomer.
    The units of these things are time,
    not 1 / time (which is what is expected for a frequency),
    so referring to this as 'time sampling' or 'time sampling interval'
    would be more accurate.
    """

    description: str
    long_name: str
    name: str
    unit: str
    # What is unit meant to be here? hour, day, month or 1 hour, 3 days etc.?

    # Add approx_interval to support CMOR?
