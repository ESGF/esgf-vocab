"""
Model (i.e. schema/definition) of the realisation index data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


class RealizationIndex(PatternTermDataDescriptor):
    """
    Label that identifies the realisation variant used to produce a dataset

    Examples: "r1", "r2", "r23"

    This label can be used to distinguish between two simulations
    that are equally likely but differ only due to stochastic variations.
    These differences can be purely stochastic
    (i.e. arising simply from stochastic variations when re-running the same simulation,
    even keeping all other conditions the same)
    or arise from differences in initial conditions
    e.g. starting/branching from different points in a control run/parent experiment.
    The value has no intrinsic meaning within the CVs.
    However, in other external sources (to be confirmed which)
    the meaning of this realisation label for a given simulation can be looked up.
    """
