"""
Model (i.e. schema/definition) of the external variables data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


class ExternalVariables(PatternTermDataDescriptor):
    """
    Variables relevant to a dataset that are stored external to the dataset

    Examples: "areacella", "areacella sftlf", "areacello sftof", "volcello"

    Governed by CF-conventions
    (https://cfconventions.org/cf-conventions/cf-conventions.html#external-variables).
   `cell_measures` must also be provided when `external_variables` is specified.
    """
