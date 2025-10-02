from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Product(PlainTermDataDescriptor):
    """
    Rough description of what kind of data product this is

    Not always 100% clear, so just do category that fits best
    """

    description: str
    """
    Description of the product
    """

    kind: str
