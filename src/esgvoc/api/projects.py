import re
from typing import Iterable, Sequence

from sqlalchemy import text
from sqlmodel import Session, and_, col, select

import esgvoc.api.universe as universe
import esgvoc.core.constants as constants
import esgvoc.core.service as service
from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
from esgvoc.api.project_specs import ProjectSpecs
from esgvoc.api.report import ProjectTermError, UniverseTermError, ValidationReport
from esgvoc.api.search import (
    Item,
    MatchingTerm,
    execute_find_item_statements,
    execute_match_statement,
    generate_matching_condition,
    get_universe_session,
    handle_rank_limit_offset,
    instantiate_pydantic_term,
    instantiate_pydantic_terms,
)
from esgvoc.core.db.connection import DBConnection
from esgvoc.core.db.models.mixins import TermKind
from esgvoc.core.db.models.project import (
    Collection,
    PCollectionFTS5,
    Project,
    PTerm,
    PTermFTS5,
)
from esgvoc.core.db.models.universe import UTerm
from esgvoc.core.exceptions import EsgvocNotFoundError, EsgvocValueError

# [OPTIMIZATION]
_VALID_TERM_IN_COLLECTION_CACHE: dict[str, list[MatchingTerm]] = dict()
_VALID_VALUE_AGAINST_GIVEN_TERM_CACHE: dict[str, list[UniverseTermError | ProjectTermError]] = dict()


def _get_project_connection(project_id: str) -> DBConnection | None:
    if project_id in service.current_state.projects:
        return service.current_state.projects[project_id].db_connection
    else:
        return None


def _get_project_session_with_exception(project_id: str) -> Session:
    if connection := _get_project_connection(project_id):
        project_session = connection.create_session()
        return project_session
    else:
        raise EsgvocNotFoundError(f'unable to find project {project_id}')


def _resolve_term(composite_term_part: dict,
                  universe_session: Session,
                  project_session: Session) -> UTerm | PTerm:
    # First find the term in the universe than in the current project
    term_id = composite_term_part[constants.TERM_ID_JSON_KEY]
    term_type = composite_term_part[constants.TERM_TYPE_JSON_KEY]
    uterm = universe._get_term_in_data_descriptor(data_descriptor_id=term_type,
                                                  term_id=term_id,
                                                  session=universe_session)
    if uterm:
        return uterm
    else:
        pterm = _get_term_in_collection(collection_id=term_type,
                                        term_id=term_id,
                                        session=project_session)
    if pterm:
        return pterm
    else:
        msg = f'unable to find the term {term_id} in {term_type}'
        raise RuntimeError(msg)


def _get_composite_term_separator_parts(term: UTerm | PTerm) -> tuple[str, list]:
    separator = term.specs[constants.COMPOSITE_SEPARATOR_JSON_KEY]
    parts = term.specs[constants.COMPOSITE_PARTS_JSON_KEY]
    return separator, parts


# TODO: support optionality of parts of composite.
# It is backtrack possible for more than one missing parts.
def _valid_value_composite_term_with_separator(value: str,
                                               term: UTerm | PTerm,
                                               universe_session: Session,
                                               project_session: Session)\
                                                   -> list[UniverseTermError | ProjectTermError]:
    result = list()
    separator, parts = _get_composite_term_separator_parts(term)
    if separator in value:
        splits = value.split(separator)
        if len(splits) == len(parts):
            for index in range(0, len(splits)):
                given_value = splits[index]
                resolved_term = _resolve_term(parts[index],
                                              universe_session,
                                              project_session)
                errors = _valid_value(given_value,
                                      resolved_term,
                                      universe_session,
                                      project_session)
                result.extend(errors)
        else:
            result.append(_create_term_error(value, term))
    else:
        result.append(_create_term_error(value, term))
    return result


def _transform_to_pattern(term: UTerm | PTerm,
                          universe_session: Session,
                          project_session: Session) -> str:
    match term.kind:
        case TermKind.PLAIN:
            if constants.DRS_SPECS_JSON_KEY in term.specs:
                result = term.specs[constants.DRS_SPECS_JSON_KEY]
            else:
                raise EsgvocValueError(f"the term {term.id} doesn't have drs name. " +
                                       "Can't validate it.")
        case TermKind.PATTERN:
            result = term.specs[constants.PATTERN_JSON_KEY]
        case TermKind.COMPOSITE:
            separator, parts = _get_composite_term_separator_parts(term)
            result = ""
            for part in parts:
                resolved_term = _resolve_term(part, universe_session, project_session)
                pattern = _transform_to_pattern(resolved_term, universe_session, project_session)
                result = f'{result}{pattern}{separator}'
            result = result.rstrip(separator)
        case _:
            raise RuntimeError(f'unsupported term kind {term.kind}')
    return result


