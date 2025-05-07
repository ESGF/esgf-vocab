from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class License(PlainTermDataDescriptor):
    kind: str
    license: str | None
    url: str | None
