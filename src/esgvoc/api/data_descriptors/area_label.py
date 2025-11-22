"""
Model (i.e. schema/definition) of the area label data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class AreaLabel(PlainTermDataDescriptor):
    """
    Label that describes a specific area sampling approach

    Examples: "lnd", "air", "sea", "u"

    This label is used as the area component of a branded variable's suffix
    (see :py:class:`BrandedSuffix`).
    """

    cf_area_type: str | None
    """
    CF-conventions area type
    (https://cfconventions.org/Data/area-type-table/current/build/area-type-table.html).

    This is set to "u" ("unmasked") when all areas are sampled
    i.e. no mask is applied to the data.
    For underlying details and logic, please see
    [Taylor et al., 2025](https://docs.google.com/document/d/19jzecgymgiiEsTDzaaqeLP6pTvLT-NzCMaq-wu-QoOc/edit?pli=1&tab=t.0).

    If `None`, there is no CF-conventions area type
    associated with this area label.
    """  # noqa: E501