# TODO: support optionality of parts of composite.
# It is backtrack possible for more than one missing parts.
def _valid_value_composite_term_separator_less(value: str,
                                               term: UTerm | PTerm,
                                               universe_session: Session,
                                               project_session: Session)\
                                                   -> list[UniverseTermError | ProjectTermError]:
    result = list()
    try:
        pattern = _transform_to_pattern(term, universe_session, project_session)
        try:
            # Patterns terms are meant to be validated individually.
            # So their regex are defined as a whole (begins by a ^, ends by a $).
            # As the pattern is a concatenation of plain or regex, multiple ^ and $ can exist.
            # The later, must be removed.
            pattern = pattern.replace('^', '').replace('$', '')
            pattern = f'^{pattern}$'
            regex = re.compile(pattern)
        except Exception as e:
            msg = f'regex compilation error while processing term {term.id}:\n{e}'
            raise RuntimeError(msg) from e
        match = regex.match(value)
        if match is None:
            result.append(_create_term_error(value, term))
        return result
    except Exception as e:
        msg = f'cannot validate separator less composite term {term.id}:\n{e}'
        raise RuntimeError(msg) from e


def _valid_value_for_composite_term(value: str,
                                    term: UTerm | PTerm,
                                    universe_session: Session,
                                    project_session: Session)\
                                        -> list[UniverseTermError | ProjectTermError]:
    result = list()
    separator, _ = _get_composite_term_separator_parts(term)
    if separator:
        result = _valid_value_composite_term_with_separator(value, term, universe_session,
                                                            project_session)
    else:
        result = _valid_value_composite_term_separator_less(value, term, universe_session,
                                                            project_session)
    return result


def _create_term_error(value: str, term: UTerm | PTerm) -> UniverseTermError | ProjectTermError:
    if isinstance(term, UTerm):
        return UniverseTermError(value=value, term=term.specs, term_kind=term.kind,
                                 data_descriptor_id=term.data_descriptor.id)
    else:
        return ProjectTermError(value=value, term=term.specs, term_kind=term.kind,
                                collection_id=term.collection.id)


def _valid_value(value: str,
                 term: UTerm | PTerm,
                 universe_session: Session,
                 project_session: Session) -> list[UniverseTermError | ProjectTermError]:
    result = list()
    match term.kind:
        case TermKind.PLAIN:
            if constants.DRS_SPECS_JSON_KEY in term.specs:
                if term.specs[constants.DRS_SPECS_JSON_KEY] != value:
                    result.append(_create_term_error(value, term))
            else:
                raise EsgvocValueError(f"the term {term.id} doesn't have drs name. " +
                                       "Can't validate it.")
        case TermKind.PATTERN:
            # TODO: Pattern can be compiled and stored for further matching.
            pattern_match = re.match(term.specs[constants.PATTERN_JSON_KEY], value)
            if pattern_match is None:
                result.append(_create_term_error(value, term))
        case TermKind.COMPOSITE:
            result.extend(_valid_value_for_composite_term(value, term,
                                                          universe_session,
                                                          project_session))
        case _:
            raise RuntimeError(f'unsupported term kind {term.kind}')
    return result


def _check_value(value: str) -> str:
    if not value or value.isspace():
        raise EsgvocValueError('value should be set')
    else:
        return value


def _search_plain_term_and_valid_value(value: str,
                                       collection_id: str,
                                       project_session: Session) \
                                        -> str | None:
    where_expression = and_(Collection.id == collection_id,
                            PTerm.specs[constants.DRS_SPECS_JSON_KEY] == f'"{value}"')
    statement = select(PTerm).join(Collection).where(where_expression)
    term = project_session.exec(statement).one_or_none()
    return term.id if term else None


def _valid_value_against_all_terms_of_collection(value: str,
                                                 collection: Collection,
                                                 universe_session: Session,
                                                 project_session: Session) \
                                                     -> list[str]:
    if collection.terms:
        result = list()
        for pterm in collection.terms:
            _errors = _valid_value(value, pterm,
                                   universe_session,
                                   project_session)
            if not _errors:
                result.append(pterm.id)
        return result
    else:
        raise RuntimeError(f'collection {collection.id} has no term')


def _valid_value_against_given_term(value: str,
                                    project_id: str,
                                    collection_id: str,
                                    term_id: str,
                                    universe_session: Session,
                                    project_session: Session)\
                                        -> list[UniverseTermError | ProjectTermError]:
    # [OPTIMIZATION]
    key = value + project_id + collection_id + term_id
    if key in _VALID_VALUE_AGAINST_GIVEN_TERM_CACHE:
        result = _VALID_VALUE_AGAINST_GIVEN_TERM_CACHE[key]
    else:
        term = _get_term_in_collection(collection_id,
                                       term_id,
                                       project_session)
        if term:
            result = _valid_value(value, term, universe_session, project_session)
        else:
            raise EsgvocNotFoundError(f'unable to find term {term_id} ' +
                                      f'in collection {collection_id}')
        _VALID_VALUE_AGAINST_GIVEN_TERM_CACHE[key] = result
    return result


