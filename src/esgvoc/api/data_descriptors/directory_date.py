"""
Model (i.e. schema/definition) of the directory date data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


class DirectoryDate(PatternTermDataDescriptor):
    """
    Date included as part of data paths

    Examples: "20240513", "20230202", "20250109"

    In practice, this acts as a version ID for the dataset.
    For most CMIP projects, it is the only version ID.
    For some (e.g. input4MIPs), it is another (redundant) version ID
    on top of other versioning conventions used by the project.

    More detail than you could ever want on why this only in the directory,
    and not a file attribute, can be found in
    https://github.com/WCRP-CMIP/CMIP7-CVs/issues/172.
    """
