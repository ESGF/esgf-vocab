import re
from collections.abc import Iterable, Sequence

from sqlmodel import Session, and_, select

import esgvoc.api.universe as universe
import esgvoc.core.constants as constants
import esgvoc.core.service as service
from esgvoc.api._utils import (get_universe_session, instantiate_pydantic_term,
                               instantiate_pydantic_terms)
from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
from esgvoc.api.project_specs import ProjectSpecs
from esgvoc.api.report import (ProjectTermError, UniverseTermError,
                               ValidationError, ValidationReport)
from esgvoc.api.search import (MatchingTerm, SearchSettings,
                               _create_str_comparison_expression)
from esgvoc.core.db.connection import DBConnection
from esgvoc.core.db.models.mixins import TermKind
from esgvoc.core.db.models.project import Collection, Project, PTerm
from esgvoc.core.db.models.universe import UTerm

# [OPTIMIZATION]
_VALID_TERM_IN_COLLECTION_CACHE: dict[str, list[MatchingTerm]] = dict()
_VALID_VALUE_AGAINST_GIVEN_TERM_CACHE: dict[str, list[ValidationError]] = dict()


class DrsValidationException(Exception): ...


def get_project_specs(project_id: str) -> ProjectSpecs:
    project_specs = find_project(project_id)
    if not project_specs:
        msg = f'Unable to find project {project_id}'
        raise ValueError(msg)
    try:
        result = ProjectSpecs(**project_specs)
    except Exception as e:
        msg = f'Unable to read specs in project {project_id}'
        raise RuntimeError(msg) from e
    return result


def _get_project_connection(project_id: str) -> DBConnection|None:
    return service.state_service.projects[project_id].db_connection

def _get_project_session_with_exception(project_id: str) -> Session:
    if connection:=_get_project_connection(project_id):
        project_session = connection.create_session()
        return project_session
    else:
        raise ValueError(f'unable to find project {project_id}')


def _resolve_term(composite_term_part: dict,
                  universe_session: Session,
                  project_session: Session) -> UTerm|PTerm:
    # First find the term in the universe than in the current project
    term_id = composite_term_part[constants.TERM_ID_JSON_KEY]
    term_type = composite_term_part[constants.TERM_TYPE_JSON_KEY]
    uterms = universe._find_terms_in_data_descriptor(data_descriptor_id=term_type,
                                                     term_id=term_id,
                                                     session=universe_session,
                                                     settings=None)
    if uterms:
        return uterms[0]
    else:
        pterms = _find_terms_in_collection(collection_id=term_type,
                                           term_id=term_id,
                                           session=project_session,
                                           settings=None)
    if pterms:
        return pterms[0]
    else:
        msg = f'unable to find the term {term_id} in {term_type}'
        raise RuntimeError(msg)


def _get_composite_term_separator_parts(term: UTerm|PTerm) -> tuple[str, list]:
    separator = term.specs[constants.COMPOSITE_SEPARATOR_JSON_KEY]
    parts = term.specs[constants.COMPOSITE_PARTS_JSON_KEY]
    return separator, parts


# TODO: support optionality of parts of composite.
# It is backtrack possible for more than one missing parts.
def _valid_value_composite_term_with_separator(value: str,
                                               term: UTerm|PTerm,
                                               universe_session: Session,
                                               project_session: Session)\
                                                   -> list[ValidationError]:
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


def _transform_to_pattern(term: UTerm|PTerm,
                          universe_session: Session,
                          project_session: Session) -> str:
    match term.kind:
        case TermKind.PLAIN:
            if constants.DRS_SPECS_JSON_KEY in term.specs:
                result = term.specs[constants.DRS_SPECS_JSON_KEY]
            else:
                raise DrsValidationException(f"the term {term.id} doesn't have drs name. " +
                                             "Can't validate it.")
        case TermKind.PATTERN:
            result = term.specs[constants.PATTERN_JSON_KEY]
        case TermKind.COMPOSITE:
            separator, parts =  _get_composite_term_separator_parts(term)
            result = ""
            for part in parts:
                resolved_term = _resolve_term(part, universe_session, project_session)
                pattern = _transform_to_pattern(resolved_term, universe_session, project_session)
                result = f'{result}{pattern}{separator}'
            result = result.rstrip(separator)
        case _:
            raise NotImplementedError(f'unsupported term kind {term.kind}')
    return result


