from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Unit(PlainTermDataDescriptor):
    """
    Native vertical grid units of the top level boundary or top layer thickness value. See section 5.2 Native vertical grid properties.
    Options for the native vertical grid Units property:
        • m
            ◦ metre (unit for length).
        • Pa
            ◦ pascal (unit for pressure).
        • K
            ◦ kelvin (unit for temperature).
            ◦
    """

    description: str
