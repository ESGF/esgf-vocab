import json
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from sqlmodel import Session

from esgvoc.api import projects, search
from esgvoc.api.project_specs import CatalogProperty, DrsType
from esgvoc.core.constants import DRS_SPECS_JSON_KEY, PATTERN_JSON_KEY
from esgvoc.core.db.models.project import PCollection, PTerm, TermKind
from esgvoc.core.exceptions import EsgvocException, EsgvocNotFoundError, EsgvocNotImplementedError, EsgvocValueError

KEY_SEPARATOR = ':'
TEMPLATE_DIR_NAME = 'templates'
TEMPLATE_DIR_PATH = Path(__file__).parent.joinpath(TEMPLATE_DIR_NAME)
TEMPLATE_FILE_NAME = 'template.jinja'
JSON_INDENTATION = 2


@dataclass
class _CatalogProperty:
    field_name: str
    field_value: dict
    is_required: bool


def _process_col_plain_terms(collection: PCollection, source_collection_key: str) -> tuple[str, list[str]]:
    property_values: set[str] = set()
    for term in collection.terms:
        property_key, property_value = _process_plain_term(term, source_collection_key)
        property_values.add(property_value)
    return property_key, list(property_values)  # type: ignore


def _process_plain_term(term: PTerm, source_collection_key: str) -> tuple[str, str]:
    if source_collection_key in term.specs:
        property_value = term.specs[source_collection_key]
    else:
        raise EsgvocNotFoundError(f'missing key {source_collection_key} for term {term.id} in ' +
                                  f'collection {term.collection.id}')
    return 'enum', property_value


def _process_col_composite_terms(collection: PCollection, universe_session: Session,
                                 project_session: Session) -> tuple[str, list[str]]:
    result = set()
    for term in collection.terms:
        property_key, property_value = _process_composite_term(term, universe_session,
                                                               project_session)
        result.add(property_value)
    return property_key, list(result)  # type: ignore


def _process_composite_term(term: PTerm, universe_session: Session,
                            project_session: Session) -> tuple[str, str]:
    result = ""
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
    return 'pattern', result


def _process_col_pattern_terms(collection: PCollection) -> tuple[str, str]:
    # The generation of the value of the field pattern for the collections with more than one term
    # is not specified yet.
    if len(collection.terms) == 1:
        term = collection.terms[0]
        return _process_pattern_term(term)
    else:
        msg = f"unsupported collection of term pattern with more than one term for '{collection.id}'"
        raise EsgvocNotImplementedError(msg)


def _process_pattern_term(term: PTerm) -> tuple[str, str]:
    return 'pattern', term.specs[PATTERN_JSON_KEY]


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

    def _translate_property_value(self, catalog_property: CatalogProperty) -> tuple[str, str | list[str]]:
        property_value: str | list[str]
        if catalog_property.source_collection not in self.collections:
            # DEBUG
            # raise EsgvocNotFoundError(f"collection '{source_collection}' is not found")
            print(f"collection '{catalog_property.source_collection}' is not found")
            return 'enum', {}

        if catalog_property.source_collection_key is None:
            source_collection_key = DRS_SPECS_JSON_KEY
        else:
            source_collection_key = catalog_property.source_collection_key

        if catalog_property.source_collection_term is None:
            collection = self.collections[catalog_property.source_collection]
            match collection.term_kind:
                case TermKind.PLAIN:
                    property_key, property_value = _process_col_plain_terms(
                        collection=collection,
                        source_collection_key=source_collection_key)
                case TermKind.COMPOSITE:
                    property_key, property_value = _process_col_composite_terms(
                        collection=collection,
                        universe_session=self.universe_session,
                        project_session=self.project_session)
                case TermKind.PATTERN:
                    property_key, property_value = _process_col_pattern_terms(collection)
                case _:
                    msg = f"unsupported term kind '{collection.term_kind}'"
                    raise EsgvocNotImplementedError(msg)
        else:
            pterm_found = projects._get_term_in_collection(
                session=self.project_session,
                collection_id=catalog_property.source_collection,
                term_id=catalog_property.source_collection_term)
            if pterm_found is None:
                raise EsgvocValueError(f"term '{catalog_property.source_collection_term}' is not " +
                                       f"found in collection '{catalog_property.source_collection}'")
            match pterm_found.kind:
                case TermKind.PLAIN:
                    property_key, property_value = _process_plain_term(
                        term=pterm_found,
                        source_collection_key=source_collection_key)
                case TermKind.COMPOSITE:
                    property_key, property_value = _process_composite_term(
                        term=pterm_found,
                        universe_session=self.universe_session,
                        project_session=self.project_session)
                case TermKind.PATTERN:
                    property_key, property_value = _process_pattern_term(term=pterm_found)
                case _:
                    msg = f"unsupported term kind '{pterm_found.kind}'"
                    raise EsgvocNotImplementedError(msg)
        return property_key, property_value

    def translate_property(self, catalog_property: CatalogProperty) -> _CatalogProperty:
        property_key, property_value = self._translate_property_value(catalog_property)
        field_value = dict()
        if 'array' in catalog_property.catalog_field_value_type:
            field_value['type'] = 'array'
            root_property = dict()
            field_value['items'] = root_property
            root_property['type'] = catalog_property.catalog_field_value_type.split('_')[0]
            root_property['minItems'] = 1
        else:
            field_value['type'] = catalog_property.catalog_field_value_type
            root_property = field_value

        root_property[property_key] = property_value

        if catalog_property.catalog_field_name is None:
            attribute_name = catalog_property.source_collection
        else:
            attribute_name = catalog_property.catalog_field_name
        field_name = CatalogPropertiesJsonTranslator._translate_field_name(self.project_id,
                                                                           attribute_name)
        return _CatalogProperty(field_name=field_name,
                                field_value=field_value,
                                is_required=catalog_property.is_required)

    @staticmethod
    def _translate_field_name(project_id: str, attribute_name) -> str:
        return f'{project_id}{KEY_SEPARATOR}{attribute_name}'


