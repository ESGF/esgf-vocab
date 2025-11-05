import json
from dataclasses import dataclass
from itertools import combinations, product
from pathlib import Path
from typing import Sequence

from jinja2 import Environment, FileSystemLoader
from sqlmodel import Session

from esgvoc.api import projects, search
from esgvoc.api.project_specs import CatalogProperty, DrsType
from esgvoc.core.constants import COMPOSITE_REQUIRED_KEY, DRS_SPECS_JSON_KEY, PATTERN_JSON_KEY
from esgvoc.core.db.models.project import PCollection, PTerm, TermKind
from esgvoc.core.db.models.universe import UTerm
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
                                 project_session: Session) -> tuple[str, list[str | dict], bool]:
    result: list[str | dict] = list()
    property_key = ""
    has_pattern = False
    for term in collection.terms:
        property_key, property_value, _has_pattern = _process_composite_term(term, universe_session,
                                                                             project_session)
        if isinstance(property_value, list):
            result.extend(property_value)
        else:
            result.append(property_value)
        has_pattern |= _has_pattern
    return property_key, result, has_pattern


def _inner_process_composite_term(resolved_term: UTerm | PTerm,
                                  universe_session: Session,
                                  project_session: Session) -> tuple[str | list, bool]:
    is_pattern = False
    match resolved_term.kind:
        case TermKind.PLAIN:
            result = resolved_term.specs[DRS_SPECS_JSON_KEY]
        case TermKind.PATTERN:
            result = resolved_term.specs[PATTERN_JSON_KEY].replace('^', '').replace('$', '')
            is_pattern = True
        case TermKind.COMPOSITE:
            _, result, is_pattern = _process_composite_term(resolved_term, universe_session,
                                                            project_session)
        case _:
            msg = f"unsupported term kind '{resolved_term.kind}'"
            raise EsgvocNotImplementedError(msg)
    return result, is_pattern


def _accumulate_resolved_part(resolved_part: list,
                              resolved_term: UTerm | PTerm,
                              universe_session: Session,
                              project_session: Session) -> bool:
    tmp, has_pattern = _inner_process_composite_term(resolved_term, universe_session,
                                                     project_session)
    if isinstance(tmp, list):
        resolved_part.extend(tmp)
    else:
        resolved_part.append(tmp)
    return has_pattern


def _generate_combinations(items_parts: list[list], required_parts: list[bool]) -> list[list]:
    number_of_parts = len(items_parts)
    required_indexes = {index for index, required in enumerate(required_parts) if required}
    result = list()
    # Generate all the combination of item lists.
    for r in range(1, number_of_parts + 1):  # Some optional list may or may not be included.
        # According to the doc, combination respect the list order.
        for index_subset in combinations(range(number_of_parts), r):
            # Only keep combinations with the required item lists.
            if required_indexes.issubset(index_subset):
                result.append([items_parts[index] for index in index_subset])
    return result


def _process_composite_term(term: UTerm | PTerm, universe_session: Session,
                            project_session: Session) -> tuple[str, list[str | dict], bool]:
    items_parts: list[list[str]] = list()
    required_parts: list[bool] = list()
    separator, parts = projects._get_composite_term_separator_parts(term)
    has_pattern = False
    for part in parts:
        resolved_term = projects._resolve_composite_term_part(part, universe_session, project_session)
        resolved_part = list()
        if isinstance(resolved_term, Sequence):
            for r_term in resolved_term:
                has_pattern |= _accumulate_resolved_part(resolved_part, r_term, universe_session,
                                                         project_session)
        else:
            has_pattern = _accumulate_resolved_part(resolved_part, resolved_term, universe_session,
                                                    project_session)
        items_parts.append(resolved_part)
        required_parts.append(part[COMPOSITE_REQUIRED_KEY])
    property_values: list[str | dict] = list()
    combinations = _generate_combinations(items_parts, required_parts)
    for combination in combinations:
        for product_result in product(*combination):
            # Patterns terms are meant to be validated individually.
            # So their regex are defined as a whole (begins by a ^, ends by a $).
            # As the pattern is a concatenation of plain or regex, multiple ^ and $ can exist.
            # The later, must be removed.
            tmp = separator.join(product_result)
            if has_pattern:
                tmp = f'^{tmp}$'
                tmp = {'pattern': tmp}
            property_values.append(tmp)
    property_key = 'anyOf' if has_pattern else 'enum'
    return property_key, property_values, has_pattern


def _process_col_pattern_terms(collection: PCollection) -> tuple[str, str | list[dict]]:
    if len(collection.terms) == 1:
        term = collection.terms[0]
        property_key, property_value = _process_pattern_term(term)
    else:
        property_key = 'anyOf'
        property_value = list()
        for term in collection.terms:
            pkey, pvalue = _process_pattern_term(term)
            property_value.append({pkey: pvalue})
    return property_key, property_value


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

    def _translate_property_value(self, catalog_property: CatalogProperty) \
            -> tuple[str | None, str | list[str] | list[str | dict] | None]:
        property_key: str | None
        property_value: str | list[str] | list[str | dict] | None

        # Properties unrelated to collections of project.
        if catalog_property.source_collection is None:
            property_key = None
            property_value = None
        elif catalog_property.source_collection not in self.collections:
            raise EsgvocNotFoundError(f"collection '{catalog_property.source_collection}' is not found")
        else:
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
                        property_key, property_value, _ = _process_col_composite_terms(
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
                        property_key, property_value, _ = _process_composite_term(
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

        if (property_key is not None) and (property_value is not None):
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
            extension_specs = dict()
            for catalog_extension in catalog_specs.catalog_properties.extensions:
                catalog_extension_name = catalog_extension.name.replace('-', '_')
                extension_specs[f'{catalog_extension_name}_extension_version'] = catalog_extension.version
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
                                           drs_dataset_id_regex=drs_dataset_id_regex,
                                           catalog_dataset_properties=catalog_dataset_properties,
                                           catalog_file_properties=catalog_file_properties,
                                           **extension_specs)
            # Json compliance checking.
            try:
                result = json.loads(json_raw_str)
                return result
            except Exception as e:
                raise EsgvocException(f'JSON error: {e}. Dump raw:\n{json_raw_str}') from e
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
