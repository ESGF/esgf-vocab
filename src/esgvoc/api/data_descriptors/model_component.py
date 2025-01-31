from esgvoc.api.data_descriptors.data_descriptor import DrsPlainTermDataDescriptor


class ModelComponent(DrsPlainTermDataDescriptor):
    description: str
    name: str 
    realm: dict
    nominal_resolution: dict
    version: int