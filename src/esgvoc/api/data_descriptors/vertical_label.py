from esgvoc.api.data_descriptors.data_descriptor import PatternTermDataDescriptor


class VerticalLabel(PatternTermDataDescriptor):
    """
    Vertical label.

    This label provides information about the vertical sampling of a given dataset.
    For a list of allowed values, see
    [TODO think about how to cross-reference to somewhere where people can look up the allowed values,
    e.g. some summary of the values in https://github.com/WCRP-CMIP/WCRP-universe/tree/esgvoc/vertical_label.]

    This label is used as the vertical component of a branded variable's suffix
    (see :py:class:`BrandedSuffix`).
    By definition, the vertical label must be consistent with the branded suffix.
    Vertical labels must not contain the separator used when constructing the branded suffix.
    """

    pass
