from typing import Sequence

from esgvoc.api._utils import (get_universe_session,
                               instantiate_pydantic_terms)
from esgvoc.api.search import SearchSettings, create_str_comparison_expression
from esgvoc.core.db.models.universe import DataDescriptor, UTerm
from pydantic import BaseModel
from sqlmodel import Session, select


def _find_terms_in_data_descriptor(data_descriptor_id: str,
                                   term_id: str,
                                   session: Session,
                                   settings: SearchSettings|None) -> Sequence[UTerm]:
    """Settings only apply on the term_id comparison."""
    where_expression = create_str_comparison_expression(field=UTerm.id,
                                                        value=term_id,
                                                        settings=settings)
    statement = select(UTerm).join(DataDescriptor).where(DataDescriptor.id==data_descriptor_id,
                                                         where_expression)
    results = session.exec(statement)
    result = results.all()
    return result


def find_terms_in_data_descriptor(data_descriptor_id: str,
                                  term_id: str,
                                  settings: SearchSettings|None = None) \
                                     -> list[BaseModel]:
    """
    Finds one or more terms in the given data descriptor based on the specified search settings.
    This function performs an exact match on the `data_descriptor_id` and 
    does **not** search for similar or related descriptors.
    The given `term_id` is searched according to the search type specified in 
    the parameter `settings`,
    which allows a flexible matching (e.g., `LIKE` may return multiple results).
    If the parameter `settings` is `None`, this function performs an exact match on the `term_id`.
    If any of the provided ids (`data_descriptor_id` or `term_id`) is not found, the function
    returns an empty list.

    Behavior based on search type:
    - `EXACT` and absence of `settings`: returns zero or one Pydantic term instance in the list.
    - `REGEX`, `LIKE`, `STARTS_WITH` and `ENDS_WITH`: returns zero, one or more Pydantic term \
      instances in the list.

    :param data_descriptor_id: A data descriptor id
    :type data_descriptor_id: str
    :param term_id: A term id to be found
    :type term_id: str
    :param settings: The search settings
    :type settings: SearchSettings|None
    :returns: A list of Pydantic model term instances. Returns an empty list if no matches are found.
    :rtype: list[BaseModel]
    """
    result: list[BaseModel] = list()
    with get_universe_session() as session:
        terms = _find_terms_in_data_descriptor(data_descriptor_id, term_id, session, settings)
        instantiate_pydantic_terms(terms, result)
    return result


def _find_terms_in_universe(term_id: str,
                            session: Session,
                            settings: SearchSettings|None) -> Sequence[UTerm]:
    where_expression = create_str_comparison_expression(field=UTerm.id,
                                                        value=term_id,
                                                        settings=settings)
    statement = select(UTerm).where(where_expression)
    results = session.exec(statement).all()
    return results


def find_terms_in_universe(term_id: str,
                           settings: SearchSettings|None = None) \
                              -> list[BaseModel]:
    """
    Finds one or more terms of the universe.
    The given `term_id` is searched according to the search type specified in 
    the parameter `settings`,
    which allows a flexible matching (e.g., `LIKE` may return multiple results).
    If the parameter `settings` is `None`, this function performs an exact match on the `term_id`.
    Terms are unique within a data descriptor but may have some synonyms in the universe.
    If the provided `term_id` is not found, the function returns an empty list.

    :param term_id: A term id to be found
    :type term_id: str
    :param settings: The search settings
    :type settings: SearchSettings|None
    :returns: A list of Pydantic term instances. Returns an empty list if no matches are found.
    :rtype: list[BaseModel]
    """
    result: list[BaseModel] = list()
    with get_universe_session() as session:
        terms = _find_terms_in_universe(term_id, session, settings)
        instantiate_pydantic_terms(terms, result)
    return result


def _get_all_terms_in_data_descriptor(data_descriptor: DataDescriptor) -> list[BaseModel]:
    result: list[BaseModel] = list()
    instantiate_pydantic_terms(data_descriptor.terms, result)
    return result


