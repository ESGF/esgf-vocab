from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Realm(PlainTermDataDescriptor):
    """
    Realm of the data
    """

    description: str
    name: str