# TODO: support optionality of parts of composite.
# It is backtrack possible for more than one missing parts.
def _valid_value_composite_term_separator_less(value: str,
                                               term: UTerm|PTerm,
                                               universe_session: Session,
                                               project_session: Session)\
                                                   -> list[ValidationError]:
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
            msg = f'regex compilation error:\n{e}'
            raise ValueError(msg) from e
        match = regex.match(value)
        if match is None:
            result.append(_create_term_error(value, term))
        return result
    except Exception as e:
        msg = f'cannot validate separator less composite term {term.id}:\n{e}'
        raise RuntimeError(msg) from e


def _valid_value_for_composite_term(value: str,
                                    term: UTerm|PTerm,
                                    universe_session: Session,
                                    project_session: Session)\
                                        -> list[ValidationError]:
    result = list()
    separator, _ = _get_composite_term_separator_parts(term)
    if separator:
        result = _valid_value_composite_term_with_separator(value, term, universe_session,
                                                            project_session)
    else:
        result = _valid_value_composite_term_separator_less(value, term, universe_session,
                                                            project_session)
    return result


def _create_term_error(value: str, term: UTerm|PTerm) -> ValidationError:
    if isinstance(term, UTerm):
        return UniverseTermError(value=value, term=term.specs, term_kind=term.kind,
                                 data_descriptor_id=term.data_descriptor.id)
    else:
        return ProjectTermError(value=value, term=term.specs, term_kind=term.kind,
                                collection_id=term.collection.id)


def _valid_value(value: str,
                 term: UTerm|PTerm,
                 universe_session: Session,
                 project_session: Session) -> list[ValidationError]:
    result = list()
    match term.kind:
        case TermKind.PLAIN:
            if constants.DRS_SPECS_JSON_KEY in term.specs:
                if term.specs[constants.DRS_SPECS_JSON_KEY] != value:
                    result.append(_create_term_error(value, term))
            else:
                raise DrsValidationException(f"the term {term.id} doesn't have drs name. " +
                                             "Can't validate it.")
        case TermKind.PATTERN:
            # OPTIM: Pattern can be compiled and stored for further matching.
            pattern_match = re.match(term.specs[constants.PATTERN_JSON_KEY], value)
            if pattern_match is None:
                result.append(_create_term_error(value, term))
        case TermKind.COMPOSITE:
            result.extend(_valid_value_for_composite_term(value, term,
                                                          universe_session,
                                                          project_session))
        case _:
            raise NotImplementedError(f'unsupported term kind {term.kind}')
    return result


def _check_value(value: str) -> str:
    if not value or value.isspace():
        raise ValueError('value should be set')
    else:
        return value


def _search_plain_term_and_valid_value(value: str,
                                       collection_id: str,
                                       project_session: Session) \
                                        -> str|None:
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
                                        -> list[ValidationError]:
    # [OPTIMIZATION]
    key = value + project_id + collection_id + term_id
    if key in _VALID_VALUE_AGAINST_GIVEN_TERM_CACHE:
        result = _VALID_VALUE_AGAINST_GIVEN_TERM_CACHE[key]
    else:
        try:
            terms = _find_terms_in_collection(collection_id,
                                              term_id,
                                              project_session,
                                              None)
            if terms:
                term = terms[0]
                result = _valid_value(value, term, universe_session, project_session)
            else:
                raise ValueError(f'unable to find term {term_id} ' +
                                 f'in collection {collection_id}')
        except Exception as e:
            msg = f'unable to valid term {term_id} ' +\
                  f'in collection {collection_id}'
            raise RuntimeError(msg) from e
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
    the function raises a ValueError.

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
    :raises ValueError: If any of the provided ids is not found
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
    # [OPTIMIZATION]
    key = value + project_id + collection_id
    if key in _VALID_TERM_IN_COLLECTION_CACHE:
        result = _VALID_TERM_IN_COLLECTION_CACHE[key]
    else:
        value = _check_value(value)
        result = list()
        collections = _find_collections_in_project(collection_id,
                                                   project_session,
                                                   None)
        if collections:
            collection = collections[0]
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
            raise ValueError(msg)
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
    the function raises a ValueError.

    :param value: A value to be validated
    :type value: str
    :param project_id: A project id
    :type project_id: str
    :param collection_id: A collection id
    :type collection_id: str
    :returns: The list of terms that the value matches.
    :rtype: list[MatchingTerm]
    :raises ValueError: If any of the provided ids is not found
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

    If the `project_id` is not found, the function raises a ValueError.

    :param value: A value to be validated
    :type value: str
    :param project_id: A project id
    :type project_id: str
    :returns: The list of terms that the value matches.
    :rtype: list[MatchingTerm]
    :raises ValueError: If the `project_id` is not found
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


