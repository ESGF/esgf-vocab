"""
Model (i.e. schema/definition) of the branded variale data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import CompositeTermDataDescriptor


class BrandedVariable(CompositeTermDataDescriptor):
    """
    A climate-related quantity or measurement, including information about sampling.

    Examples: "tas_tavg-h2m-hxy-u", "pr_tpt-u-hxy-u", "ua_tavg-p19-hxy-air"

    The concept of a branded variable was introduced in CMIP7.
    A branded variable is composed of two parts.
    The first part is the root variable (see :py:class:`Variable`).
    The second is the suffix (see :py:class:`BrandedSuffix`).

    For underlying details and logic, please see
    [Taylor et al., 2025](https://docs.google.com/document/d/19jzecgymgiiEsTDzaaqeLP6pTvLT-NzCMaq-wu-QoOc/edit?pli=1&tab=t.0).
    """  # noqa: E501
