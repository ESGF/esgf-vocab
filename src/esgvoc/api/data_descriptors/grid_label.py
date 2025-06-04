from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class GridLabel(PlainTermDataDescriptor):
    description: str
    short_name: str
    name: str
    region: str
