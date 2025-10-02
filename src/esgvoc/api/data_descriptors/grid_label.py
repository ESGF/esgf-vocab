from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class GridLabel(PlainTermDataDescriptor):
    """
    Label that identifies the grid of the data

    Exact meaning of this is still being discussed,
    see https://github.com/WCRP-CMIP/CMIP7-CVs/issues/202.
    """

    description: str
    short_name: str
    name: str
    region: str
