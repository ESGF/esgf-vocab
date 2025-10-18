"""
Model (i.e. schema/definition) of the vertical label data descriptor
"""

from pydantic import field_validator

from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


class VerticalLabel(PatternTermDataDescriptor):
    """
    Label that describes a specific vertical sampling approach

    Examples: "h2m", "200hPa", "p19"

    This is set to "u" ("unspecified") when the data has no vertical dimension.
    For underlying details and logic, please see
    [Taylor et al., 2025](https://docs.google.com/document/d/19jzecgymgiiEsTDzaaqeLP6pTvLT-NzCMaq-wu-QoOc/edit?pli=1&tab=t.0).

    This label is used as the area component of a branded variable's suffix
    (see :py:class:`BrandedSuffix`).
    As a result, vertical labels must not contain dashes
    (as the dash is used as a separator when constructing the branded suffix).
    By definition, the vertical label must be consistent with the branded suffix.
    """  # noqa: E501

    # Ensure no dash in the drs name
    # as this would cause the branding suffix construction to explode.
    # [TODO: check with Laurent whether there is already a fancier
    # mechanism for ensuring that the separator doesn't appear in any of the drs names
    # for the components.]
    # Could introduce a BrandedSuffixComponent sub-class
    # to avoid duplicating this code four times,
    # but more layers in the sub-classing hierarchy, urgh...
    @field_validator("drs_name")
    def name_must_not_contain_dash(cls, v):
        if "-" in v:
            msg = f"`drs_name` for {cls} must not contain a dash. Received: {v}"
            raise ValueError(msg)

        return v
