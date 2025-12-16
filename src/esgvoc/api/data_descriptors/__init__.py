# EMD v1.0: horizontal_grid.py removed (v0.993 deprecated)
# Use EMD_models.horizontal_computational_grid instead
from esgvoc.api.data_descriptors.vertical_label import VerticalLabel
from esgvoc.api.data_descriptors.variant_label import VariantLabel
from esgvoc.api.data_descriptors.variable import Variable
from esgvoc.api.data_descriptors.tracking_id import TrackingId
from esgvoc.api.data_descriptors.title import Title
from esgvoc.api.data_descriptors.time_range import TimeRange
from esgvoc.api.data_descriptors.temporal_label import TemporalLabel
from esgvoc.api.data_descriptors.table import Table
from esgvoc.api.data_descriptors.sub_experiment import SubExperiment
from esgvoc.api.data_descriptors.source_type import SourceType
from esgvoc.api.data_descriptors.source import Source
from esgvoc.api.data_descriptors.EMD_models.resolution import EMDResolution
from esgvoc.api.data_descriptors.resolution import Resolution
from esgvoc.api.data_descriptors.region import Region
from esgvoc.api.data_descriptors.regex import Regex
from esgvoc.api.data_descriptors.EMD_models.reference import Reference
from esgvoc.api.data_descriptors.realm import Realm
from esgvoc.api.data_descriptors.realization_index import RealizationIndex
from esgvoc.api.data_descriptors.publication_status import PublicationStatus
from esgvoc.api.data_descriptors.product import Product
from esgvoc.api.data_descriptors.physics_index import PhysicsIndex
from esgvoc.api.data_descriptors.organisation import Organisation
from esgvoc.api.data_descriptors.obs_type import ObsType
from esgvoc.api.data_descriptors.nominal_resolution import NominalResolution

# EMD v1.0: native_vertical_grid_new and native_horizontal_grid_new removed
# Use EMD_models.vertical_computational_grid and EMD_models.horizontal_computational_grid instead
from esgvoc.api.data_descriptors.models_test.models import CompositeTermDDex, PatternTermDDex, PlainTermDDex
from esgvoc.api.data_descriptors.EMD_models.model import Model
from esgvoc.api.data_descriptors.EMD_models.model_component import EMDModelComponent
from esgvoc.api.data_descriptors.model_component import ModelComponent
from esgvoc.api.data_descriptors.mip_era import MipEra
from esgvoc.api.data_descriptors.member_id import MemberId
from esgvoc.api.data_descriptors.license import License
from esgvoc.api.data_descriptors.known_branded_variable import KnownBrandedVariable
from esgvoc.api.data_descriptors.institution import Institution
from esgvoc.api.data_descriptors.initialization_index import InitializationIndex
from esgvoc.api.data_descriptors.horizontal_label import HorizontalLabel
from esgvoc.api.data_descriptors.activity import Activity
from esgvoc.api.data_descriptors.archive import Archive
from esgvoc.api.data_descriptors.area_label import AreaLabel
from esgvoc.api.data_descriptors.branded_suffix import BrandedSuffix
from esgvoc.api.data_descriptors.branded_variable import BrandedVariable
from esgvoc.api.data_descriptors.EMD_models.calendar import Calendar
from esgvoc.api.data_descriptors.citation_url import CitationUrl
from esgvoc.api.data_descriptors.EMD_models.component_type import ComponentType
from esgvoc.api.data_descriptors.contact import Contact
from esgvoc.api.data_descriptors.conventions import Convention
from esgvoc.api.data_descriptors.creation_date import CreationDate
from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
from esgvoc.api.data_descriptors.data_specs_version import DataSpecsVersion
from esgvoc.api.data_descriptors.date import Date
from esgvoc.api.data_descriptors.directory_date import DirectoryDate
from esgvoc.api.data_descriptors.drs_specs import DRSSpecs

# # Import new EMD CV models
# from esgvoc.api.data_descriptors.EMD import (
#     CellVariableType,
#     GridType,
#     HorizontalUnits,
#     MeshLocation,
#     TruncationMethod,
#     VerticalUnits,
# )
from esgvoc.api.data_descriptors.experiment import Experiment
from esgvoc.api.data_descriptors.forcing_index import ForcingIndex
from esgvoc.api.data_descriptors.frequency import Frequency
from esgvoc.api.data_descriptors.further_info_url import FurtherInfoUrl
from esgvoc.api.data_descriptors.grid import Grid
from esgvoc.api.data_descriptors.EMD_models.coordinate import Coordinate

# Import EMD v1.0 CV models from EMD_models (Section 7)
from esgvoc.api.data_descriptors.EMD_models.arrangement import Arrangement
from esgvoc.api.data_descriptors.EMD_models.cell_variable_type import CellVariableType
from esgvoc.api.data_descriptors.EMD_models.grid_mapping import GridMapping
from esgvoc.api.data_descriptors.EMD_models.grid_region import GridRegion
from esgvoc.api.data_descriptors.EMD_models.grid_type import GridType
from esgvoc.api.data_descriptors.EMD_models.temporal_refinement import TemporalRefinement as EMDTemporalRefinement
from esgvoc.api.data_descriptors.EMD_models.truncation_method import TruncationMethod
from esgvoc.api.data_descriptors.EMD_models.vertical_units import VerticalUnits

