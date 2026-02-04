"""
Model (i.e. schema/definition) of the license data descriptor
"""

from pydantic import HttpUrl

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor


class License(PlainTermDataDescriptor):
    """
    License that applies to the dataset

    Examples: "CC-BY-4.0", "CC0-1.0"

    Licenses must be approved by the WIP & CMIP panel
    before they can be used in CMIP exercises.
    """

    spdx_id: str | None
    """
    SPDX license identifier (https://spdx.org/licenses/)
    """
    # Developer note: `id` will not match `spdx_id`
    # exactly because SPDX IDs are not all lowercase,
    # hence we need this extra attribute.

    url: HttpUrl
    """
    URL with details of the full license and other information
    """
