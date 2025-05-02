from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Product(PlainTermDataDescriptor):
    description: str
    kind: str
