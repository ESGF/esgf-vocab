from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Resolution(PlainTermDataDescriptor):
    description: str
    value: str
    name: str
    unit: str
