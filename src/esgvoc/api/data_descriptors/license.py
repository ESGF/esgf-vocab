from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class License(PlainTermDataDescriptor):
    """
    License that is/can be used with CMIP data
    """

    kind: str
    """
    Type of the license
    """
    # TODO: validation, should be SPDX identifier
    # http://spdx.org/licenses

    license: str | None
    """
    Plain-text description of the license
    """

    url: str | None
    """
    URL that describes the license
    """
