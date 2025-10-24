"""
Model (i.e. schema/definition) of the parent directory data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


# TODO: discuss - I think this would be a helpful thing to put in the file
# so you have at least a chance of finding the parent version.
# If people think it's too hard/annoying, I'll drop it.
class ParentDirectory(PatternTermDataDescriptor):
    """
    The directory (fully DRS resolved) entry of the parent dataset from which this dataset branched

    Examples: "ScenarioMIP/CNRM-CERFACS/CNRM-ESM2-1/ssp245/r1i1p1f2/Ofx/areacello/gn/v20190328"

    Only applies if the dataset has a parent (i.e. branched from another dataset).
    """