def _find_terms_in_collection(collection_id: str,
                              term_id: str,
                              session: Session,
                              settings: SearchSettings|None = None) -> Sequence[PTerm]:
    # Settings only apply on the term_id comparison.
    where_expression = _create_str_comparison_expression(field=PTerm.id,
                                                         value=term_id,
                                                         settings=settings)
    statement = select(PTerm).join(Collection).where(Collection.id==collection_id,
                                                     where_expression)
    results = session.exec(statement)
    result = results.all()
    return result


def find_terms_in_collection(project_id:str,
                             collection_id: str,
                             term_id: str,
                             settings: SearchSettings|None = None) \
                                -> list[DataDescriptor]:
    """
    Finds one or more terms, based on the specified search settings, in the given collection of a project.
    This function performs an exact match on the `project_id` and `collection_id`,
    and does **not** search for similar or related projects and collections.
    The given `term_id` is searched according to the search type specified in the parameter `settings`,
    which allows a flexible matching (e.g., `LIKE` may return multiple results).
    If the parameter `settings` is `None`, this function performs an exact match on the `term_id`.
    If any of the provided ids (`project_id`, `collection_id` or `term_id`) is not found,
    the function returns an empty list.

    Behavior based on search type:
        - `EXACT` and absence of `settings`: returns zero or one term instance in the list.
        - `REGEX`, `LIKE`, `STARTS_WITH` and `ENDS_WITH`: returns zero, one or more \
          term instances in the list.

    :param project_id: A project id
    :type project_id: str
    :param collection_id: A collection
    :type collection_id: str
    :param term_id: A term id to be found
    :type term_id: str
    :param settings: The search settings
    :type settings: SearchSettings|None
    :returns: A list of term instances. Returns an empty list if no matches are found.
    :rtype: list[DataDescriptor]
    """
    result: list[DataDescriptor] = list()
    if connection:=_get_project_connection(project_id):
        with connection.create_session() as session:
            terms = _find_terms_in_collection(collection_id, term_id, session, settings)
            instantiate_pydantic_terms(terms, result,
                                       settings.selected_term_fields if settings else None)
    return result


def _find_terms_from_data_descriptor_in_project(data_descriptor_id: str,
                                                term_id: str,
                                                session: Session,
                                                settings: SearchSettings|None = None) \
                                                   -> Sequence[PTerm]:
    # Settings only apply on the term_id comparison.
    where_expression = _create_str_comparison_expression(field=PTerm.id,
                                                         value=term_id,
                                                         settings=settings)
    statement = select(PTerm).join(Collection).where(Collection.data_descriptor_id==data_descriptor_id,
                                                     where_expression)
    results = session.exec(statement)
    result = results.all()
    return result