def valid_term(value: str,
               project_id: str,
               collection_id: str,
               term_id: str) \
                  -> ValidationReport:
    """
    Check if the given value may or may not represent the given term. The functions returns
    a report that contains the possible errors.

    Behavior based on the nature of the term:
        - plain term: the function try to match the value on the drs_name field.
        - pattern term: the function try to match the value on the pattern field (regex).
        - composite term:
            - if the composite has got a separator, the function splits the value according to the\
              separator of the term then it try to match every part of the composite\
              with every split of the value.
            - if the composite hasn't got a separator, the function aggregates the parts of the \
              composite so as to compare it as a regex to the value.

    If any of the provided ids (`project_id`, `collection_id` or `term_id`) is not found,
    the function raises a APIException.

    :param value: A value to be validated
    :type value: str
    :param project_id: A project id
    :type project_id: str
    :param collection_id: A collection id
    :type collection_id: str
    :param term_id: A term id
    :type term_id: str
    :returns: A validation report that contains the possible errors
    :rtype: ValidationReport
    :raises APIException: If any of the provided ids is not found
    """
    value = _check_value(value)
    with get_universe_session() as universe_session, \
         _get_project_session_with_exception(project_id) as project_session:
        errors = _valid_value_against_given_term(value, project_id, collection_id, term_id,
                                                 universe_session, project_session)
        return ValidationReport(expression=value, errors=errors)


def _valid_term_in_collection(value: str,
                              project_id: str,
                              collection_id: str,
                              universe_session: Session,
                              project_session: Session) \
                                -> list[MatchingTerm]:
    # [OPTIMIZATION]
    key = value + project_id + collection_id
    if key in _VALID_TERM_IN_COLLECTION_CACHE:
        result = _VALID_TERM_IN_COLLECTION_CACHE[key]
    else:
        value = _check_value(value)
        result = list()
        collection = _get_collection_in_project(collection_id, project_session)
        if collection:
            match collection.term_kind:
                case TermKind.PLAIN:
                    term_id_found = _search_plain_term_and_valid_value(value, collection_id,
                                                                       project_session)
                    if term_id_found:
                        result.append(MatchingTerm(project_id=project_id,
                                                   collection_id=collection_id,
                                                   term_id=term_id_found))
                case _:
                    term_ids_found = _valid_value_against_all_terms_of_collection(value, collection,
                                                                                  universe_session,
                                                                                  project_session)
                    for term_id_found in term_ids_found:
                        result.append(MatchingTerm(project_id=project_id,
                                                   collection_id=collection_id,
                                                   term_id=term_id_found))
        else:
            msg = f'unable to find collection {collection_id}'
            raise EsgvocNotFoundError(msg)
        _VALID_TERM_IN_COLLECTION_CACHE[key] = result
    return result


def valid_term_in_collection(value: str,
                             project_id: str,
                             collection_id: str) \
                               -> list[MatchingTerm]:
    """
    Check if the given value may or may not represent a term in the given collection. The function
    returns the terms that the value matches.

    Behavior based on the nature of the term:
        - plain term: the function try to match the value on the drs_name field.
        - pattern term: the function try to match the value on the pattern field (regex).
        - composite term:
            - if the composite has got a separator, the function splits the value according to the \
              separator of the term then it try to match every part of the composite \
              with every split of the value.
            - if the composite hasn't got a separator, the function aggregates the parts of the \
              composite so as to compare it as a regex to the value.

    If any of the provided ids (`project_id` or `collection_id`) is not found,
    the function raises a APIException.

    :param value: A value to be validated
    :type value: str
    :param project_id: A project id
    :type project_id: str
    :param collection_id: A collection id
    :type collection_id: str
    :returns: The list of terms that the value matches.
    :rtype: list[MatchingTerm]
    :raises APIException: If any of the provided ids is not found
    """
    with get_universe_session() as universe_session, \
         _get_project_session_with_exception(project_id) as project_session:
        return _valid_term_in_collection(value, project_id, collection_id,
                                         universe_session, project_session)


def _valid_term_in_project(value: str,
                           project_id: str,
                           universe_session: Session,
                           project_session: Session) -> list[MatchingTerm]:
    result = list()
    collections = _get_all_collections_in_project(project_session)
    for collection in collections:
        result.extend(_valid_term_in_collection(value, project_id, collection.id,
                                                universe_session, project_session))
    return result


def valid_term_in_project(value: str, project_id: str) -> list[MatchingTerm]:
    """
    Check if the given value may or may not represent a term in the given project. The function
    returns the terms that the value matches.

    Behavior based on the nature of the term:
        - plain term: the function try to match the value on the drs_name field.
        - pattern term: the function try to match the value on the pattern field (regex).
        - composite term:
            - if the composite has got a separator, the function splits the value according to the \
              separator of the term then it try to match every part of the composite \
              with every split of the value.
            - if the composite hasn't got a separator, the function aggregates the parts of the \
              composite so as to compare it as a regex to the value.

    If the `project_id` is not found, the function raises a APIException.

    :param value: A value to be validated
    :type value: str
    :param project_id: A project id
    :type project_id: str
    :returns: The list of terms that the value matches.
    :rtype: list[MatchingTerm]
    :raises APIException: If the `project_id` is not found
    """
    with get_universe_session() as universe_session, \
         _get_project_session_with_exception(project_id) as project_session:
        return _valid_term_in_project(value, project_id, universe_session, project_session)


