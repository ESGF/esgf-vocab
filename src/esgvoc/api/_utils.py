from typing import Iterable

from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
import esgvoc.core.constants as api_settings
from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING
from esgvoc.core.db.models.project import PTerm
from esgvoc.core.db.models.universe import UTerm
from pydantic import BaseModel
from sqlmodel import Session

import esgvoc.core.service as service
UNIVERSE_DB_CONNECTION = service.state_service.universe.db_connection


def get_pydantic_class(data_descriptor_id_or_term_type: str) -> type[BaseModel]:
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
                              selected_fields: Iterable[str]|None = None) -> BaseModel:
    type = term.specs[api_settings.TERM_TYPE_JSON_KEY]
    if selected_fields:
        result = DataDescriptor(id=term.id, type=type)
        for selected_field in selected_fields:
            setattr(object=result, name=selected_field, value=term.specs.get(selected_field, None))
    else:
        term_class = get_pydantic_class(type)
        result = term_class(**term.specs)
    return result


def instantiate_pydantic_terms(db_terms: Iterable[UTerm|PTerm],
                               list_to_populate: list[BaseModel],
                               selected_fields: Iterable[str]|None = None) -> None:
    for db_term in db_terms:
        term = instantiate_pydantic_term(db_term, selected_fields)
        list_to_populate.append(term)
