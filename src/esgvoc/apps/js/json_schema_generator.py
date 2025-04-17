import json
from pathlib import Path
from typing import Any

from sqlmodel import Session

from esgvoc.api import projects, search
from esgvoc.core.constants import PATTERN_JSON_KEY
from esgvoc.core.db.models.project import Collection, TermKind
from esgvoc.core.exceptions import EsgvocValueError

KEY_SEPARATOR = ':'
FIELD_PART_SEPARATOR = '_'
LONG_NAME_POSTFIX = '_long_name'
JSON_SCHEMA_TEMPLATE_DIR_PATH = Path(__file__).parent
JSON_SCHEMA_TEMPLATE_FILE_NAME_TEMPLATE = '{project_id}_template.json'
JSON_INDENTATION = 4


def _process_plain(collection: Collection, selected_field: str) -> list[str]:
    result: list[str] = list()
    for term in collection.terms:
        value = term.specs.get(selected_field, 'None')
        result.append(value)
    return result


def _process_composite(collection: Collection, universe_session: Session,
                       project_session: Session) -> str:
    result = ""
    for term in collection.terms:
        _, parts = projects._get_composite_term_separator_parts(term)
        for part in parts:
            resolved_term = projects._resolve_term(part, universe_session, project_session)
            if resolved_term.kind == TermKind.PATTERN:
                result += resolved_term.specs[PATTERN_JSON_KEY]
            else:
                raise NotImplementedError(f'{term.kind} term is not supported yet')
    # Patterns terms are meant to be validated individually.
    # So their regex are defined as a whole (begins by a ^, ends by a $).
    # As the pattern is a concatenation of plain or regex, multiple ^ and $ can exist.
    # The later, must be removed.
    result = result.replace('^', '').replace('$', '')
    result = f'^{result}$'
    return result


def _match_collection(field: str, collections: list[Collection], universe_session: Session,
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
                          f"for field '{field}'"
                    raise EsgvocValueError(msg)
            break
    return property_key, property_value


def _generate_property(project_id: str, collections: list[Collection], schema_field: str,
                       universe_session: Session, project_session: Session) -> tuple[str, dict]:
    key = f'{project_id}{KEY_SEPARATOR}{schema_field}'
    value: dict[str, Any] = dict()
    value['type'] = 'string'
    property_value: str | list | None = None
    property_key: str | None = None
    # 1. Process "long name" fields.
    if LONG_NAME_POSTFIX in schema_field:
        recomputed_schema_field = schema_field.removesuffix(LONG_NAME_POSTFIX)
        property_key, property_value = _match_collection(recomputed_schema_field,
                                                         collections,
                                                         universe_session,
                                                         project_session)
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
                        case '_id' | '_label':
                            property_value = _process_plain(collection=collection,
                                                            selected_field='description')
                            property_key = 'enum'
                            break
    if property_value is None or property_key is None:
        raise EsgvocValueError(f"unsupported field '{schema_field}'")
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
                try:
                    property = _generate_property(project_id=project_id, collections=collections,
                                                  schema_field=schema_field,
                                                  universe_session=universe_session,
                                                  project_session=project_session)
                    properties.append(property)
                except Exception as e:  # DEBUG
                    print(e)
                    continue
        _inject_properties(root, properties)
        return json.dumps(root, indent=JSON_INDENTATION)
    else:
        raise NotImplementedError(f"project '{project_id}' is not supported yet")