def valid_term_in_all_projects(value: str) -> list[MatchingTerm]:
    """
    Check if the given value may or may not represent a term in all projects. The function
    returns the terms that the value matches.

    Behavior based on the nature of the term:
        - plain term: the function try to match the value on the drs_name field.
        - pattern term: the function try to match the value on the pattern field (regex).
        - composite term:
            - if the composite has got a separator, the function splits the value according to the \
              separator of the term then it try to match every part of the composite \
              with every split of the value.
            - if the composite hasn't got a separator, the function aggregates the parts of the \
              composite so as to compare it as a regex to the value.

    :param value: A value to be validated
    :type value: str
    :returns: The list of terms that the value matches.
    :rtype: list[MatchingTerm]
    """
    result = list()
    with get_universe_session() as universe_session:
        for project_id in get_all_projects():
            with _get_project_session_with_exception(project_id) as project_session:
                result.extend(_valid_term_in_project(value, project_id,
                                                     universe_session, project_session))
    return result


def get_all_terms_in_collection(project_id: str,
                                collection_id: str,
                                selected_term_fields: Iterable[str] | None = None)\
                                   -> list[DataDescriptor]:
    """
    Gets all terms of the given collection of a project.
    This function performs an exact match on the `project_id` and `collection_id`,
    and does not search for similar or related projects and collections.
    If any of the provided ids (`project_id` or `collection_id`) is not found, the function
    returns an empty list.

    :param project_id: A project id
    :type project_id: str
    :param collection_id: A collection id
    :type collection_id: str
    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned. If empty, selects the id and type fields.
    :type selected_term_fields: Iterable[str] | None
    :returns: a list of term instances. Returns an empty list if no matches are found.
    :rtype: list[DataDescriptor]
    """
    result = list()
    if connection := _get_project_connection(project_id):
        with connection.create_session() as session:
            collection = _get_collection_in_project(collection_id, session)
            if collection:
                result = _get_all_terms_in_collection(collection, selected_term_fields)
    return result


def _get_all_collections_in_project(session: Session) -> list[Collection]:
    project = session.get(Project, constants.SQLITE_FIRST_PK)
    # Project can't be missing if session exists.
    return project.collections  # type: ignore


def get_all_collections_in_project(project_id: str) -> list[str]:
    """
    Gets all collections of the given project.
    This function performs an exact match on the `project_id` and
    does not search for similar or related projects.
    If the provided `project_id` is not found, the function returns an empty list.

    :param project_id: A project id
    :type project_id: str
    :returns: A list of collection ids. Returns an empty list if no matches are found.
    :rtype: list[str]
    """
    result = list()
    if connection := _get_project_connection(project_id):
        with connection.create_session() as session:
            collections = _get_all_collections_in_project(session)
            for collection in collections:
                result.append(collection.id)
    return result


def _get_all_terms_in_collection(collection: Collection,
                                 selected_term_fields: Iterable[str] | None) -> list[DataDescriptor]:
    result: list[DataDescriptor] = list()
    instantiate_pydantic_terms(collection.terms, result, selected_term_fields)
    return result


def get_all_terms_in_project(project_id: str,
                             selected_term_fields: Iterable[str] | None = None) -> list[DataDescriptor]:
    """
    Gets all terms of the given project.
    This function performs an exact match on the `project_id` and
    does not search for similar or related projects.
    Terms are unique within a collection but may have some synonyms in a project.
    If the provided `project_id` is not found, the function returns an empty list.

    :param project_id: A project id
    :type project_id: str
    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned. If empty, selects the id and type fields.
    :type selected_term_fields: Iterable[str] | None
    :returns: A list of term instances. Returns an empty list if no matches are found.
    :rtype: list[DataDescriptor]
    """
    result = list()
    if connection := _get_project_connection(project_id):
        with connection.create_session() as session:
            collections = _get_all_collections_in_project(session)
            for collection in collections:
                # Term may have some synonyms in a project.
                result.extend(_get_all_terms_in_collection(collection, selected_term_fields))
    return result


def get_all_terms_in_all_projects(selected_term_fields: Iterable[str] | None = None) \
                                                          -> list[tuple[str, list[DataDescriptor]]]:
    """
    Gets all terms of all projects.

    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned. If empty, selects the id and type fields.
    :type selected_term_fields: Iterable[str] | None
    :returns: A list of tuple project_id and term instances of that project.
    :rtype: list[tuple[str, list[DataDescriptor]]]
    """
    project_ids = get_all_projects()
    result = list()
    for project_id in project_ids:
        terms = get_all_terms_in_project(project_id, selected_term_fields)
        result.append((project_id, terms))
    return result


def get_all_projects() -> list[str]:
    """
    Gets all projects.

    :returns: A list of project ids.
    :rtype: list[str]
    """
    return list(service.current_state.projects.keys())


def _get_term_in_project(term_id: str, session: Session) -> PTerm | None:
    statement = select(PTerm).where(PTerm.id == term_id)
    results = session.exec(statement)
    result = results.first()  # Term ids are not supposed to be unique within a project.
    return result


