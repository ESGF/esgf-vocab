from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class SourceType(PlainTermDataDescriptor):
    """
    Known source types e.g. GCM, aerosol scheme, radiation scheme
    """

    description: str
