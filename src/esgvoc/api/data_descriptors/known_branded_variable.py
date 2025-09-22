from typing import Any, Dict, List, Optional

from pydantic import Field

from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor

#
# class KnownBrandedVariable(PlainTermDataDescriptor):
#     """
#     A climate-related quantity or measurement, including information about sampling.
#
#     The concept of a branded variable was introduced in CMIP7.
#     A branded variable is composed of two parts.
#     The first part is the root variable (see :py:class:`Variable`).
#     The second is the suffix (see :py:class:`BrandedSuffix`).
#
#     For further details on the development of branded variables,
#     see [this paper draft](https://docs.google.com/document/d/19jzecgymgiiEsTDzaaqeLP6pTvLT-NzCMaq-wu-QoOc/edit?pli=1&tab=t.0).
#     """
#
#     description: str
#     dimensions: list[str] = Field(default_factory=list)
#     cell_methods: str
#     variable: str
#     label: str
#


class KnownBrandedVariable(PlainTermDataDescriptor):
    """
    A climate-related quantity or measurement, including information about sampling.

    The concept of a branded variable was introduced in CMIP7.
    A branded variable is composed of two parts.
    The first part is the root variable (see :py:class:`Variable`).
    The second is the suffix (see :py:class:`BrandedSuffix`).

    For further details on the development of branded variables,
    see [this paper draft](https://docs.google.com/document/d/19jzecgymgiiEsTDzaaqeLP6pTvLT-NzCMaq-wu-QoOc/edit?pli=1&tab=t.0).
    """

    # # ESGVoc required fields
    # id: str = Field(description="Unique identifier, e.g., 'ta_tavg-p19-hxy-air'")
    # type: str = Field(default="branded_variable", description="ESGVoc type identifier")
    # drs_name: str = Field(description="DRS name, same as id")
    # => already in PlainTermDataDescriptor

    # CF Standard Name context (flattened from hierarchy)
    cf_standard_name: str = Field(description="CF standard name, e.g., 'air_temperature'")
    cf_units: str = Field(description="CF standard units, e.g., 'K'")
    cf_sn_status: str = Field(description="CF standard name status, e.g., 'approved'")

    # Variable Root context (flattened from hierarchy)
    variable_root_name: str = Field(description="Variable root name, e.g., 'ta'")
    var_def_qualifier: str = Field(default="", description="Variable definition qualifier")
    branding_suffix_name: str = Field(description="Branding suffix, e.g., 'tavg-p19-hxy-air'")

    # Variable metadata
    description: str = Field(description="Human-readable description")
    dimensions: List[str] = Field(description="NetCDF dimensions")
    cell_methods: str = Field(default="", description="CF cell_methods attribute")
    cell_measures: str = Field(default="", description="CF cell_measures attribute")
    history: str = Field(default="", description="Processing history")
    realm: str = Field(description="Earth system realm, e.g., 'atmos'")

    # Label components (embedded, not references)
    temporal_label: str = Field(description="Temporal label, e.g., 'tavg'")
    vertical_label: str = Field(description="Vertical label, e.g., 'p19'")
    horizontal_label: str = Field(description="Horizontal label, e.g., 'hxy'")
    area_label: str = Field(description="Area label, e.g., 'air'")

    # Status
    bn_status: str = Field(description="Branded variable status, e.g., 'accepted'")

    # Additional required fields from specifications
    positive_direction: str = Field(default="", description="Positive direction for the variable")
