from esgvoc.api.data_descriptors.data_descriptor import DrsPlainTermDataDescriptor


class GridLabel(DrsPlainTermDataDescriptor):
    description: str
    short_name: str 
    name: str 
    region: str