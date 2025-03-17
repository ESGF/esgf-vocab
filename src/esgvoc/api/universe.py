from typing import Any, Iterable, Sequence

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, col, select

from esgvoc.api._utils import (APIException, Item, execute_match_statement,
                               generate_matching_condition,
                               get_universe_session, instantiate_pydantic_term,
                               instantiate_pydantic_terms)
from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
from esgvoc.api.search import SearchSettings, _create_str_comparison_expression
from esgvoc.core.db.models.universe import (UDataDescriptor,
                                            UDataDescriptorFTS5, UTerm,
                                            UTermFTS5)


def _find_terms_in_data_descriptor(data_descriptor_id: str,
                                   term_id: str,
                                   session: Session,
                                   settings: SearchSettings | None) -> Sequence[UTerm]:
    """Settings only apply on the term_id comparison."""
    where_expression = _create_str_comparison_expression(field=UTerm.id,
                                                         value=term_id,
                                                         settings=settings)
    statement = select(UTerm).join(UDataDescriptor).where(UDataDescriptor.id == data_descriptor_id,
                                                          where_expression)
    results = session.exec(statement)
    result = results.all()
    return result


def find_terms_in_data_descriptor(data_descriptor_id: str,
                                  term_id: str,
                                  settings: SearchSettings | None = None) \
                                     -> list[DataDescriptor]:
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
        - `EXACT` and absence of `settings`: returns zero or one term instance in the list.
        - `REGEX`, `LIKE`, `STARTS_WITH` and `ENDS_WITH`: returns zero, one or more term \
          instances in the list.

    :param data_descriptor_id: A data descriptor id
    :type data_descriptor_id: str
    :param term_id: A term id to be found
    :type term_id: str
    :param settings: The search settings
    :type settings: SearchSettings | None
    :returns: A list of term instances. Returns an empty list if no matches are found.
    :rtype: list[DataDescriptor]
    """
    result: list[DataDescriptor] = list()
    with get_universe_session() as session:
        terms = _find_terms_in_data_descriptor(data_descriptor_id, term_id, session, settings)
        instantiate_pydantic_terms(terms, result, settings.selected_term_fields if settings else None)
    return result


def _find_terms_in_universe(term_id: str,
                            session: Session,
                            settings: SearchSettings | None) -> Sequence[UTerm]:
    where_expression = _create_str_comparison_expression(field=UTerm.id,
                                                         value=term_id,
                                                         settings=settings)
    statement = select(UTerm).where(where_expression)
    results = session.exec(statement).all()
    return results


def find_terms_in_universe(term_id: str,
                           settings: SearchSettings | None = None) \
                              -> list[DataDescriptor]:
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
    :type settings: SearchSettings | None
    :returns: A list of term instances. Returns an empty list if no matches are found.
    :rtype: list[DataDescriptor]
    """
    result: list[DataDescriptor] = list()
    with get_universe_session() as session:
        terms = _find_terms_in_universe(term_id, session, settings)
        instantiate_pydantic_terms(terms, result, settings.selected_term_fields if settings else None)
    return result


def _get_all_terms_in_data_descriptor(data_descriptor: UDataDescriptor,
                                      selected_term_fields: Iterable[str] | None) -> list[DataDescriptor]:
    result: list[DataDescriptor] = list()
    instantiate_pydantic_terms(data_descriptor.terms, result, selected_term_fields)
    return result


def _find_data_descriptors_in_universe(data_descriptor_id: str,
                                       session: Session,
                                       settings: SearchSettings | None) -> Sequence[UDataDescriptor]:
    where_expression = _create_str_comparison_expression(field=UDataDescriptor.id,
                                                         value=data_descriptor_id,
                                                         settings=settings)
    statement = select(UDataDescriptor).where(where_expression)
    results = session.exec(statement)
    result = results.all()
    return result


def get_all_terms_in_data_descriptor(data_descriptor_id: str,
                                     selected_term_fields: Iterable[str] | None = None) \
                                                                            -> list[DataDescriptor]:
    """
    Gets all the terms of the given data descriptor.
    This function performs an exact match on the `data_descriptor_id` and does **not** search
    for similar or related descriptors.
    If the provided `data_descriptor_id` is not found, the function returns an empty list.

    :param data_descriptor_id: A data descriptor id
    :type data_descriptor_id: str
    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned. If empty, selects the id and type fields.
    :type selected_term_fields: Iterable[str] | None
    :returns: a list of term instances. Returns an empty list if no matches are found.
    :rtype: list[DataDescriptor]
    """
    with get_universe_session() as session:
        data_descriptors = _find_data_descriptors_in_universe(data_descriptor_id,
                                                              session,
                                                              None)
        if data_descriptors:
            data_descriptor = data_descriptors[0]
            result = _get_all_terms_in_data_descriptor(data_descriptor, selected_term_fields)
        else:
            result = list()
    return result


