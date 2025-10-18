"""
Model (i.e. schema/definition) of the temporal label data descriptor
"""

from pydantic import field_validator

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
