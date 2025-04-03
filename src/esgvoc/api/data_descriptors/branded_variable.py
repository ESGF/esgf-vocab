from esgvoc.api.data_descriptors.data_descriptor import CompositeTermDataDescriptor


class BrandedVariable(CompositeTermDataDescriptor):
    """
    A climate-related quantity or measurement, including information about sampling.

    The concept of a branded variable was introduced in CMIP7.
    A branded variable is composed of two parts.
    The first part is the root variable (see :py:class:`Variable`).
    The second is the suffix (see :py:class:`BrandedSuffix`).

    For further details on the development of branded variables,
    see [this paper draft](https://docs.google.com/document/d/19jzecgymgiiEsTDzaaqeLP6pTvLT-NzCMaq-wu-QoOc/edit?pli=1&tab=t.0).
    """

    description: str
