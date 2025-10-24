"""
Model (i.e. schema/definition) of the model component data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class ModelComponent(PlainTermDataDescriptor):
    """
    Model component

    Examples: "AOGCM", "AER", "BGC"

    These terms are intended to help with identifying required components for experiments
    or filtering models based on having common components.
    For example, an aerosol scheme or a circulation model or a biogeochemistry component.
    However, model component is only an approximate term, there is no precise definition
    of whether any given model has or does not have a given component.
    """
