from esgvoc.api.data_descriptors.data_descriptor import DrsPlainTermDataDescriptor


class MipEra(DrsPlainTermDataDescriptor):
    start: int
    end: int
    name: str 
    url: str