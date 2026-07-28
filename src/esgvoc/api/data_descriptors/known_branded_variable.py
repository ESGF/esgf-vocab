from typing import List

from pydantic import Field

from esgvoc.api.data_descriptors.area_label import AreaLabel
from esgvoc.api.data_descriptors.coordinate import Coordinate
from esgvoc.api.data_descriptors.data_descriptor import PlainTermDataDescriptor
from esgvoc.api.data_descriptors.frequency import Frequency
from esgvoc.api.data_descriptors.horizontal_label import HorizontalLabel
from esgvoc.api.data_descriptors.realm import Realm
from esgvoc.api.data_descriptors.region import Region
from esgvoc.api.data_descriptors.table import Table
from esgvoc.api.data_descriptors.temporal_label import TemporalLabel
from esgvoc.api.data_descriptors.vertical_label import VerticalLabel

# class KnownBrandedVariable(PlainTermDataDescriptor):
#     """
#     A climate-related quantity or measurement, including information about sampling.
#
#     The concept of a branded variable was introduced in CMIP7.
#     A branded variable is composed of two parts.
#     The first part is the root variable (see :py:class:`Variable`).
#     The second is the suffix (see :py:class:`BrandingSuffix`).
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
    The second is the suffix (see :py:class:`BrandingSuffix`).

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

    # Variable Root context (flattened from hierarchy)
    variable_root_name: str = Field(description="Variable root name, e.g., 'ta'")
    branding_suffix_name: str = Field(description="Branding suffix, e.g., 'tavg-p19-hxy-air'")

    # Variable metadata
    long_name: str = Field(description="Variable long name")
    description: List[str] = Field(default_factory=list, description="Free-text description(s)")
    data_type: str = Field(description="Data type from the DReq variable type attribute")
    dimensions: List[str] = Field(description="NetCDF dimensions")
    coordinates: List[Coordinate | str] = Field(description="Coordinate record names from spatial and temporal shapes")
    cell_methods: List[str] = Field(description="CF cell_methods attribute")
    cell_measures: List[str] = Field(description="CF cell_measures attribute")
    realm: List[Realm | str] = Field(default_factory=list, description="Primary and secondary Earth system realms")
    region: List[Region | str] = Field(default_factory=list, description="Geographical or domain region when exposed by the DReq")

    # Label components (embedded, not references)
    temporal_label: TemporalLabel | str = Field(description="Temporal label, e.g., 'tavg'")
    vertical_label: VerticalLabel | str = Field(description="Vertical label, e.g., 'p19'")
    horizontal_label: HorizontalLabel | str = Field(description="Horizontal label, e.g., 'hxy'")
    area_label: AreaLabel | str = Field(description="Area label, e.g., 'air'")

    # Additional required fields from specifications
    positive_direction: str = Field(default="", description="Positive direction for the variable")

    # Optional fields for legacy projects
    compound_name: list[str] | None = Field(default=None, description="Legacyd name(s)")
    table_id: list[Table | str] | None = Field(default=None, description="Legacy table identifier(s)")
    frequency: list[Frequency | str] | None = Field(default=None, description="Legacy frequency value(s)")
