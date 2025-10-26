"""
Model (i.e. schema/definition) of the data specifications data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class DataSpecsVersion(PlainTermDataDescriptor):
    """
    Data specifications version number

    Examples: "MIPDS7-202510p01", "MIPDS7-202510p01hbeta", "MIPDS7-0p1p0", "MIPDS7-0p1p0hrc1"

    The data specifications describe the overall set of data specifications
    used when writing the dataset.
    This version number captures exactly which set of data specifications
    are consistent (or intended to be consistent) with this dataset.
    (At the moment, exactly what this means is still vague, particularly for CMIP7.
    When it solidifies, more details and examples will be added here.)
    """
