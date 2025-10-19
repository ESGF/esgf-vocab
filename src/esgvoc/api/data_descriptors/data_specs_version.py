"""
Model (i.e. schema/definition) of the data specifications data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


class DataSpecsVersion(PatternTermDataDescriptor):
    """
    Data specifications version number

    Examples: "MIP-DS7.0.1.0", "MIP-DS7.1.0.0", "MIP-DS7.2.2.0-rc.1"
    [TODO: I would propose using some separator between the prefix and the semantic version
    so the above would become e.g. MIP-DS7_0.1.0.
    I don't feel super strongly about this though as,
    even when people start with semantic versioning,
    they usually do all sorts of things to break it anyway
    so strict adherence is normally an illusion/not practical
    i.e. no need to pretend we're going to be strict from the start.]

    The data specifications describe the overall set of data specifications
    used when writing the dataset.
    This version number captures exactly which set of data specifications
    are consistent (or intended to be consistent) with this dataset.
    (At the moment, exactly what this means is still vague, particularly for CMIP7.
    When it solidifies, more details and examples will be added here.)

    [TODO: Given that writing a regexp for this will be tricky
    (particularly the versioning bit)
    and perhaps too loose,
    would we consider just having a `ValidatedTermDataDescriptor`
    to support cases where the term is validated by a function
    rather than only allowing regex validation).]
    """