def get_term_in_project(project_id: str, term_id: str,
                        selected_term_fields: Iterable[str] | None = None) -> DataDescriptor | None:
    """
    Returns the first occurrence of the terms, in the given project, whose id corresponds exactly to
    the given term id.
    Terms are unique within a collection but may have some synonyms in a project.
    This function performs an exact match on the `project_id` and `term_id`, and does not search
    for similar or related projects and terms.
    If any of the provided ids (`project_id` or `term_id`) is not found,
    the function returns `None`.

    :param project_id: The id of the given project.
    :type project_id: str
    :param term_id: The id of a term to be found.
    :type term_id: str
    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned. If empty, selects the id and type fields.
    :type selected_term_fields: Iterable[str] | None
    :returns: A term instance. Returns `None` if no match is found.
    :rtype: DataDescriptor | None
    """
    result: DataDescriptor | None = None
    if connection := _get_project_connection(project_id):
        with connection.create_session() as session:
            term_found = _get_term_in_project(term_id, session)
            if term_found:
                result = instantiate_pydantic_term(term_found, selected_term_fields)
    return result


def _get_term_in_collection(collection_id: str, term_id: str, session: Session) -> PTerm | None:
    statement = select(PTerm).join(Collection).where(Collection.id == collection_id,
                                                     PTerm.id == term_id)
    results = session.exec(statement)
    result = results.one_or_none()
    return result


def get_term_in_collection(project_id: str, collection_id: str, term_id: str,
                           selected_term_fields: Iterable[str] | None = None) -> DataDescriptor | None:
    """
    Returns the term, in the given project and collection,
    whose id corresponds exactly to the given term id.
    This function performs an exact match on the `project_id`, `collection_id` and `term_id`,
    and does not search for similar or related projects, collections and terms.
    If any of the provided ids (`project_id`, `collection_id` or `term_id`) is not found,
    the function returns `None`.

    :param project_id: The id of the given project.
    :type project_id: str
    :param collection_id: The id of the given collection.
    :type collection_id: str
    :param term_id: The id of a term to be found.
    :type term_id: str
    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned. If empty, selects the id and type fields.
    :type selected_term_fields: Iterable[str] | None
    :returns: A term instance. Returns `None` if no match is found.
    :rtype: DataDescriptor | None
    """
    result: DataDescriptor | None = None
    if connection := _get_project_connection(project_id):
        with connection.create_session() as session:
            term_found = _get_term_in_collection(collection_id, term_id, session)
            if term_found:
                result = instantiate_pydantic_term(term_found, selected_term_fields)
    return result


def _get_collection_in_project(collection_id: str, session: Session) -> Collection | None:
    statement = select(Collection).where(Collection.id == collection_id)
    results = session.exec(statement)
    result = results.one_or_none()
    return result


def get_collection_in_project(project_id: str, collection_id: str) -> tuple[str, dict] | None:
    """
    Returns the collection, in the given project, whose id corresponds exactly to
    the given collection id.
    This function performs an exact match on the `project_id` and `collection_id`, and does not search
    for similar or related projects and collections.
    If any of the provided ids (`project_id` or `collection_id`) is not found,
    the function returns `None`.

    :param project_id: The id of the given project.
    :type project_id: str
    :param collection_id: The id of a collection to be found.
    :type collection_id: str
    :returns: A collection id and context. Returns `None` if no match is found.
    :rtype: tuple[str, dict] | None
    """
    result: tuple[str, dict] | None = None
    if connection := _get_project_connection(project_id):
        with connection.create_session() as session:
            collection_found = _get_collection_in_project(collection_id, session)
            if collection_found:
                result = collection_found.id, collection_found.context
    return result


def get_project(project_id: str) -> ProjectSpecs | None:
    """
    Get a project and returns its specifications.
    This function performs an exact match on the `project_id` and
    does not search for similar or related projects.
    If the provided `project_id` is not found, the function returns `None`.

    :param project_id: A project id to be found
    :type project_id: str
    :returns: The specs of the project found. Returns `None` if no matches are found.
    :rtype: ProjectSpecs | None
    """
    result: ProjectSpecs | None = None
    if connection := _get_project_connection(project_id):
        with connection.create_session() as session:
            project = session.get(Project, constants.SQLITE_FIRST_PK)
            try:
                # Project can't be missing if session exists.
                result = ProjectSpecs(**project.specs)  # type: ignore
            except Exception as e:
                msg = f'Unable to read specs in project {project_id}'
                raise RuntimeError(msg) from e
    return result


def _get_collection_from_data_descriptor_in_project(data_descriptor_id: str,
                                                    session: Session) -> Collection | None:
    statement = select(Collection).where(Collection.data_descriptor_id == data_descriptor_id)
    result = session.exec(statement).one_or_none()
    return result


