from pydantic import BaseModel

from sqlmodel import select, Session

import cmipld.db as db
import cmipld.utils.functions as functions
from cmipld.models.sqlmodel.univers import UTerm, DataDescriptor
from cmipld.utils.functions import SearchSettings, create_str_comparison_expression

############## DEBUG ##############
# TODO: to be deleted.
# The following instructions are only temporary as long as a complet data managment will be implmented.
UNIVERS_DB_CONNECTION = db.DBConnection(db.UNIVERS_DB_FILE_PATH, 'univers', False)
###################################


def _get_all_data_descriptors(session: Session) -> list[DataDescriptor]:
    statement = select(DataDescriptor)
    data_descriptors = session.exec(statement)
    result = data_descriptors.all()
    return result


def _get_data_descriptor(data_descriptor_id: str, settings: SearchSettings, session: Session) -> list[DataDescriptor]:
    where_expression = create_str_comparison_expression(field=DataDescriptor.id,
                                                        value=data_descriptor_id,
                                                        settings=settings)
    statement = select(DataDescriptor).where(where_expression)
    results = session.exec(statement).all()
    return results


def _get_terms(data_descriptor: DataDescriptor) -> list[type[BaseModel]]:
    result = list()
    term_class = functions.get_pydantic_class(data_descriptor.id)
    for term in data_descriptor.terms:
        result.append(term_class(**term.specs))
    return result


# Settings only apply on the term_id comparison.
def _get_term(data_descriptor_id: str, term_id: str, settings: SearchSettings, session: Session) -> list[UTerm]:
    where_expression = create_str_comparison_expression(field=UTerm.id,
                                                        value=term_id,
                                                        settings=settings)
    statement = select(UTerm).join(DataDescriptor).where(DataDescriptor.id==data_descriptor_id,
                                                         where_expression)
    results = session.exec(statement).all()
    return results


# Returns dict[term id: term pydantic instance]. Len > 1 depending on settings type of search.
# Settings only apply on the term_id comparison.
def get_term_in_data_descriptor(data_descriptor_id: str, term_id: str, settings: SearchSettings = SearchSettings()) -> dict[str: type[BaseModel]]:
    with UNIVERS_DB_CONNECTION.create_session() as session:
        result = dict()
        terms = _get_term(data_descriptor_id, term_id, settings, session)
        term_class = functions.get_pydantic_class(data_descriptor_id)
        for term in terms:
            result[term.id] = term_class(**term.specs)
    return result


# Returns dict[data descriptor id: [term id: term pydantic instance]]. Len > 1 depending on settings type of search.
def get_all_terms_in_data_descriptor(data_descriptor_id: str, settings: SearchSettings = SearchSettings()) -> dict[str, dict[str, type[BaseModel]]]:
    result = dict()
    with UNIVERS_DB_CONNECTION.create_session() as session:
        data_descriptors = _get_data_descriptor(data_descriptor_id, settings, session)
        for data_descriptor in data_descriptors:
            result[data_descriptor.id] = dict()
            terms = _get_terms(data_descriptor)
            for term in terms:
                result[data_descriptor.id][term.id] = term
    return result


def get_all_data_descriptors() -> dict[str, dict]:
    with UNIVERS_DB_CONNECTION.create_session() as session:
        data_descriptors = _get_all_data_descriptors(session)
        result = dict()
        for data_descriptor in data_descriptors:
            result[data_descriptor.id] = data_descriptor.context
    return result


def get_all_terms() -> dict[str, dict[str, type[BaseModel]]]:
    with UNIVERS_DB_CONNECTION.create_session() as session:
        data_descriptors = _get_all_data_descriptors(session)
        result = dict()
        for data_descriptor in data_descriptors:
            # Term may be sysnonym within the whole univers.
            result[data_descriptor.id] = dict()
            terms = _get_terms(data_descriptor)
            for term in terms:
                result[data_descriptor.id][term.id] = term
    return result