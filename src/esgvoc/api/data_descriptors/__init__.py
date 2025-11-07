from esgvoc.api.data_descriptors.activity import Activity
from esgvoc.api.data_descriptors.archive import Archive
from esgvoc.api.data_descriptors.area_label import AreaLabel
from esgvoc.api.data_descriptors.branded_suffix import BrandedSuffix
from esgvoc.api.data_descriptors.branded_variable import BrandedVariable
from esgvoc.api.data_descriptors.calendar_new import Calendar
from esgvoc.api.data_descriptors.component_type_new import ComponentType
from esgvoc.api.data_descriptors.citation_url import CitationUrl
from esgvoc.api.data_descriptors.consortium import Consortium
from esgvoc.api.data_descriptors.contact import Contact
from esgvoc.api.data_descriptors.conventions import Convention
from esgvoc.api.data_descriptors.creation_date import CreationDate
from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
from esgvoc.api.data_descriptors.data_specs_version import DataSpecsVersion
from esgvoc.api.data_descriptors.date import Date
from esgvoc.api.data_descriptors.directory_date import DirectoryDate
from esgvoc.api.data_descriptors.experiment import Experiment
from esgvoc.api.data_descriptors.forcing_index import ForcingIndex
from esgvoc.api.data_descriptors.frequency import Frequency
from esgvoc.api.data_descriptors.grid_arrangement_new import GridArrangement
from esgvoc.api.data_descriptors.grid_coordinate_new import Coordinate
from esgvoc.api.data_descriptors.further_info_url import FurtherInfoUrl
from esgvoc.api.data_descriptors.grid_label import GridLabel
from esgvoc.api.data_descriptors.grid_mapping_new import GridMapping
from esgvoc.api.data_descriptors.horizontal_label import HorizontalLabel
from esgvoc.api.data_descriptors.initialisation_index import InitialisationIndex
from esgvoc.api.data_descriptors.institution import Institution
from esgvoc.api.data_descriptors.known_branded_variable import KnownBrandedVariable
from esgvoc.api.data_descriptors.license import License
from esgvoc.api.data_descriptors.member_id import MemberId
from esgvoc.api.data_descriptors.mip_era import MipEra
from esgvoc.api.data_descriptors.model_component import ModelComponent
from esgvoc.api.data_descriptors.model_component_new import EMDModelComponent
from esgvoc.api.data_descriptors.model_new import Model
from esgvoc.api.data_descriptors.native_horizontal_grid_new import NativeHorizontalGrid
from esgvoc.api.data_descriptors.native_vertical_grid_new import NativeVerticalGrid
from esgvoc.api.data_descriptors.obs_type import ObsType
from esgvoc.api.data_descriptors.organisation import Organisation
from esgvoc.api.data_descriptors.physic_index import PhysicIndex
from esgvoc.api.data_descriptors.product import Product
from esgvoc.api.data_descriptors.publication_status import PublicationStatus
from esgvoc.api.data_descriptors.realisation_index import RealisationIndex
from esgvoc.api.data_descriptors.realm import Realm
from esgvoc.api.data_descriptors.reference_new import Reference
from esgvoc.api.data_descriptors.regex import Regex
from esgvoc.api.data_descriptors.region import Region
from esgvoc.api.data_descriptors.resolution import Resolution
from esgvoc.api.data_descriptors.resolution_new import EMDResolution
from esgvoc.api.data_descriptors.source import Source
from esgvoc.api.data_descriptors.source_type import SourceType
from esgvoc.api.data_descriptors.sub_experiment import SubExperiment
from esgvoc.api.data_descriptors.table import Table
from esgvoc.api.data_descriptors.temporal_label import TemporalLabel
from esgvoc.api.data_descriptors.time_range import TimeRange
from esgvoc.api.data_descriptors.unit_new import Unit
from esgvoc.api.data_descriptors.title import Title
from esgvoc.api.data_descriptors.tracking_id import TrackingId
from esgvoc.api.data_descriptors.variable import Variable
from esgvoc.api.data_descriptors.variant_label import VariantLabel
from esgvoc.api.data_descriptors.vertical_label import VerticalLabel

DATA_DESCRIPTOR_CLASS_MAPPING: dict[str, type[DataDescriptor]] = {
    "activity": Activity,
    "consortium": Consortium,
    "date": Date,
    "directory_date": DirectoryDate,
    "experiment": Experiment,
    "forcing_index": ForcingIndex,
    "frequency": Frequency,
    "grid": GridLabel,  # Universe
    "grid_label": GridLabel,  # cmip6, cmip6plus
    "initialisation_index": InitialisationIndex,
    "institution": Institution,
    "license": License,
    "mip_era": MipEra,
    "model_component": ModelComponent,
    "organisation": Organisation,
    "physic_index": PhysicIndex,
    "product": Product,
    "realisation_index": RealisationIndex,
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
    "component_type_new": ComponentType,
    "grid_arrangement_new": GridArrangement,
    "grid_coordinate_new": Coordinate,
    "grid_mapping_new": GridMapping,
    "model_component_new": EMDModelComponent,
    "model_new": Model,
    "native_horizontal_grid_new": NativeHorizontalGrid,
    "horizontal_grid": NativeHorizontalGrid,
    "native_vertical_grid_new": NativeVerticalGrid,
    "vertical_grid": NativeVerticalGrid,
    "reference_new": Reference,
    "resolution_new": EMDResolution,
    "unit_new": Unit,
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
}