def find_terms_from_data_descriptor_in_project(project_id: str,
                                               data_descriptor_id: str,
                                               term_id: str,
                                               settings: SearchSettings|None = None) \
                                                  -> list[tuple[DataDescriptor, str]]:
    """
    Finds one or more terms in the given project which are instances of the given data descriptor
    in the universe, based on the specified search settings, in the given collection of a project.
    This function performs an exact match on the `project_id` and `data_descriptor_id`,
    and does **not** search for similar or related projects and data descriptors.
    The given `term_id` is searched according to the search type specified in the parameter `settings`,
    which allows a flexible matching (e.g., `LIKE` may return multiple results).
    If the parameter `settings` is `None`, this function performs an exact match on the `term_id`.
    If any of the provided ids (`project_id`, `data_descriptor_id` or `term_id`) is not found,
    the function returns an empty list.

    Behavior based on search type:
        - `EXACT` and absence of `settings`: returns zero or one term instance and \
          collection id in the list.
        - `REGEX`, `LIKE`, `STARTS_WITH` and `ENDS_WITH`: returns zero, one or more \
          term instances and collection ids in the list.

    :param project_id: A project id
    :type project_id: str
    :param data_descriptor_id: A data descriptor
    :type data_descriptor_id: str
    :param term_id: A term id to be found
    :type term_id: str
    :param settings: The search settings
    :type settings: SearchSettings|None
    :returns: A list of tuple of term instances and related collection ids. \
    Returns an empty list if no matches are found.
    :rtype: list[tuple[DataDescriptor, str]]
    """
    result = list()
    if connection:=_get_project_connection(project_id):
        with connection.create_session() as session:
            terms = _find_terms_from_data_descriptor_in_project(data_descriptor_id,
                                                                term_id,
                                                                session,
                                                                settings)
            for pterm in terms:
                collection_id = pterm.collection.id
                term = instantiate_pydantic_term(pterm,
                                                 settings.selected_term_fields if settings else None)
                result.append((term, collection_id))
    return result


def find_terms_from_data_descriptor_in_all_projects(data_descriptor_id: str,
                                                    term_id: str,
                                                    settings: SearchSettings|None = None) \
                                                    -> list[tuple[list[tuple[DataDescriptor, str]], str]]:
    """
    Finds one or more terms in all projects which are instances of the given data descriptor
    in the universe, based on the specified search settings, in the given collection of a project.
    This function performs an exact match on the `data_descriptor_id`,
    and does **not** search for similar or related data descriptors.
    The given `term_id` is searched according to the search type specified in the parameter `settings`,
    which allows a flexible matching (e.g., `LIKE` may return multiple results).
    If the parameter `settings` is `None`, this function performs an exact match on the `term_id`.
    If any of the provided ids (`data_descriptor_id` or `term_id`) is not found,
    the function returns an empty list.

    Behavior based on search type:
        - `EXACT` and absence of `settings`: returns zero or one term instance and \
          collection id in the list.
        - `REGEX`, `LIKE`, `STARTS_WITH` and `ENDS_WITH`: returns zero, one or more \
          term instances and collection ids in the list.

    :param data_descriptor_id: A data descriptor
    :type data_descriptor_id: str
    :param term_id: A term id to be found
    :type term_id: str
    :param settings: The search settings
    :type settings: SearchSettings|None
    :returns: A list of tuple of matching terms with their collection id, per project. \
    Returns an empty list if no matches are found.
    :rtype: list[tuple[list[tuple[DataDescriptor, str]], str]]
    """
    project_ids = get_all_projects()
    result: list[tuple[list[tuple[DataDescriptor, str]], str]] = list()
    for project_id in project_ids:
        matching_terms = find_terms_from_data_descriptor_in_project(project_id,
                                                                    data_descriptor_id,
                                                                    term_id,
                                                                    settings)
        if matching_terms:
            result.append((matching_terms, project_id))
    return result


def _find_terms_in_project(term_id: str,
                           session: Session,
                           settings: SearchSettings|None) -> Sequence[PTerm]:
    where_expression = _create_str_comparison_expression(field=PTerm.id,
                                                         value=term_id,
                                                         settings=settings)
    statement = select(PTerm).where(where_expression)
    results = session.exec(statement).all()
    return results


