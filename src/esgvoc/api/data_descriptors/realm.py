"""
Model (i.e. schema/definition) of the realm data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Realm(PlainTermDataDescriptor):
    """
    Realm associated with the dataset

    Examples: "atmos", "land", "ocean", "atmosChem"

    This is intended as a rough categorisation only
    and is not precisely defined.
    """
