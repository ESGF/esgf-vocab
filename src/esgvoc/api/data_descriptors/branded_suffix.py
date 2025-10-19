"""
Model (i.e. schema/definition) of the branded suffix data descriptor
"""

from esgvoc.api.data_descriptors.data_descriptor import CompositeTermDataDescriptor


class BrandedSuffix(CompositeTermDataDescriptor):
    """
    The suffix of a branded variable.

    Examples: "tavg-h2m-hxy-u", "tpt-u-hxy-u", "tavg-p19-hxy-air"

    A branded variable is composed of two parts.
    The first part is the root variable (see :py:class:`Variable`).
    The second is the suffix, i.e. the component described here.
    The suffix captures all the information
    about the time sampling, horizontal sampling, vertical sampling
    and area masking of the variable.

    The suffix is composed of the following components:

    #. :py:class:`TemporalLabel`
    #. :py:class:`VerticalLabel`
    #. :py:class:`HorizontalLabel`
    #. :py:class:`AreaLabel`

    These components are separated by a separator to create the branded suffix.
    [TODO: discuss whether separator should be general or just hard-coded
    to dash to simplify things, particularly validation implemenation
    on the components and avoid speculative generality
    (I see pros and cons, tricky choice).]

    For underlying details and logic, please see
    [Taylor et al., 2025](https://docs.google.com/document/d/19jzecgymgiiEsTDzaaqeLP6pTvLT-NzCMaq-wu-QoOc/edit?pli=1&tab=t.0).
    """  # noqa: E501
