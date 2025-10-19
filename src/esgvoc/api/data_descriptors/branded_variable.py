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

    These components are separated by a separator to create the branded variable.
    [TODO: discuss whether separator should be general or just hard-coded
    to dash to simplify things, particularly validation implemenation
    on the whole system
    (there isn't a free choice for separator,
    the value for branded variable and branded suffix are tightly coupled)
    and avoid speculative generality where we don't have a clear use case for it
    (I see pros and cons, tricky choice).]

    For underlying details and logic, please see
    [Taylor et al., 2025](https://docs.google.com/document/d/19jzecgymgiiEsTDzaaqeLP6pTvLT-NzCMaq-wu-QoOc/edit?pli=1&tab=t.0).
    """  # noqa: E501