def find_terms_in_all_projects(term_id: str,
                               settings: SearchSettings|None = None) \
                                  -> list[DataDescriptor]:
    """
    Finds one or more terms, based on the specified search settings, in all projects.
    The given `term_id` is searched according to the search type specified in the parameter `settings`,
    which allows a flexible matching (e.g., `LIKE` may return multiple results).
    If the parameter `settings` is `None`, this function performs an exact match on the `term_id`.
    Terms are unique within a collection but may have some synonyms within a project.
    If the provided `term_id` is not found, the function returns an empty list.

    :param term_id: A term id to be found
    :type term_id: str
    :param settings: The search settings
    :type settings: SearchSettings|None
    :returns: A list of term instances. Returns an empty list if no matches are found.
    :rtype: list[DataDescriptor]
    """
    project_ids = get_all_projects()
    result = list()
    for project_id in project_ids:
        result.extend(find_terms_in_project(project_id, term_id, settings))
    return result


def find_terms_in_project(project_id: str,
                          term_id: str,
                          settings: SearchSettings|None = None) \
                            -> list[DataDescriptor]:
    """
    Finds one or more terms, based on the specified search settings, in a project.
    This function performs an exact match on the `project_id` and
    does **not** search for similar or related projects.
    The given `term_id` is searched according to the search type specified in the parameter `settings`,
    which allows a flexible matching (e.g., `LIKE` may return multiple results).
    If the parameter `settings` is `None`, this function performs an exact match on the `term_id`.
    Terms are unique within a collection but may have some synonyms within a project.
    If any of the provided ids (`project_id` or `term_id`) is not found, the function returns
    an empty list.

    :param project_id: A project id
    :type project_id: str
    :param term_id: A term id to be found
    :type term_id: str
    :param settings: The search settings
    :type settings: SearchSettings|None
    :returns: A list of term instances. Returns an empty list if no matches are found.
    :rtype: list[DataDescriptor]
    """
    result: list[DataDescriptor] = list()
    if connection:=_get_project_connection(project_id):
        with connection.create_session() as session:
            terms = _find_terms_in_project(term_id, session, settings)
            instantiate_pydantic_terms(terms, result,
                                       settings.selected_term_fields if settings else None)
    return result


def get_all_terms_in_collection(project_id: str,
                                collection_id: str,
                                selected_term_fields: Iterable[str]|None = None)\
                                   -> list[DataDescriptor]:
    """
    Gets all terms of the given collection of a project.
    This function performs an exact match on the `project_id` and `collection_id`,
    and does **not** search for similar or related projects and collections.
    If any of the provided ids (`project_id` or `collection_id`) is not found, the function
    returns an empty list.

    :param project_id: A project id
    :type project_id: str
    :param collection_id: A collection id
    :type collection_id: str
    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned.
    :type selected_term_fields: Iterable[str]|None
    :returns: a list of term instances. Returns an empty list if no matches are found.
    :rtype: list[DataDescriptor]
    """
    result = list()
    if connection:=_get_project_connection(project_id):
        with connection.create_session() as session:
            collections = _find_collections_in_project(collection_id,
                                                       session,
                                                       None)
            if collections:
                collection = collections[0]
                result = _get_all_terms_in_collection(collection, selected_term_fields)
    return result


def _find_collections_in_project(collection_id: str,
                                 session: Session,
                                 settings: SearchSettings|None) \
                                    -> Sequence[Collection]:
    where_exp = _create_str_comparison_expression(field=Collection.id,
                                                  value=collection_id,
                                                  settings=settings)
    statement = select(Collection).where(where_exp)
    results = session.exec(statement)
    result = results.all()
    return result


def find_collections_in_project(project_id: str,
                                collection_id: str,
                                settings: SearchSettings|None = None) \
                                    -> list[dict]:
    """
    Finds one or more collections of the given project.
    This function performs an exact match on the `project_id` and
    does **not** search for similar or related projects.
    The given `collection_id` is searched according to the search type specified in
    the parameter `settings`,
    which allows a flexible matching (e.g., `LIKE` may return multiple results).
    If the parameter `settings` is `None`, this function performs an exact match on the `collection_id`.
    If any of the provided ids (`project_id` or `collection_id`) is not found, the function returns
    an empty list.

    Behavior based on search type:
        - `EXACT` and absence of `settings`: returns zero or one collection context in the list.
        - `REGEX`, `LIKE`, `STARTS_WITH` and `ENDS_WITH`: returns zero, one or more \
          collection contexts in the list.

    :param project_id: A project id
    :type project_id: str
    :param collection_id: A collection id to be found
    :type collection_id: str
    :param settings: The search settings
    :type settings: SearchSettings|None
    :returns: A list of collection contexts. Returns an empty list if no matches are found.
    :rtype: list[dict]
    """
    result = list()
    if connection:=_get_project_connection(project_id):
        with connection.create_session() as session:
            collections = _find_collections_in_project(collection_id,
                                                       session,
                                                       settings)
            for collection in collections:
                result.append(collection.context)
    return result


