from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class EMDResolution(PlainTermDataDescriptor):
    """
    The nominal resolution (in km) characterises the resolution of a model’s native horizontal grid. See section 5.1 Native horizontal grid properties.
    Options for the native horizontal grid nominal resolution property are defined in the following table as a function of the value of the mean resolution km property:

    for mean resolution, R, in the range (km):
    nominal resolution is:
    0.036 ≤ R < 0.072
    0.05 km
    0.072 ≤ R < 0.16
    0.1 km
    0.16 ≤ R < 0.36
    0.25 km
    0.36 ≤ R < 0.72
    0.5 km
    0.72 ≤ R < 1.6
    1 km
    1.6 ≤ R < 3.6
    2.5 km
    3.6 ≤ R < 7.2
    5 km
    7.2 ≤ R < 16
    10 km
    16 ≤ R < 36
    25 km
    36 ≤ R < 72
    50 km
    72 ≤ R < 160
    100 km
    160 ≤ R < 360
    250 km
    360 ≤ R < 720
    500 km
    720 ≤ R < 1600
    1000 km
    1600 ≤ R < 3600
    2500 km
    3600 ≤ R < 7200
    5000 km
    7200 ≤ R < 16000
    10000 km
            7.10. Native vertical grid “Coordinate” CV
    """

    mean_resolution: str