def get_collection_from_data_descriptor_in_project(project_id: str,
                                                   data_descriptor_id: str) \
                                                    -> tuple[str, dict] | None:
    """
    Returns the collection, in the given project, that corresponds to the given data descriptor
    in the universe.
    This function performs an exact match on the `project_id` and `data_descriptor_id`,
    and does not search for similar or related projects and data descriptors.
    If any of the provided ids (`project_id` or `data_descriptor_id`) is not found, or if
    there is no collection corresponding to the given data descriptor, the function returns `None`.

    :param project_id: The id of the given project.
    :type project_id: str
    :param data_descriptor_id: The id of the given data descriptor.
    :type data_descriptor_id: str
    :returns: A collection id and context. Returns `None` if no matches are found.
    :rtype: tuple[str, dict] | None
    """
    result: tuple[str, dict] | None = None
    if connection := _get_project_connection(project_id):
        with connection.create_session() as session:
            collection_found = _get_collection_from_data_descriptor_in_project(data_descriptor_id,
                                                                               session)
            if collection_found:
                result = collection_found.id, collection_found.context
    return result


def get_collection_from_data_descriptor_in_all_projects(data_descriptor_id: str) \
                                                                     -> list[tuple[str, str, dict]]:
    """
    Returns the collections, in all projects, that correspond to the given data descriptor
    in the universe.
    This function performs an exact match on `data_descriptor_id`,
    and does not search for similar or related data descriptors.
    If the provided `data_descriptor_id` is not found, or if
    there is no collection corresponding to the given data descriptor, the function returns
    an empty list.

    :param data_descriptor_id: The id of the given data descriptor.
    :type data_descriptor_id: str
    :returns: A list of collection ids and contexts. Returns an empty list if no matches are found.
    :rtype: list[tuple[str, str, dict]]
    """
    result = list()
    project_ids = get_all_projects()
    for project_id in project_ids:
        collection_found = get_collection_from_data_descriptor_in_project(project_id,
                                                                          data_descriptor_id)
        if collection_found:
            result.append((project_id, collection_found[0], collection_found[1]))
    return result


def _find_collections_in_project(expression: str,
                                 session: Session,
                                 only_id: bool = False,
                                 limit: int | None = None,
                                 offset: int | None = None) -> Sequence[Collection]:
    matching_condition = generate_matching_condition(PCollectionFTS5, expression, only_id)
    tmp_statement = select(PCollectionFTS5).where(matching_condition)
    statement = select(Collection).from_statement(handle_rank_limit_offset(tmp_statement, limit, offset))
    return execute_match_statement(expression, statement, session)


def find_collections_in_project(expression: str, project_id: str,
                                only_id: bool = False,
                                limit: int | None = None,
                                offset: int | None = None) -> list[tuple[str, dict]]:
    """
    Find collections in the given project based on a full text search defined by the given `expression`.
    The `expression` comes from the powerful
    `SQLite FTS extension <https://sqlite.org/fts5.html#full_text_query_syntax>`_
    and corresponds to the expression of the `MATCH` operator.
    It can be composed of one or multiple keywords combined with boolean
    operators (`NOT`, `AND`, `^`, etc. default is `OR`). Keywords can define prefixes or postfixes
    with the wildcard `*`.
    The function returns a list of collection ids and contexts, sorted according to the
    bm25 ranking metric (list index `0` has the highest rank).
    This function performs an exact match on the `project_id`,
    and does not search for similar or related projects.
    If the provided `expression` does not hit any collection or the given `project_id` does not
    match exactly to an id of a project, the function returns an empty list.
    The function searches for the `expression` in the collection specifications.
    However, if `only_id` is `True` (default is `False`), the search is restricted to the id of the
    collections. **At the moment, `only_id` is set to `True` as the collections
    haven't got any description.**

    :param expression: The full text search expression.
    :type expression: str
    :param project_id: The id of the given project.
    :type project_id: str
    :param only_id: Performs the search only on ids, otherwise on all the specifications.
    :type only_id: bool
    :param limit: Limit the number of returned items found. Returns all items found the if \
    `limit` is either `None`, zero or negative.
    :type limit: int | None
    :param offset: Skips `offset` number of items found. Ignored if `offset` is \
    either `None`, zero or negative.
    :type offset: int | None
    :returns: A list of collection ids and contexts. Returns an empty list if no matches are found.
    :rtype: list[tuple[str, dict]]
    :raises APIException: If the `expression` cannot be interpreted.
    """
    result: list[tuple[str, dict]] = list()
    if connection := _get_project_connection(project_id):
        with connection.create_session() as session:
            collections_found = _find_collections_in_project(expression, session, only_id,
                                                             limit, offset)
            for collection in collections_found:
                result.append((collection.id, collection.context))
    return result


def _find_terms_in_collection(expression: str,
                              collection_id: str,
                              session: Session,
                              only_id: bool = False,
                              limit: int | None = None,
                              offset: int | None = None) -> Sequence[PTerm]:
    matching_condition = generate_matching_condition(PTermFTS5, expression, only_id)
    where_condition = Collection.id == collection_id, matching_condition
    tmp_statement = select(PTermFTS5).join(Collection).where(*where_condition)
    statement = select(PTerm).from_statement(handle_rank_limit_offset(tmp_statement, limit, offset))
    return execute_match_statement(expression, statement, session)