def _get_all_collections_in_project(session: Session) -> list[Collection]:
    project = session.get(Project, constants.SQLITE_FIRST_PK)
    # Project can't be missing if session exists.
    return project.collections # type: ignore


def get_all_collections_in_project(project_id: str) -> list[str]:
    """
    Gets all collections of the given project.
    This function performs an exact match on the `project_id` and
    does **not** search for similar or related projects.
    If the provided `project_id` is not found, the function returns an empty list.

    :param project_id: A project id
    :type project_id: str
    :returns: A list of collection ids. Returns an empty list if no matches are found.
    :rtype: list[str]
    """
    result = list()
    if connection:=_get_project_connection(project_id):
        with connection.create_session() as session:
            collections = _get_all_collections_in_project(session)
            for collection in collections:
                result.append(collection.id)
    return result


def _get_all_terms_in_collection(collection: Collection,
                                 selected_term_fields: Iterable[str]|None) -> list[DataDescriptor]:
    result: list[DataDescriptor] = list()
    instantiate_pydantic_terms(collection.terms, result, selected_term_fields)
    return result


def get_all_terms_in_project(project_id: str,
                             selected_term_fields: Iterable[str]|None = None) -> list[DataDescriptor]:
    """
    Gets all terms of the given project.
    This function performs an exact match on the `project_id` and
    does **not** search for similar or related projects.
    Terms are unique within a collection but may have some synonyms in a project.
    If the provided `project_id` is not found, the function returns an empty list.

    :param project_id: A project id
    :type project_id: str
    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned.
    :type selected_term_fields: Iterable[str]|None
    :returns: A list of term instances. Returns an empty list if no matches are found.
    :rtype: list[DataDescriptor]
    """
    result = list()
    if connection:=_get_project_connection(project_id):
        with connection.create_session() as session:
            collections = _get_all_collections_in_project(session)
            for collection in collections:
                # Term may have some synonyms in a project.
                result.extend(_get_all_terms_in_collection(collection, selected_term_fields))
    return result


def get_all_terms_in_all_projects(selected_term_fields: Iterable[str]|None = None) \
                                                                            -> list[DataDescriptor]:
    """
    Gets all terms of all projects.

    :param selected_term_fields: A list of term fields to select or `None`. If `None`, all the \
    fields of the terms are returned.
    :type selected_term_fields: Iterable[str]|None
    :returns: A list of term instances.
    :rtype: list[DataDescriptor]
    """
    project_ids = get_all_projects()
    result = list()
    for project_id in project_ids:
        result.extend(get_all_terms_in_project(project_id, selected_term_fields))
    return result


def find_project(project_id: str) -> dict|None:
    """
    Finds a project.
    This function performs an exact match on the `project_id` and
    does **not** search for similar or related projects.
    If the provided `project_id` is not found, the function returns `None`.

    :param project_id: A project id to be found
    :type project_id: str
    :returns: The specs of the project found. Returns `None` if no matches are found.
    :rtype: dict|None
    """
    result = None
    if connection:=_get_project_connection(project_id):
        with connection.create_session() as session:
            project = session.get(Project, constants.SQLITE_FIRST_PK)
            # Project can't be missing if session exists.
            result = project.specs # type: ignore
    return result


def get_all_projects() -> list[str]:
    """
    Gets all projects.

    :returns: A list of project ids.
    :rtype: list[str]
    """
    return list(service.state_service.projects.keys())


if __name__ == "__main__":
    settings = SearchSettings()
    settings.selected_term_fields = ('id', 'drs_name')
    settings.case_sensitive = False
    matching_terms = find_terms_from_data_descriptor_in_all_projects('organisation', 'IpsL', settings)
    print(matching_terms)
