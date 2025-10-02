from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


# TODO: rename to MIPEra?
class MipEra(PlainTermDataDescriptor):
    # Delete, not sure why this is there, shouldn't this just be a strin?
    start: int
    # Delete, not sure why this is there, shouldn't this just be a strin?
    end: int
    name: str
    url: str