def _catalog_properties_json_processor(property_translator: CatalogPropertiesJsonTranslator,
                                       properties: list[CatalogProperty]) -> list[_CatalogProperty]:
    result: list[_CatalogProperty] = list()
    for dataset_property_spec in properties:
        # DEBUG
        if dataset_property_spec.source_collection == 'member_id':
            continue
        ##
        catalog_property = property_translator.translate_property(dataset_property_spec)
        result.append(catalog_property)
    return result


def generate_json_schema(project_id: str) -> dict:
    """
    Generate json schema for the given project.

    :param project_id: The id of the given project.
    :type project_id: str
    :returns: The root node of a json schema.
    :rtype: dict
    :raises EsgvocValueError: On wrong information in catalog_specs.
    :raises EsgvocNotFoundError: On missing information in catalog_specs.
    :raises EsgvocNotImplementedError: On unexpected operations resulted in wrong information in catalog_specs).
    :raises EsgvocException: On json compliance error.
    """
    project_specs = projects.get_project(project_id)
    if project_specs is not None:
        catalog_specs = project_specs.catalog_specs
        if catalog_specs is not None:
            env = Environment(loader=FileSystemLoader(TEMPLATE_DIR_PATH))  # noqa: S701
            template = env.get_template(TEMPLATE_FILE_NAME)

            file_extension_version = catalog_specs.catalog_properties.extensions[0].version
            drs_dataset_id_regex = project_specs.drs_specs[DrsType.DATASET_ID].regex
            property_translator = CatalogPropertiesJsonTranslator(project_id)
            catalog_dataset_properties = \
                _catalog_properties_json_processor(property_translator,
                                                   catalog_specs.dataset_properties)

            catalog_file_properties = \
                _catalog_properties_json_processor(property_translator,
                                                   catalog_specs.file_properties)
            del property_translator
            json_raw_str = template.render(project_id=project_id,
                                           catalog_version=catalog_specs.version,
                                           file_extension_version=file_extension_version,
                                           drs_dataset_id_regex=drs_dataset_id_regex,
                                           catalog_dataset_properties=catalog_dataset_properties,
                                           catalog_file_properties=catalog_file_properties)
            # Json compliance checking.
            try:
                result = json.loads(json_raw_str)
                return result
            except Exception as e:
                raise EsgvocException(f'unable to produce schema compliant to JSON: {e}') from e
        else:
            raise EsgvocNotFoundError(f"catalog properties for the project '{project_id}' " +
                                      "are missing")
    else:
        raise EsgvocNotFoundError(f"unknown project '{project_id}'")


def pretty_print_json_node(obj: dict) -> str:
    """
    Serialize a dictionary into json format.

    :param obj: The dictionary.
    :type obj: dict
    :returns: a string that represents the dictionary in json format.
    :rtype: str
    """
    return json.dumps(obj, indent=JSON_INDENTATION)