def find_data_descriptors_in_universe(data_descriptor_id: str,
                                      settings: SearchSettings | None = None) \
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
    :type settings: SearchSettings | None
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


def _get_all_data_descriptors_in_universe(session: Session) -> Sequence[UDataDescriptor]:
    statement = select(UDataDescriptor)
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


def get_all_terms_in_universe(selected_term_fields: Iterable[str] | None = None) -> list[DataDescriptor]:
    """
    Gets all the terms of the universe.
    Terms are unique within a data descriptor but may have some synonyms in the universe.

    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned. If empty, selects the id and type fields.
    :type selected_term_fields: Iterable[str] | None
    :returns: A list of term instances.
    :rtype: list[DataDescriptor]
    """
    result = list()
    with get_universe_session() as session:
        data_descriptors = _get_all_data_descriptors_in_universe(session)
        for data_descriptor in data_descriptors:
            # Term may have some synonyms within the whole universe.
            terms = _get_all_terms_in_data_descriptor(data_descriptor, selected_term_fields)
            result.extend(terms)
    return result


def _get_term_in_data_descriptor(data_descriptor_id: str, term_id: str, session: Session) \
                                                                           -> UTerm | None:
    statement = select(UTerm).join(UDataDescriptor).where(UDataDescriptor.id == data_descriptor_id,
                                                          UTerm.id == term_id)
    results = session.exec(statement)
    result = results.one_or_none()
    return result


def get_term_in_data_descriptor(data_descriptor_id: str,
                                term_id: str,
                                selected_term_fields: Iterable[str] | None = None) \
                                                                           -> DataDescriptor | None:
    """
    Returns a term according to the id of the terms in the given data descriptor.
    This function performs an exact match on the `term_id` and does not search
    for similar or related terms. If the provided `term_id` is not found, the function returns `None`.

    :param data_descriptor_id: The given data descriptor id.
    :param term_id: An id of a term to be found.
    :type term_id: str
    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned. If empty, selects the id and type fields.
    :type selected_term_fields: Iterable[str] | None
    :returns: A term instance. Returns `None` if no match is found.
    :rtype: DataDescriptor | None
    """
    with get_universe_session() as session:
        term_found = _get_term_in_data_descriptor(data_descriptor_id, term_id, session)
        if term_found:
            result = instantiate_pydantic_term(term_found, selected_term_fields)
        else:
            result = None
    return result


def _get_term_in_universe(term_id: str, session: Session) -> UTerm | None:
    statement = select(UTerm).where(UTerm.id == term_id)
    results = session.exec(statement)
    result = results.first()  # Term ids are not supposed to be unique within the universe.
    return result


def get_term_in_universe(term_id: str,
                         selected_term_fields: Iterable[str] | None = None) -> DataDescriptor | None:
    """
    Returns the first occurrence of a term according to the id of the terms in the universe.
    Terms are unique within a data descriptor but may have some synonyms in the universe.
    This function performs an exact match on the `term_id` and does not search
    for similar or related terms. If the provided `term_id` is not found, the function returns `None`.

    :param term_id: An id of a term to be found.
    :type term_id: str
    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned. If empty, selects the id and type fields.
    :type selected_term_fields: Iterable[str] | None
    :returns: A term instance. Returns `None` if no match is found.
    :rtype: DataDescriptor | None
    """
    with get_universe_session() as session:
        term_found = _get_term_in_universe(term_id, session)
        if term_found:
            result = instantiate_pydantic_term(term_found, selected_term_fields)
        else:
            result = None
    return result


def _get_data_descriptor_in_universe(data_descriptor_id: str, session: Session) -> UDataDescriptor | None:
    statement = select(UDataDescriptor).where(UDataDescriptor.id == data_descriptor_id)
    results = session.exec(statement)
    result = results.one_or_none()
    return result


def get_data_descriptor_in_universe(data_descriptor_id: str) -> tuple[str, dict] | None:
    """
    TODO: docstring
    """
    with get_universe_session() as session:
        data_descriptor_found = _get_data_descriptor_in_universe(data_descriptor_id, session)
        if data_descriptor_found:
            result = data_descriptor_found.id, data_descriptor_found.context
        else:
            result = None
    return result


