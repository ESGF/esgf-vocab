"""
Model (i.e. schema/definition) of the physics index data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


class PhysicsIndex(PatternTermDataDescriptor):
    """
    Label that identifies the physics variant used to produce a dataset

    Examples: "p1", "p2", "p20"

    This label can be used, for example, to distinguish between two simulations,
    one using a model's 'default physics'
    and another using a model's 'other physics scheme',
    which might yield information about how differences in physics within the model affects the simulation.
    The value has no intrinsic meaning within the CVs.
    However, in other external sources (to be confirmed which)
    the meaning of this physics label for a given simulation can be looked up.
    """