def _find_terms_in_project(expression: str,
                           session: Session,
                           only_id: bool = False,
                           limit: int | None = None,
                           offset: int | None = None) -> Sequence[PTerm]:
    matching_condition = generate_matching_condition(PTermFTS5, expression, only_id)
    tmp_statement = select(PTermFTS5).where(matching_condition)
    statement = select(PTerm).from_statement(handle_rank_limit_offset(tmp_statement, limit, offset))
    return execute_match_statement(expression, statement, session)


def find_terms_in_collection(expression: str, project_id: str,
                             collection_id: str,
                             only_id: bool = False,
                             limit: int | None = None,
                             offset: int | None = None,
                             selected_term_fields: Iterable[str] | None = None) \
                                                                          -> list[DataDescriptor]:
    """
    Find terms in the given project and collection based on a full text search defined by the given
    `expression`. The `expression` comes from the powerful
    `SQLite FTS extension <https://sqlite.org/fts5.html#full_text_query_syntax>`_
    and corresponds to the expression of the `MATCH` operator.
    It can be composed of one or multiple keywords combined with boolean
    operators (`NOT`, `AND`, `^`, etc. default is `OR`). Keywords can define prefixes or postfixes
    with the wildcard `*`.
    The function returns a list of term instances, sorted according to the
    bm25 ranking metric (list index `0` has the highest rank).
    This function performs an exact match on the `project_id` and `collection_id`,
    and does not search for similar or related projects and collections.
    If the provided `expression` does not hit any term or if any of the provided ids
    (`project_id` or `collection_id`) is not found, the function returns an empty list.
    The function searches for the `expression` in the term specifications.
    However, if `only_id` is `True` (default is `False`), the search is restricted to the id of the
    terms.

    :param expression: The full text search expression.
    :type expression: str
    :param project_id: The id of the given project.
    :type project_id: str
    :param collection_id: The id of the given collection.
    :type collection_id: str
    :param only_id: Performs the search only on ids, otherwise on all the specifications.
    :type only_id: bool
    :param limit: Limit the number of returned items found. Returns all items found the if \
    `limit` is either `None`, zero or negative.
    :type limit: int | None
    :param offset: Skips `offset` number of items found. Ignored if `offset` is \
    either `None`, zero or negative.
    :type offset: int | None
    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned. If empty, selects the id and type fields.
    :type selected_term_fields: Iterable[str] | None
    :returns: A list of term instances. Returns an empty list if no matches are found.
    :rtype: list[DataDescriptor]
    :raises APIException: If the `expression` cannot be interpreted.
    """
    result: list[DataDescriptor] = list()
    if connection := _get_project_connection(project_id):
        with connection.create_session() as session:
            pterms_found = _find_terms_in_collection(expression, collection_id, session,
                                                     only_id, limit, offset)
            instantiate_pydantic_terms(pterms_found, result, selected_term_fields)
    return result


def find_terms_in_project(expression: str,
                          project_id: str,
                          only_id: bool = False,
                          limit: int | None = None,
                          offset: int | None = None,
                          selected_term_fields: Iterable[str] | None = None) \
                                                                          -> list[DataDescriptor]:
    """
    Find terms in the given project on a full text search defined by the given
    `expression`. The `expression` comes from the powerful
    `SQLite FTS extension <https://sqlite.org/fts5.html#full_text_query_syntax>`_
    and corresponds to the expression of the `MATCH` operator.
    It can be composed of one or multiple keywords combined with boolean
    operators (`NOT`, `AND`, `^`, etc. default is `OR`). Keywords can define prefixes or postfixes
    with the wildcard `*`.
    The function returns a list of term instances, sorted according to the
    bm25 ranking metric (list index `0` has the highest rank).
    This function performs an exact match on the `project_id`,
    and does not search for similar or related projects.
    If the provided `expression` does not hit any term or if any of the provided `project_id` is
    not found, the function returns an empty list.
    The function searches for the `expression` in the term specifications.
    However, if `only_id` is `True` (default is `False`), the search is restricted to the id of the
    terms.

    :param expression: The full text search expression.
    :type expression: str
    :param project_id: The id of the given project.
    :type project_id: str
    :param only_id: Performs the search only on ids, otherwise on all the specifications.
    :type only_id: bool
    :param limit: Limit the number of returned items found. Returns all items found the if \
    `limit` is either `None`, zero or negative.
    :type limit: int | None
    :param offset: Skips `offset` number of items found. Ignored if `offset` is \
    either `None`, zero or negative.
    :type offset: int | None
    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned. If empty, selects the id and type fields.
    :type selected_term_fields: Iterable[str] | None
    :returns: A list of term instances. Returns an empty list if no matches are found.
    :rtype: list[DataDescriptor]
    :raises APIException: If the `expression` cannot be interpreted.
    """
    result: list[DataDescriptor] = list()
    if connection := _get_project_connection(project_id):
        with connection.create_session() as session:
            pterms_found = _find_terms_in_project(expression, session, only_id, limit, offset)
            instantiate_pydantic_terms(pterms_found, result, selected_term_fields)
    return result


