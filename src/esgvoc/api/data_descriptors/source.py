"""
Model (i.e. schema/definition) of the source descriptor
"""

from esgvoc.api.data_descriptors.contributor import Contributor
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
from esgvoc.api.data_descriptors.model_component_new import EMDModelComponent


class Source(PlainTermDataDescriptor):
    """
    Source of the dataset

    Examples: "CanESM6-MR", "CR-CMIP-1-0-0"

    The more precise meaning of source depends on the kind of dataset this is.
    For model output, 'source' refers to a numerical representations of the Earth's climate system.
    This source is the model which was used to generate the dataset.
    Such models simulate the interactions between the atmosphere, oceans, land surface, and ice.
    They are based on fundamental physical, chemical, and biological processes
    and are used to understand past, present, and future climate conditions.
    Each source or model is typically associated with a specific research institution, center, or group.
    For instance, models like 'EC-Earth' are developed by a consortium of European institutes,
    while 'GFDL-CM4' is developed by the Geophysical Fluid Dynamics Laboratory (GFDL) in the United States.

    For model inputs i.e. forcings, the 'source' is a unique identifier
    for the group that produced the data and its version.
    This is a different convention from almost all other cases
    (which really muddies the meaning of the term).
    """

    label: str
    """
    Label to use for this source

    Unlike the `drs_name`, this can contain any characters
    """

    label_extended: str
    """
    Extended label to use for this source

    Unlike the `drs_name`, this can contain any characters.
    If desired, it can include lots of verbose information
    (unlike `label`, which should be more terse).
    It can also just be the same as `label`
    if the person registering the source wishes.
    """

    contributors: list[Contributor]
    """
    Contributor(s) using this source

    Using is a bit vaguely defined, but in practice it is the contributor(s)
    that submit data using this source.
    """

    model_components: list[EMDModelComponent]
    """
    Model components

    If this source is not a model, this can/will just be an empty list.
    """

    @property
    def source(self) -> str:
        """
        Source label as used by CMOR
        """
        raise NotImplementedError
        # Something like:
        # label (release year from EMD if known):
        # (for each model component)\n component: component name (description)
