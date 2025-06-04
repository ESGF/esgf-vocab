import json
from pathlib import Path
from typing import Any

from sqlmodel import Session

from esgvoc.api import projects, search
from esgvoc.core.constants import PATTERN_JSON_KEY
from esgvoc.core.db.models.project import PCollection, TermKind
from esgvoc.core.exceptions import EsgvocNotFoundError, EsgvocNotImplementedError

KEY_SEPARATOR = ':'
FIELD_PART_SEPARATOR = '_'
LONG_NAME_POSTFIX = '_long_name'
JSON_SCHEMA_TEMPLATE_DIR_PATH = Path(__file__).parent
JSON_SCHEMA_TEMPLATE_FILE_NAME_TEMPLATE = '{project_id}_template.json'
JSON_INDENTATION = 4


def _process_plain(collection: PCollection, selected_field: str) -> list[str]:
    result: list[str] = list()
    for term in collection.terms:
        if selected_field in term.specs:
            value = term.specs[selected_field]
            result.append(value)
        else:
            raise EsgvocNotFoundError(f'missing key {selected_field} for term {term.id}')
    return result


def _process_composite(collection: PCollection, universe_session: Session,
                       project_session: Session) -> str:
    result = ""
    for term in collection.terms:
        _, parts = projects._get_composite_term_separator_parts(term)
        for part in parts:
            resolved_term = projects._resolve_term(part, universe_session, project_session)
            if resolved_term.kind == TermKind.PATTERN:
                result += resolved_term.specs[PATTERN_JSON_KEY]
            else:
                raise EsgvocNotImplementedError(f'{term.kind} term is not supported yet')
    # Patterns terms are meant to be validated individually.
    # So their regex are defined as a whole (begins by a ^, ends by a $).
    # As the pattern is a concatenation of plain or regex, multiple ^ and $ can exist.
    # The later, must be removed.
    result = result.replace('^', '').replace('$', '')
    result = f'^{result}$'
    return result


def _match_collection(field: str, collections: list[PCollection], universe_session: Session,
                      project_session: Session) -> tuple[str | None, str | list | None]:
    property_value: str | list | None = None
    property_key: str | None = None
    for collection in collections:
        if field == collection.id:
            match collection.term_kind:
                case TermKind.PLAIN:
                    property_value = _process_plain(collection=collection,
                                                    selected_field='drs_name')
                    property_key = 'enum'
                case TermKind.COMPOSITE:
                    property_value = _process_composite(collection=collection,
                                                        universe_session=universe_session,
                                                        project_session=project_session)
                    property_key = 'pattern'
                case _:
                    msg = f'unsupported term kind {collection.term_kind} ' + \
                          f"for schema field '{field}'"
                    raise EsgvocNotImplementedError(msg)
            break
    return property_key, property_value


def _generate_property(project_id: str, collections: list[PCollection], schema_field: str,
                       universe_session: Session, project_session: Session) -> tuple[str, dict]:
    key = f'{project_id}{KEY_SEPARATOR}{schema_field}'
    value: dict[str, Any] = dict()
    value['type'] = 'string'
    property_value: str | list | None = None
    property_key: str | None = None
    # 1. Process "long name" fields.
    if LONG_NAME_POSTFIX in schema_field:
        recomputed_schema_field = schema_field.removesuffix(LONG_NAME_POSTFIX)
        matched_collection = projects._get_collection_in_project(collection_id=recomputed_schema_field,
                                                                 session=project_session)
        if matched_collection:
            property_value = _process_plain(collection=matched_collection, selected_field='long_name')
            property_key = 'enum'
        else:
            raise EsgvocNotFoundError(f"collection '{recomputed_schema_field}' not found")
    else:
        # 2. Process schema_fields that are collection ids. (e.g. of sub_experiment_id).
        property_key, property_value = _match_collection(schema_field,
                                                         collections,
                                                         universe_session,
                                                         project_session)
        if property_value is None or property_key is None:
            # 3. Process schema_fields that are part of collection ids.
            for collection in collections:
                if schema_field in collection.id:
                    postfix = collection.id.removeprefix(schema_field)
                    match postfix:
                        case '_id' | '_label':  # Process "description" fields.
                            property_value = _process_plain(collection=collection,
                                                            selected_field='description')
                            property_key = 'enum'
                            break
    if property_value is None or property_key is None:
        raise EsgvocNotImplementedError(f"unsupported schema field '{schema_field}'")
    else:
        value[property_key] = property_value
    return (key, value)


def _get_schema_fields(json_root: dict) -> list[str]:
    result = list()
    objs = json_root['definitions']['require_any']['anyOf']
    for obj in objs:
        key = obj['required'][0]
        collection_name = key.split(KEY_SEPARATOR)[1]
        result.append(collection_name)
    return result


def _inject_properties(json_root: dict, properties: list[tuple]) -> None:
    for property in properties:
        json_root['definitions']['fields']['properties'][property[0]] = property[1]


def generate_json_schema(project_id: str) -> str:
    """
    Generate json schema for the given project.

    :param project_id: The id of the given project.
    :type project_id: str
    :returns: The content of a json schema
    :rtype: str
    :raises EsgvocNotFoundError: On missing information
    :raises EsgvocNotImplementedError: On unexpected operations
    """
    file_name = JSON_SCHEMA_TEMPLATE_FILE_NAME_TEMPLATE.format(project_id=project_id)
    template_file_path = JSON_SCHEMA_TEMPLATE_DIR_PATH.joinpath(file_name)
    if template_file_path.exists():
        with open(file=template_file_path, mode='r') as file:
            file_content = file.read()
        root = json.loads(file_content)
        schema_fields = _get_schema_fields(root)
        properties = list()
        # Connection can't be None here.
        with search.get_universe_session() as universe_session, \
             projects._get_project_session_with_exception(project_id) as project_session:
            collections = projects._get_all_collections_in_project(project_session)
            for schema_field in schema_fields:
                property = _generate_property(project_id=project_id, collections=collections,
                                              schema_field=schema_field,
                                              universe_session=universe_session,
                                              project_session=project_session)
                properties.append(property)
        _inject_properties(root, properties)
        return json.dumps(root, indent=JSON_INDENTATION)
    else:
        raise EsgvocNotFoundError(f"project '{project_id}' is not supported/found yet")
