"""
Model (i.e. schema/definition) of the area label data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class AreaLabel(PlainTermDataDescriptor):
    """
    Label that describes a specific area sampling approach

    Examples: "lnd", "air", "sea", "u"

    This is set to "u" ("unmasked") when all areas are sampled
    i.e. no mask is applied to the data.
    For underlying details and logic, please see
    [Taylor et al., 2025](https://docs.google.com/document/d/19jzecgymgiiEsTDzaaqeLP6pTvLT-NzCMaq-wu-QoOc/edit?pli=1&tab=t.0).

    This label is used as the area component of a branded variable's suffix
    (see :py:class:`BrandedSuffix`).
    By definition, the area label must be consistent with the branded suffix.
    Area labels must not contain dashes
    (as the dash is used as a separator when constructing the branded suffix).
    """  # noqa: E501

    # TODO: add validation for not containing dashes in `drs_name`,
    # although my pydantic is not good enough to know how to do
    # that without looking it up (which I'm not going to do right now).

    description: str
    """
    Description of the meaning of this area label
    """

    label: str
    # TODO: remove? `drs_name` or `id` should be used here instead?
