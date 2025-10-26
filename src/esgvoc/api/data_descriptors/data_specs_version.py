"""
Model (i.e. schema/definition) of the data specifications data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class DataSpecsVersion(PlainTermDataDescriptor):
    """
    Data specifications version number

    Examples: "MIPDS7-2025p10p1"

    The data specifications describe the overall set of data specifications
    used when writing the dataset.
    This version number captures exactly which set of data specifications
    are consistent (or intended to be consistent) with this dataset.
    The DRS values can't contain '.' so we use 'p' instead.
    To go from a DRS value back to a standard version,
    get everything after the hyphen (everything before the hyphen is a prefix)
    then replace "p" with ".".
    Something like, `drs_name.split('-')[-1].replace('p', '.')`.
    (At the moment, exactly what this means is still vague, particularly for CMIP7.
    When it solidifies, more details and examples will be added here.)
    """
