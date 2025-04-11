from typing import Any

from esgvoc.core.db.models.project import Collection, TermKind
from esgvoc.core.exceptions import EsgvocValueError

KEY_SEPARATOR = ':'
FIELD_PART_SEPARATOR = '_'


def _generate_enum(collection: Collection, selected_field: str) -> list[str]:
    result: list[str] = list()
    for term in collection.terms:
        value = term.specs.get(selected_field, "*******")
        result.append(value)
    return result


def _generate_pattern(project_id: str, collection_id: str) -> str:
    # TODO: to be implemented!
    return ""


def _generate_properties(project_id: str, project_collections: list[Collection], field: str) -> tuple[str, dict]:
    key = f'{project_id}{KEY_SEPARATOR}{field}'
    value: dict[str, Any] = dict()
    value['type'] = 'string'
    property_value: str | list | None = None
    property_key: str | None = None
    field_splits = field.split(FIELD_PART_SEPARATOR)
    field_prefix = field_splits[0]
    if len(field_splits) > 1:
        field_postfix = FIELD_PART_SEPARATOR.join(field_splits[1:])
    else:
        field_postfix = None
    for collection in project_collections:
        if field in collection.id:
            postfix = collection.id.removeprefix(field)
            match postfix:
                case '_id' | '_label':
                    property_value = _generate_enum(collection=collection,
                                                    selected_field='description')
                    property_key = 'enum'
                case '':
                    match collection.term_kind:
                        case TermKind.PLAIN:
                            property_value = _generate_enum(collection=collection,
                                                            selected_field='drs_name')
                            property_key = 'enum'
                        case TermKind.PATTERN:
                            property_value = _generate_pattern(project_id=project_id,
                                                               collection_id=collection.id)
                            property_key = 'pattern'
                        case _:
                            msg = f'unsupported term kind {collection.term_kind} ' + \
                                  f"for field '{field}'"
                            raise EsgvocValueError(msg)
                case _:
                    raise EsgvocValueError(f"unsupported postfix '{postfix}'")
        elif field_prefix in collection.id:
            match field_postfix:
                case 'long_name':
                    property_value = _generate_enum(collection=collection, selected_field='long_name')
                    property_key = 'enum'
                case _:
                    raise EsgvocValueError(f'unsupported postfix {field_postfix}')
    if property_value is None or property_key is None:
        raise EsgvocValueError(f"enable to generate properties: unsupported field '{field}'")
    else:
        value[property_key] = property_value
    return (key, value)
