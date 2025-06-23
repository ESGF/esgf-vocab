from esgvoc.api.data_descriptors.data_descriptor import CompositeTermDataDescriptor


class MemberId(CompositeTermDataDescriptor):
    """
    The member_id uniquely identifies a specific model simulation within an experiment. It is created by combining the sub_experiment, which describes the setup or timing of the simulation (like a specific start year), and the variant_label, which details the configuration of the model (including initial conditions, physics, and forcings). Together, they form a code like s1960-r1i1p1f1. This allows users to distinguish between different ensemble members and understand how each run differs from others within the same experiment.
    """

    description: str
