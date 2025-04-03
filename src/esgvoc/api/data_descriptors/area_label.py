from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class AreaLabel(PlainTermDataDescriptor):
    """
    Area sampling label.

    This label provides information about the area sampling of a given dataset.
    For a list of allowed values, see
    [TODO think about how to cross-reference to somewhere where people can look up the allowed values,
    e.g. some summary of the values in https://github.com/WCRP-CMIP/WCRP-universe/tree/esgvoc/area_label.]

    This label is used as the area component of a branded variable's suffix
    (see :py:class:`BrandedSuffix`).
    By definition, the area label must be consistent with the branded suffix.
    area labels must not contain dashes
    (as the dash is used as a separator when constructing the branded suffix).
    """

    description: str
    label: str
