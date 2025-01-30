from pydantic import BaseModel

from esgvoc.api.data_descriptors.activity import Activity
from esgvoc.api.data_descriptors.consortium import Consortium
from esgvoc.api.data_descriptors.date import Date
from esgvoc.api.data_descriptors.experiment import Experiment 
from esgvoc.api.data_descriptors.forcing_index import ForcingIndex
from esgvoc.api.data_descriptors.frequency import Frequency
from esgvoc.api.data_descriptors.grid_label import GridLabel 
from esgvoc.api.data_descriptors.initialisation_index import InitialisationIndex 
from esgvoc.api.data_descriptors.institution import Institution
from esgvoc.api.data_descriptors.license import License 
from esgvoc.api.data_descriptors.mip_era import MipEra
from esgvoc.api.data_descriptors.model_component import ModelComponent
from esgvoc.api.data_descriptors.organisation import Organisation 
from esgvoc.api.data_descriptors.physic_index import PhysicIndex
from esgvoc.api.data_descriptors.product import Product
from esgvoc.api.data_descriptors.realisation_index import RealisationIndex 
from esgvoc.api.data_descriptors.realm import Realm
from esgvoc.api.data_descriptors.resolution import Resolution
from esgvoc.api.data_descriptors.source import Source 
from esgvoc.api.data_descriptors.source_type import SourceType 
from esgvoc.api.data_descriptors.sub_experiment import SubExperiment
from esgvoc.api.data_descriptors.table import Table 
from esgvoc.api.data_descriptors.time_range import TimeRange 
from esgvoc.api.data_descriptors.variable import Variable
from esgvoc.api.data_descriptors.variant_label import VariantLabel
from esgvoc.api.data_descriptors.directory_date import DirectoryDate


DATA_DESCRIPTOR_CLASS_MAPPING: dict[str, type[BaseModel]] = {
    "activity": Activity,
    "consortium": Consortium,
    "date": Date,
    "directory_date": DirectoryDate,
    "experiment": Experiment, 
    "forcing_index": ForcingIndex,
    "frequency": Frequency,
    "grid": GridLabel, # DEBUG: the value of the key type for the terms of the DD grid is not consistent.
    "grid-label": GridLabel, # DEBUG: the value of the key type for the terms of the DD grid is not consistent.
    "grid_label": GridLabel, # DEBUG: the value of the key type for the terms of the DD grid is not consistent.
    "initialisation_index": InitialisationIndex, 
    "institution": Institution,
    "license": License,
    "mip_era": MipEra,
    "model_component": ModelComponent,
    "organisation": Organisation, 
    "physic_index": PhysicIndex,
    "product": Product,
    "realisation_index": RealisationIndex ,
    "realm": Realm,
    "resolution": Resolution,
    "source": Source, 
    "source_type": SourceType, 
    "sub_experiment": SubExperiment,
    "table" : Table,
    "time_range": TimeRange,
    "variable": Variable,
    "real": Variable, # DEBUG: key type should be the pydantic class for the terms of DD variable!
    "integer": Variable, # DEBUG: key type should be the pydantic class for the terms of DD variable!
    "variant_label": VariantLabel
}
