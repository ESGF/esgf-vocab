from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Frequency(PlainTermDataDescriptor):
    """
    Frequency options
    """

    description: str
    long_name: str
    name: str
    unit: str
    # What is unit meant to be here? hour, day, month or 1 hour, 3 days etc.?

    # Add approx_interval to support CMOR?