# from esgvoc.api.data_descriptors.grid_label import GridLabel
# EMD v1.0: Old horizontal_grid_* files removed (v0.993 deprecated)
# EMD v1.0: vertical_grid.py removed (v0.993 deprecated)
# Use EMD_models for all EMD v1.0 CV classes

# Model rebuilding to handle cross-links
# Needs Experiment links made
from esgvoc.api.data_descriptors.activity import ActivityCMIP7

ActivityCMIP7.model_rebuild()

DATA_DESCRIPTOR_CLASS_MAPPING: dict[str, type[DataDescriptor]] = {
    "PlainTermDDex": PlainTermDDex,
    "PatternTermDDex": PatternTermDDex,
    "CompositeTermDDex": CompositeTermDDex,
    "activity": Activity,
    "date": Date,
    "directory_date": DirectoryDate,
    "experiment": Experiment,
    "forcing_index": ForcingIndex,
    "frequency": Frequency,
    # "grid": GridLabel,  # Universe
    # "grid_label": GridLabel,  # cmip6, cmip6plus
    "grid": Grid,
    "initialization_index": InitializationIndex,
    "institution": Institution,
    "license": License,
    "mip_era": MipEra,
    "model_component": ModelComponent,
    "organisation": Organisation,
    "physics_index": PhysicsIndex,
    "product": Product,
    "realization_index": RealizationIndex,
    "realm": Realm,
    "resolution": Resolution,
    "source": Source,
    "source_type": SourceType,
    "sub_experiment": SubExperiment,
    "table": Table,
    "time_range": TimeRange,
    "variable": Variable,
    "variant_label": VariantLabel,
    "area_label": AreaLabel,
    "temporal_label": TemporalLabel,
    "vertical_label": VerticalLabel,
    "horizontal_label": HorizontalLabel,
    "branded_suffix": BrandedSuffix,
    "branded_variable": BrandedVariable,
    "publication_status": PublicationStatus,
    "known_branded_variable": KnownBrandedVariable,
    "calendar_new": Calendar,
    "calendar": Calendar,
    "component_type_new": ComponentType,
    "component_type": ComponentType,
    "grid_arrangement": Arrangement,  # EMD v1.0
    "grid_coordinate_new": Coordinate,
    "coordinate": Coordinate,
    "grid_mapping": GridMapping,  # EMD v1.0
    "model_component_new": EMDModelComponent,
    "model_component": EMDModelComponent,  # EMD v1.0
    "model_new": Model,
    "model": Model,  # EMD v1.0
    # EMD v0.993 files removed - use EMD_models for v1.0
    # "native_horizontal_grid_new": removed
    # "horizontal_grid": removed (use EMD_models.HorizontalComputationalGrid)
    # "native_vertical_grid_new": removed
    # "vertical_grid": removed (use EMD_models.VerticalComputationalGrid)
    "reference_new": Reference,
    "reference": Reference,  # EMD v1.0
    "resolution_new": EMDResolution,
    # EMD v1.0 (note: different from general Resolution)
    "resolution": EMDResolution,
    "unit_new": VerticalUnits,  # EMD v1.0
    "temporal_refinement": EMDTemporalRefinement,  # EMD v1.0
    "grid_type": GridType,  # EMD v1.0
    "cell_variable_type": CellVariableType,  # EMD v1.0
    "truncation_method": TruncationMethod,  # EMD v1.0
    "vertical_units": VerticalUnits,  # EMD v1.0
    "grid_region": GridRegion,  # EMD v1.0
    "data_specs_version": DataSpecsVersion,
    "further_info_url": FurtherInfoUrl,
    "tracking_id": TrackingId,
    "creation_date": CreationDate,
    "conventions": Convention,
    "title": Title,
    "contact": Contact,
    "region": Region,
    "member_id": MemberId,
    "obs_type": ObsType,  # obs4Mips
    "regex": Regex,
    "citation_url": CitationUrl,
    "archive": Archive,
    "drs_specs": DRSSpecs,
    "nominal_resolution": NominalResolution,
    # EMD v0.993 files - mapped to EMD v1.0 classes
    "horizontal_grid_arrangement": Arrangement,  # EMD v1.0
    "horizontal_grid_cell_variable_type": CellVariableType,  # EMD v1.0
    "horizontal_grid_mapping": GridMapping,  # EMD v1.0
    "horizontal_grid_region": GridRegion,  # EMD v1.0
    "horizontal_grid_temporal_refinement": EMDTemporalRefinement,  # EMD v1.0
    "horizontal_grid_truncation_method": TruncationMethod,  # EMD v1.0
    "horizontal_grid_type": GridType,  # EMD v1.0
}
