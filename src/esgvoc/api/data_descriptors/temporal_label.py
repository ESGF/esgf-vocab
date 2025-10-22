"""
Model (i.e. schema/definition) of the temporal label data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class TemporalLabel(PlainTermDataDescriptor):
    """
    Label that describes a specific temporal sampling approach

    Examples: "tavg", "tpt", "tclm"

    This is set to "ti" ("time-independent") when the data has no time axis.
    For underlying details and logic, please see
    [Taylor et al., 2025](https://docs.google.com/document/d/19jzecgymgiiEsTDzaaqeLP6pTvLT-NzCMaq-wu-QoOc/edit?pli=1&tab=t.0).

    This label is used as the area component of a branded variable's suffix
    (see :py:class:`BrandedSuffix`).
    As a result, temporal labels must not contain dashes
    (as the dash is used as a separator when constructing the branded suffix).
    By definition, the temporal label must be consistent with the branded suffix.
    """  # noqa: E501
