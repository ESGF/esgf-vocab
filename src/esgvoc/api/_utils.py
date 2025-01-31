from typing import Iterable

from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor, DataDescriptorSubSet
import esgvoc.core.constants as api_settings
from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING
from esgvoc.core.db.models.project import PTerm
from esgvoc.core.db.models.universe import UTerm
from sqlmodel import Session

import esgvoc.core.service as service
UNIVERSE_DB_CONNECTION = service.state_service.universe.db_connection


def get_pydantic_class(data_descriptor_id_or_term_type: str) -> type[DataDescriptor]:
    if data_descriptor_id_or_term_type in DATA_DESCRIPTOR_CLASS_MAPPING:
        return DATA_DESCRIPTOR_CLASS_MAPPING[data_descriptor_id_or_term_type]
    else:
        raise ValueError(f"{data_descriptor_id_or_term_type} pydantic class not found")


def get_universe_session() -> Session:

    if UNIVERSE_DB_CONNECTION:
        return UNIVERSE_DB_CONNECTION.create_session()
    else:
        raise RuntimeError('universe connection is not initialized')


def instantiate_pydantic_term(term: UTerm|PTerm,
                              selected_term_fields: list[str]|None = None) -> DataDescriptor:
    type = term.specs[api_settings.TERM_TYPE_JSON_KEY]
    if selected_term_fields:
        subset = DataDescriptorSubSet(id=term.id, type=type)
        for selected_field in selected_term_fields + DataDescriptorSubSet.MANDATORY_TERM_FIELDS:
            setattr(subset, selected_field, term.specs.get(selected_field, None))
        return subset
    else:
        term_class = get_pydantic_class(type)
        return term_class(**term.specs)


def instantiate_pydantic_terms(db_terms: Iterable[UTerm|PTerm],
                               list_to_populate: list[DataDescriptor],
                               selected_term_fields: list[str]|None = None) -> None:
    for db_term in db_terms:
        term = instantiate_pydantic_term(db_term, selected_term_fields)
        list_to_populate.append(term)
