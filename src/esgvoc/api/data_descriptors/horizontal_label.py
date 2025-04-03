from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class HorizontalLabel(PlainTermDataDescriptor):
    """
    Horizontal sampling label.

    This label provides information about the horizontal sampling of a given dataset.
    For a list of allowed values, see
    [TODO think about how to cross-reference to somewhere where people can look up the allowed values,
    e.g. some summary of the values in https://github.com/WCRP-CMIP/WCRP-universe/tree/esgvoc/horizontal_label.]

    This label is used as the horizontal component of a branded variable's suffix
    (see :py:class:`BrandedSuffix`).
    By definition, the horizontal label must be consistent with the branded suffix.
    Horizontal labels must not contain the separator used when constructing the branded suffix.
    """

    description: str
    label: str