def R_find_data_descriptors_in_universe(expression: str, session: Session,
                                        only_id: bool = False) -> Sequence[UDataDescriptor]:
    # TODO: replace the following instructions by this, when specs will ba available in UDataDescriptor.
    # matching_condition = generate_matching_condition(CollectionFTS, only_id)
    matching_condition = col(UDataDescriptorFTS5.id).match(expression)
    tmp_statement = select(UDataDescriptorFTS5).where(matching_condition)
    statement = select(UDataDescriptor).from_statement(tmp_statement.order_by(text('rank')))
    return execute_match_statement(expression, statement, session)


def Rfind_data_descriptors_in_universe(expression: str,
                                       only_id: bool = False) -> list[tuple[str, dict]]:
    """
    TODO: docstring
    only_id alway true
    """
    result: list[tuple[str, dict]] = list()
    with get_universe_session() as session:
        data_descriptors_found = R_find_data_descriptors_in_universe(expression, session, only_id)
        if data_descriptors_found:
            for data_descriptor_found in data_descriptors_found:
                result.append((data_descriptor_found.id, data_descriptor_found.context))
    return result


def R_find_terms_in_universe(expression: str, session: Session, only_id: bool = False) -> Sequence[UTerm]:
    matching_condition = generate_matching_condition(UTermFTS5, expression, only_id)
    tmp_statement = select(UTermFTS5).where(matching_condition)
    statement = select(UTerm).from_statement(tmp_statement.order_by(text('rank')))
    return execute_match_statement(expression, statement, session)


def Rfind_terms_in_universe(expression: str, only_id: bool = False,
                            selected_term_fields: Iterable[str] | None = None) -> list[DataDescriptor]:
    """
    TODO: docstring
    """
    result: list[DataDescriptor] = list()
    with get_universe_session() as session:
        uterms_found = R_find_terms_in_universe(expression, session, only_id)
        if uterms_found:
            instantiate_pydantic_terms(uterms_found, result, selected_term_fields)
    return result


def R_find_terms_in_data_descriptor(expression: str, data_descriptor_id: str, session: Session,
                                    only_id: bool = False) -> Sequence[UTerm]:
    matching_condition = generate_matching_condition(UTermFTS5, expression, only_id)
    where_condition = UDataDescriptor.id == data_descriptor_id, matching_condition
    tmp_statement = select(UTermFTS5).join(UDataDescriptor).where(*where_condition)
    statement = select(UTerm).from_statement(tmp_statement.order_by(text('rank')))
    return execute_match_statement(expression, statement, session)


def Rfind_terms_in_data_descriptor(expression: str, data_descriptor_id: str, only_id: bool = False,
                                   selected_term_fields: Iterable[str] | None = None) \
                                                                            -> list[DataDescriptor]:
    """
    TODO: docstring
    """
    result: list[DataDescriptor] = list()
    with get_universe_session() as session:
        uterms_found = R_find_terms_in_data_descriptor(expression, data_descriptor_id,
                                                       session, only_id)
        if uterms_found:
            instantiate_pydantic_terms(uterms_found, result, selected_term_fields)
    return result


def find_items_in_universe(expression: str, only_id: bool = False) -> list[Item]:
    """
    TODO: docstring.
    """
    result = list()
    with get_universe_session() as session:
        if only_id:
            dd_column = col(UDataDescriptorFTS5.id)
            term_column = col(UTermFTS5.id)
        else:
            dd_column = col(UDataDescriptorFTS5.id)  # TODO: use specs when implemented!
            term_column = col(UTermFTS5.specs)  # type: ignore
        dd_where_condition = dd_column.match(expression)
        dd_statement = select(UDataDescriptorFTS5.id,
                              text("'data_descriptor' AS TYPE"),
                              text("'universe' AS TYPE"),
                              text('rank')).where(dd_where_condition)
        term_where_condition = term_column.match(expression)
        term_statement = select(UTermFTS5.id,
                                text("'term' AS TYPE"),
                                UDataDescriptor.id,
                                text('rank')).join(UDataDescriptor) \
                                             .where(term_where_condition)
        try:
            # Items found are kind of tuple with an object, a kindness, a parent id and a rank.
            dds_found = session.exec(dd_statement).all()
            terms_found = session.exec(term_statement).all()
            tmp_result: list[Any] = list()
            tmp_result.extend(dds_found)
            tmp_result.extend(terms_found)
            tmp_result = sorted(tmp_result, key=lambda r: r[3], reverse=False)
            result = [Item(id=r[0], kind=r[1], parent_id=r[2]) for r in tmp_result]
        except OperationalError:
            raise APIException(f"unable to interpret expression '{expression}'")
    return result


if __name__ == "__main__":
    find_items_in_universe('ipsl', True)
