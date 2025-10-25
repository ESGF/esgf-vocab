"""
Model (i.e. schema/definition) of the forcing index data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


class VariantLabel(PatternTermDataDescriptor):
    """
    The variant which provides information about how a dataset was created

    Examples: "r1i1p1f1", "r2i2p2f1", "r1i198001p1f1", "r1i198001ap1f1", "r1i199001bp1f1"

    Really, this should be a composite term.
    However, as there is no separator between the parts, it has to be a pattern term
    (at least at the moment).

    As of the latest round of CMIP,
    the variant label is usually composed of the following components:

    #. :py:class:`RealizationIndex`
    #. :py:class:`InitializationIndex`
    #. :py:class:`PhysicsIndex`
    #. :py:class:`ForcingIndex`
    """