def _find_data_descriptors_in_universe(data_descriptor_id: str,
                                       session: Session,
                                       settings: SearchSettings|None) -> Sequence[DataDescriptor]:
    where_expression = create_str_comparison_expression(field=DataDescriptor.id,
                                                        value=data_descriptor_id,
                                                        settings=settings)
    statement = select(DataDescriptor).where(where_expression)
    results = session.exec(statement)
    result = results.all()      
    return result


def get_all_terms_in_data_descriptor(data_descriptor_id: str) \
                                        -> list[BaseModel]:
    """
    Gets all the terms of the given data descriptor.
    This function performs an exact match on the `data_descriptor_id` and does **not** search 
    for similar or related descriptors.
    If the provided `data_descriptor_id` is not found, the function returns an empty list.

    :param data_descriptor_id: A data descriptor id
    :type data_descriptor_id: str
    :returns: a list of Pydantic term instances. Returns an empty list if no matches are found.
    :rtype: list[BaseModel]
    """
    with get_universe_session() as session:
        data_descriptors = _find_data_descriptors_in_universe(data_descriptor_id,
                                                              session,
                                                              None)
        if data_descriptors:
            data_descriptor = data_descriptors[0]
            result = _get_all_terms_in_data_descriptor(data_descriptor)
        else:
            result = list()
    return result


def find_data_descriptors_in_universe(data_descriptor_id: str,
                                      settings: SearchSettings|None = None) \
                                        -> list[dict]:
    """
    Finds one or more data descriptor of the universe, based on the specified search settings.
    The given `data_descriptor_id` is searched according to the search type specified in 
    the parameter `settings`,
    which allows a flexible matching (e.g., `LIKE` may return multiple results).
    If the parameter `settings` is `None`, this function performs an exact match on 
    the `data_descriptor_id`.
    If the provided `data_descriptor_id` is not found, the function returns an empty list.
    
    Behavior based on search type:
    - `EXACT` and absence of `settings`: returns zero or one data descriptor context in the list.
    - `REGEX`, `LIKE`, `STARTS_WITH` and `ENDS_WITH`: returns zero, one or more \
      data descriptor contexts in the list.

    :param data_descriptor_id: A data descriptor id to be found
    :type data_descriptor_id: str
    :param settings: The search settings
    :type settings: SearchSettings|None
    :returns: A list of data descriptor contexts. Returns an empty list if no matches are found.
    :rtype: list[dict]
    """
    result = list()
    with get_universe_session() as session:
        data_descriptors = _find_data_descriptors_in_universe(data_descriptor_id,
                                                              session,
                                                              settings)
        for data_descriptor in data_descriptors:
            result.append(data_descriptor.context)
    return result


def _get_all_data_descriptors_in_universe(session: Session) -> Sequence[DataDescriptor]:
    statement = select(DataDescriptor)
    data_descriptors = session.exec(statement)
    result = data_descriptors.all()
    return result


def get_all_data_descriptors_in_universe() -> list[str]:
    """
    Gets all the data descriptors of the universe.

    :returns: A list of data descriptor ids.
    :rtype: list[str]
    """
    result = list()
    with get_universe_session() as session:
        data_descriptors = _get_all_data_descriptors_in_universe(session)
        for data_descriptor in data_descriptors:
            result.append(data_descriptor.id)
    return result


def get_all_terms_in_universe() -> list[BaseModel]:
    """
    Gets all the terms of the universe.
    Terms are unique within a data descriptor but may have some synonyms in the universe.

    :returns: A list of Pydantic term instances.
    :rtype: list[BaseModel]
    """
    result = list()
    with get_universe_session() as session:
        data_descriptors = _get_all_data_descriptors_in_universe(session)
        for data_descriptor in data_descriptors:
            # Term may have some synonyms within the whole universe.
            terms = _get_all_terms_in_data_descriptor(data_descriptor)
            result.extend(terms)
    return result


if __name__ == "__main__":
    print(find_terms_in_data_descriptor('institution', 'ipsl'))
