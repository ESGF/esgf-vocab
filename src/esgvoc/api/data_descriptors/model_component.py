from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class ModelComponent(PlainTermDataDescriptor):
    name: str
    realm: dict
    nominal_resolution: dict
    version: int
