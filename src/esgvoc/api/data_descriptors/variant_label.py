from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


class VariantLabel(PatternTermDataDescriptor):
    """
    Form that can be used for variant label

    [TODO: fill this out better]
    This takes the form `rXiXpXfX`:

    - `r` represents the realisation of the simulation
    - `i` represents the initialisation of the simulation
    - `p` represents the physics used in the simulation
    - `f` represents the forcing used in the simulation

    Users are directed to the Essential Model Documentation (EMD)
    for details of the meaning of this term for a given simulation/model/dataset.
    """

    description: str
