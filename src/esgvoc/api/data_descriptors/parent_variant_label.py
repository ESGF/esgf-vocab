"""
Model (i.e. schema/definition) of the parent variant label data descriptor
"""

from esgvoc.api.data_descriptors.variant_label import VariantLabel


class ParentVariantLabel(VariantLabel):
    """
    The variant label of the parent dataset from which this dataset branched

    Examples: "r1i1p1f1", "r2i1p1f1", "r1i1p1f2", "r3i2f2p3"

    Only applies if the dataset has a parent (i.e. branched from another dataset).
    """
