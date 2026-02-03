"""
Model (i.e. schema/definition) of the data specifications data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class DataSpecsVersion(PlainTermDataDescriptor):
    """
    Data specifications version number

    Examples: "MIP-DS7.0.0.0", "01.00.33"

    The data specifications describe the overall set of data specifications
    used when writing the dataset.
    The details of what exactly this means are not always precisely defined
    and can vary across different CMIP projects.
    Please check your specific project's documentation for details.
    """
