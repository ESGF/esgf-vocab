"""
Model (i.e. schema/definition) of the organisation data descriptor

Note: this is kept for legacy reasons,
but is redundant given we have :py:class:`Contributor` and :py:class:`ContributorMember`.
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class Organisation(PlainTermDataDescriptor):
    pass
