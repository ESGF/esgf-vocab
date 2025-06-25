import contextlib
import json
from json import JSONEncoder
from pathlib import Path
from typing import Iterable

from sqlmodel import Session

from esgvoc.api import projects, search
from esgvoc.api.project_specs import (
    GlobalAttributeSpecBase,
    GlobalAttributeSpecSpecific,
    GlobalAttributeVisitor,
)
from esgvoc.core.constants import DRS_SPECS_JSON_KEY, PATTERN_JSON_KEY
from esgvoc.core.db.models.project import PCollection, TermKind
from esgvoc.core.exceptions import EsgvocNotFoundError, EsgvocNotImplementedError

KEY_SEPARATOR = ':'
JSON_SCHEMA_TEMPLATE_DIR_PATH = Path(__file__).parent
JSON_SCHEMA_TEMPLATE_FILE_NAME_TEMPLATE = '{project_id}_template.json'
JSON_INDENTATION = 2


def _process_plain(collection: PCollection, selected_field: str) -> set[str]:
    result: set[str] = set()
    for term in collection.terms:
        if selected_field in term.specs:
            value = term.specs[selected_field]
            result.add(value)
        else:
            raise EsgvocNotFoundError(f'missing key {selected_field} for term {term.id} in ' +
                                      f'collection {collection.id}')
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


def _process_pattern(collection: PCollection) -> str:
    # The generation of the value of the field pattern for the collections with more than one term
    # is not specified yet.
    if len(collection.terms) == 1:
        term = collection.terms[0]
        return term.specs[PATTERN_JSON_KEY]
    else:
        msg = f"unsupported collection of term pattern with more than one term for '{collection.id}'"
        raise EsgvocNotImplementedError(msg)


def _generate_attribute_key(project_id: str, attribute_name) -> str:
    return f'{project_id}{KEY_SEPARATOR}{attribute_name}'


class JsonPropertiesVisitor(GlobalAttributeVisitor, contextlib.AbstractContextManager):
    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        # Project session can't be None here.
        self.universe_session: Session = search.get_universe_session()
        self.project_session: Session = projects._get_project_session_with_exception(project_id)
        self.collections: dict[str, PCollection] = dict()
        for collection in projects._get_all_collections_in_project(self.project_session):
            self.collections[collection.id] = collection

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.project_session.close()
        self.universe_session.close()
        if exception_type is not None:
            raise exception_value
        return True

    def _generate_attribute_property(self, attribute_name: str, source_collection: str,
                                     selected_field: str) -> tuple[str, str | set[str]]:
        property_value: str | set[str]
        property_key: str
        if source_collection not in self.collections:
            raise EsgvocNotFoundError(f"collection '{source_collection}' referenced by attribute " +
                                      f"{attribute_name} is not found")
        collection = self.collections[source_collection]
        match collection.term_kind:
            case TermKind.PLAIN:
                property_value = _process_plain(collection=collection,
                                                selected_field=selected_field)
                property_key = 'enum'
            case TermKind.COMPOSITE:
                property_value = _process_composite(collection=collection,
                                                    universe_session=self.universe_session,
                                                    project_session=self.project_session)
                property_key = 'pattern'
            case TermKind.PATTERN:
                property_value = _process_pattern(collection)
                property_key = 'pattern'
            case _:
                msg = f"unsupported term kind '{collection.term_kind}' " + \
                      f"for global attribute {attribute_name}"
                raise EsgvocNotImplementedError(msg)
        return property_key, property_value

    def visit_base_attribute(self, attribute_name: str, attribute: GlobalAttributeSpecBase) \
            -> tuple[str, dict[str, str | set[str]]]:
        attribute_key = _generate_attribute_key(self.project_id, attribute_name)
        attribute_properties: dict[str, str | set[str]] = dict()
        attribute_properties['type'] = attribute.value_type.value
        property_key, property_value = self._generate_attribute_property(attribute_name,
                                                                         attribute.source_collection,
                                                                         DRS_SPECS_JSON_KEY)
        attribute_properties[property_key] = property_value
        return attribute_key, attribute_properties

    def visit_specific_attribute(self, attribute_name: str, attribute: GlobalAttributeSpecSpecific) \
            -> tuple[str, dict[str, str | set[str]]]:
        attribute_key = _generate_attribute_key(self.project_id, attribute_name)
        attribute_properties: dict[str, str | set[str]] = dict()
        attribute_properties['type'] = attribute.value_type.value
        property_key, property_value = self._generate_attribute_property(attribute_name,
                                                                         attribute.source_collection,
                                                                         attribute.specific_key)
        attribute_properties[property_key] = property_value
        return attribute_key, attribute_properties


def _inject_global_attributes(json_root: dict, project_id: str, attribute_names: Iterable[str]) -> None:
    attribute_properties = list()
    for attribute_name in attribute_names:
        attribute_key = _generate_attribute_key(project_id, attribute_name)
        attribute_properties.append({"required": [attribute_key]})
    json_root['definitions']['require_any']['anyOf'] = attribute_properties


def _inject_properties(json_root: dict, properties: list[tuple]) -> None:
    for property in properties:
        json_root['definitions']['fields']['properties'][property[0]] = property[1]


class SetEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, set):
            return list(o)
        else:
            return super().default(self, o)


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
        project_specs = projects.get_project(project_id)
        if project_specs:
            if project_specs.global_attributes_specs:
                with open(file=template_file_path, mode='r') as file, \
                     JsonPropertiesVisitor(project_id) as visitor:
                    file_content = file.read()
                    root = json.loads(file_content)
                    properties: list[tuple[str, dict[str, str | set[str]]]] = list()
                    for attribute_name, attribute in project_specs.global_attributes_specs.items():
                        attribute_key, attribute_properties = attribute.accept(attribute_name, visitor)
                        properties.append((attribute_key, attribute_properties))
                _inject_properties(root, properties)
                _inject_global_attributes(root, project_id, project_specs.global_attributes_specs.keys())
                return json.dumps(root, indent=JSON_INDENTATION, cls=SetEncoder)
            else:
                raise EsgvocNotFoundError(f"global attributes for the project '{project_id}' " +
                                          "are not provided")
        else:
            raise EsgvocNotFoundError(f"specs of project '{project_id}' is not found")
    else:
        raise EsgvocNotFoundError(f"template for project '{project_id}' is not found")
