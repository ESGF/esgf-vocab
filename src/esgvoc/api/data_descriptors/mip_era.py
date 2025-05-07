from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class MipEra(PlainTermDataDescriptor):
    start: int
    end: int
    name: str
    url: str
