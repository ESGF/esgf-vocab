"""
Model (i.e. schema/definition) of the vertical label data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class VerticalLabel(PlainTermDataDescriptor):
    """
    Label that describes a specific vertical sampling approach

    Examples: "h2m", "200hPa", "p19"

    This is set to "u" ("unspecified") when the data has no vertical dimension.
    For underlying details and logic, please see
    [Taylor et al., 2025](https://docs.google.com/document/d/19jzecgymgiiEsTDzaaqeLP6pTvLT-NzCMaq-wu-QoOc/edit?pli=1&tab=t.0).

    This label is used as the area component of a branded variable's suffix
    (see :py:class:`BrandedSuffix`).
    """  # noqa: E501
