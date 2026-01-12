"""
Model (i.e. schema/definition) of the product data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Product(PlainTermDataDescriptor):
    """
    Identifier of the data category

    Examples: "model-output", "observations", derived"

    This is not a precisely defined data descriptor,
    rather an approximate labelling.
    """
