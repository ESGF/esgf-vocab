import json
from dataclasses import dataclass
from json import JSONEncoder
from pathlib import Path

from sqlmodel import Session

from esgvoc.api import projects, search
from esgvoc.api.project_specs import CatalogProperty
from esgvoc.core.constants import DRS_SPECS_JSON_KEY, PATTERN_JSON_KEY
from esgvoc.core.db.models.project import PCollection, TermKind
from esgvoc.core.exceptions import EsgvocNotFoundError, EsgvocNotImplementedError

KEY_SEPARATOR = ':'
JSON_SCHEMA_TEMPLATE_DIR_PATH = Path(__file__).parent
JSON_SCHEMA_TEMPLATE_FILE_NAME = 'template.json'
JSON_INDENTATION = 2


@dataclass
class _CatalogProperty:
    field_name: str
    field_value: dict
    is_required: bool


class _SetJsonEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, set):
            return list(o)
        else:
            return super().default(self, o)


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


class CatalogPropertiesJsonTranslator:
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

    def _translate_property_value(self, source_collection: str, source_collection_key: str) \
            -> tuple[str, str | set[str]]:
        property_value: str | set[str]
        if source_collection not in self.collections:
            # DEBUG
            # raise EsgvocNotFoundError(f"collection '{source_collection}' is not found")
            print(f"collection '{source_collection}' is not found")
            return 'enum', {}
        collection = self.collections[source_collection]
        match collection.term_kind:
            case TermKind.PLAIN:
                property_value = _process_plain(collection=collection,
                                                selected_field=source_collection_key)
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
                msg = f"unsupported term kind '{collection.term_kind}'"
                raise EsgvocNotImplementedError(msg)
        return property_key, property_value

    def translate_property(self, catalog_property: CatalogProperty) -> _CatalogProperty:
        if catalog_property.source_collection_key is None:
            source_collection_key = DRS_SPECS_JSON_KEY
        else:
            source_collection_key = catalog_property.source_collection_key
        property_key, property_value = self._translate_property_value(catalog_property.source_collection,
                                                                      source_collection_key)
        field_value = dict()
        if 'array' in catalog_property.catalog_field_value_type:
            field_value['type'] = 'array'
            root_property = dict()
            field_value['items'] = root_property
            root_property['type'] = catalog_property.catalog_field_value_type.split('_')[0]
        else:
            field_value['type'] = catalog_property.catalog_field_value_type
            root_property = field_value

        root_property[property_key] = property_value

        if catalog_property.catalog_field_name is None:
            attribute_name = catalog_property.source_collection
        else:
            attribute_name = catalog_property.catalog_field_name
        field_name = CatalogPropertiesJsonTranslator._translate_field_name(self.project_id, attribute_name)
        return _CatalogProperty(field_name=field_name,
                                field_value=field_value,
                                is_required=catalog_property.is_required)

    @staticmethod
    def _translate_field_name(project_id: str, attribute_name) -> str:
        return f'{project_id}{KEY_SEPARATOR}{attribute_name}'


def _inject_catalog_properties(field_definitions_node: dict,
                               catalog_properties: list[_CatalogProperty],
                               required_field_declarations_node: list[dict]):
    for catalog_property in catalog_properties:
        if catalog_property.is_required:
            required_field_declarations_node.append({"required": [catalog_property.field_name]})
        field_definitions_node[catalog_property.field_name] = catalog_property.field_value


def _catalog_properties_json_processor(property_translator: CatalogPropertiesJsonTranslator,
                                       properties: list[CatalogProperty],
                                       field_definitions_node: dict,
                                       required_field_declarations_node: list[dict]) -> None:
    catalog_properties: list[_CatalogProperty] = list()
    for dataset_property_spec in properties:
        # DEBUG
        if dataset_property_spec.source_collection == 'member_id':
            continue
        ##
        catalog_property = property_translator.translate_property(dataset_property_spec)
        catalog_properties.append(catalog_property)
    _inject_catalog_properties(
        field_definitions_node=field_definitions_node,
        catalog_properties=catalog_properties,
        required_field_declarations_node=required_field_declarations_node)


def _project_id_json_processor(node: dict, key: str, project_id, is_capital_letters: bool) -> None:
    template = node[key]
    node[key] = template.format(project_id=project_id.upper() if is_capital_letters else project_id)


def _pattern_properties_json_processor(root_node: dict, project_id: str) -> None:
    pattern_properties_node = root_node['definitions']['item_fields']
    pattern_properties = pattern_properties_node['patternProperties']
    key, value = list(pattern_properties.items())[0]
    key = key.format(project_id=project_id)
    pattern_properties_node['patternProperties'] = {key: value}


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
    template_file_path = JSON_SCHEMA_TEMPLATE_DIR_PATH.joinpath(JSON_SCHEMA_TEMPLATE_FILE_NAME)
    if template_file_path.exists():
        project_specs = projects.get_project(project_id)
        if project_specs is not None:
            if project_specs.catalog_specs is not None:
                with open(file=template_file_path, mode='r') as file:
                    root_node = json.load(file)
                property_translator = CatalogPropertiesJsonTranslator(project_id)

                # Process title.
                _project_id_json_processor(root_node, 'title', project_id, True)

                # Process description.
                _project_id_json_processor(root_node, 'description', project_id, True)

                # Process schema id.
                _project_id_json_processor(root_node, '$id', project_id, False)

                # Process pattern properties.
                _pattern_properties_json_processor(root_node, project_id)

                # Process catalog properties.

                # Process id & collection common fields.
                # Process dataset id.

                # Process catalog file properties.
                catalog_file_field_definitions_node = \
                    root_node['definitions']['asset_fields']['properties']
                catalog_file_required_field_declaration_node = \
                    root_node['definitions']['require_asset_fields']['allOf']
                _catalog_properties_json_processor(property_translator,
                                                   project_specs.catalog_specs.file_properties,
                                                   catalog_file_field_definitions_node,
                                                   catalog_file_required_field_declaration_node)
                # Process catalog dataset properties.
                catalog_dataset_field_definitions_node = \
                    root_node['definitions']['item_fields']['properties']
                catalog_dataset_required_field_declarations_node = \
                    root_node['definitions']['require_item_fields']['allOf']
                _catalog_properties_json_processor(property_translator,
                                                   project_specs.catalog_specs.dataset_properties,
                                                   catalog_dataset_field_definitions_node,
                                                   catalog_dataset_required_field_declarations_node)
                del property_translator

                return json.dumps(root_node, indent=JSON_INDENTATION, cls=_SetJsonEncoder)
            else:
                raise EsgvocNotFoundError(f"catalog properties for the project '{project_id}' " +
                                          "are missing")
        else:
            raise EsgvocNotFoundError(f"unknown project '{project_id}'")
    else:
        raise EsgvocNotFoundError('missing json schema template')
