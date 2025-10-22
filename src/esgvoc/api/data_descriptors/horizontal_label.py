"""
Model (i.e. schema/definition) of the horizontal label data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class HorizontalLabel(PlainTermDataDescriptor):
    """
    Label that describes a specific horizontal sampling approach

    Examples: "hxy", "hs", "hm"

    This is set to "hm" ("horizontal mean") when no other horizontal labels apply.
    For underlying details and logic, please see
    [Taylor et al., 2025](https://docs.google.com/document/d/19jzecgymgiiEsTDzaaqeLP6pTvLT-NzCMaq-wu-QoOc/edit?pli=1&tab=t.0).

    This label is used as the area component of a branded variable's suffix
    (see :py:class:`BrandedSuffix`).
    As a result, horizontal labels must not contain dashes
    (as the dash is used as a separator when constructing the branded suffix).
    By definition, the horizontal label must be consistent with the branded suffix.
    """  # noqa: E501