def find_terms_in_all_projects(expression: str,
                               only_id: bool = False,
                               limit: int | None = None,
                               offset: int | None = None,
                               selected_term_fields: Iterable[str] | None = None) \
                                                        -> list[tuple[str, list[DataDescriptor]]]:
    """
    Find terms in the all projects on a full text search defined by the given
    `expression`. The `expression` comes from the powerful
    `SQLite FTS extension <https://sqlite.org/fts5.html#full_text_query_syntax>`_
    and corresponds to the expression of the `MATCH` operator.
    It can be composed of one or multiple keywords combined with boolean
    operators (`NOT`, `AND`, `^`, etc. default is `OR`). Keywords can define prefixes or postfixes
    with the wildcard `*`.
    The function returns a list of project ids and term instances, sorted according to the
    bm25 ranking metric (list index `0` has the highest rank).
    If the provided `expression` does not hit any term, the function returns an empty list.
    The function searches for the `expression` in the term specifications.
    However, if `only_id` is `True` (default is `False`), the search is restricted to the id of the
    terms.

    :param expression: The full text search expression.
    :type expression: str
    :param only_id: Performs the search only on ids, otherwise on all the specifications.
    :type only_id: bool
    :param limit: Limit the number of returned items found. Returns all items found the if \
    `limit` is either `None`, zero or negative.
    :type limit: int | None
    :param offset: Skips `offset` number of items found. Ignored if `offset` is \
    either `None`, zero or negative.
    :type offset: int | None
    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned. If empty, selects the id and type fields.
    :type selected_term_fields: Iterable[str] | None
    :returns: A list of project ids and term instances. Returns an empty list if no matches are found.
    :rtype: list[tuple[str, list[DataDescriptor]]]
    :raises APIException: If the `expression` cannot be interpreted.
    """
    result: list[tuple[str, list[DataDescriptor]]] = list()
    project_ids = get_all_projects()
    for project_id in project_ids:
        terms_found = find_terms_in_project(expression, project_id, only_id,
                                            limit, offset, selected_term_fields)
        if terms_found:
            result.append((project_id, terms_found))
    return result


def find_items_in_project(expression: str,
                          project_id: str,
                          only_id: bool = False,
                          limit: int | None = None,
                          offset: int | None = None) -> list[Item]:
    """
    Find items, at the moment terms and collections, in the given project based on a full-text
    search defined by the given `expression`. The `expression` comes from the powerful
    `SQLite FTS extension <https://sqlite.org/fts5.html#full_text_query_syntax>`_
    and corresponds to the expression of the `MATCH` operator.
    It can be composed of one or multiple keywords combined with boolean
    operators (`NOT`, `AND`, `^`, etc. default is `OR`). Keywords can define prefixes or postfixes
    with the wildcard `*`.
    The function returns a list of item instances sorted according to the
    bm25 ranking metric (list index `0` has the highest rank).
    This function performs an exact match on the `project_id`,
    and does not search for similar or related projects.
    If the provided `expression` does not hit any item, or the provided `project_id` is not found,
    the function returns an empty list.
    The function searches for the `expression` in the term and collection specifications.
    However, if `only_id` is `True` (default is `False`), the search is restricted to the id of the
    terms and collections. **At the moment, `only_id` is set to `True` for the collections because
    they haven't got any description.**

    :param expression: The full text search expression.
    :type expression: str
    :param only_id: Performs the search only on ids, otherwise on all the specifications.
    :type only_id: bool
    :param limit: Limit the number of returned items found. Returns all items found the if \
    `limit` is either `None`, zero or negative.
    :type limit: int | None
    :param offset: Skips `offset` number of items found. Ignored if `offset` is \
    either `None`, zero or negative.
    :type offset: int | None
    :returns: A list of item instances. Returns an empty list if no matches are found.
    :rtype: list[Item]
    :raises APIException: If the `expression` cannot be interpreted.
    """
    # TODO: execute union query when it will be possible to compute parent of terms and collections.
    result = list()
    if connection := _get_project_connection(project_id):
        with connection.create_session() as session:
            if only_id:
                collection_column = col(PCollectionFTS5.id)
                term_column = col(PTermFTS5.id)
            else:
                collection_column = col(PCollectionFTS5.id)  # TODO: use specs when implemented!
                term_column = col(PTermFTS5.specs)  # type: ignore
            collection_where_condition = collection_column.match(expression)
            collection_statement = select(PCollectionFTS5.id,
                                          text("'collection' AS TYPE"),
                                          text(f"'{project_id}' AS TYPE"),
                                          text('rank')).where(collection_where_condition)
            term_where_condition = term_column.match(expression)
            term_statement = select(PTermFTS5.id,
                                    text("'term' AS TYPE"),
                                    Collection.id,
                                    text('rank')).join(Collection) \
                                                 .where(term_where_condition)
            result = execute_find_item_statements(session, expression, collection_statement,
                                                  term_statement, limit, offset)
    return result
