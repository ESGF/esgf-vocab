"""
Generic translator that uses esgvoc API to discover mappings dynamically.

This translator doesn't hardcode any mappings - it uses the esgvoc database
to discover the relationship between:
- project collections (e.g., input4mip/source_id)
- universe data descriptors (e.g., source)
- pydantic models (e.g., Source)
"""

from typing import TypeVar, Generic, Type, Any, Iterator, get_origin, Callable
from pydantic import BaseModel, ValidationError, TypeAdapter

import esgvoc.api as api
from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING
from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor


# =============================================================================
# FIELD TRANSFORMER FUNCTIONS
# =============================================================================
# These functions create transformers for mapping source fields to target fields.
# Use them in project-specific COLLECTION_MAPPINGS.

FieldTransformer = Callable[[str, dict[str, Any]], Any]


def from_id() -> FieldTransformer:
    """Use the term_id as the value."""

    def transformer(term_id: str, data: dict[str, Any]) -> Any:
        return term_id

    return transformer


def field(source_field: str) -> FieldTransformer:
    """Copy value from another field."""

    def transformer(term_id: str, data: dict[str, Any]) -> Any:
        return data.get(source_field)

    return transformer


def default(value: Any) -> FieldTransformer:
    """Use a constant default value."""

    def transformer(term_id: str, data: dict[str, Any]) -> Any:
        return value

    return transformer


def as_list(source_field: str) -> FieldTransformer:
    """Wrap a field value in a list."""

    def transformer(term_id: str, data: dict[str, Any]) -> Any:
        val = data.get(source_field)
        if val is None:
            return []
        return [val] if not isinstance(val, list) else val

    return transformer


def as_dict(source_field: str, key: str = "id") -> FieldTransformer:
    """Wrap a field value in a dict with the given key."""

    def transformer(term_id: str, data: dict[str, Any]) -> Any:
        val = data.get(source_field)
        if val is None:
            return {}
        return {key: val}

    return transformer


def first_of(*source_fields: str) -> FieldTransformer:
    """Use the first non-None value from multiple fields. Use "@id" for term_id."""

    def transformer(term_id: str, data: dict[str, Any]) -> Any:
        for f in source_fields:
            if f == "@id":
                return term_id
            val = data.get(f)
            if val is not None:
                return val
        return None

    return transformer


# =============================================================================
# STRING-BASED MAPPING SYNTAX
# =============================================================================
# Allows defining mappings without importing functions:
#   "@id"              -> from_id()
#   "field_name"       -> field("field_name")
#   "=value"           -> default("value")
#   "=[]"              -> default([])
#   "=[value]"         -> default(["value"])
#   "[field_name]"     -> as_list("field_name")
#   "{field_name}"     -> as_dict("field_name")
#   "field1|field2"    -> first_of("field1", "field2")


def parse_mapping(spec: str) -> FieldTransformer:
    """
    Parse a string mapping specification into a FieldTransformer.

    Syntax:
        "@id"           - Use term_id
        "field_name"    - Copy from field
        "=value"        - Constant value (use "=[]" for empty list)
        "[field_name]"  - Wrap field in list
        "{field_name}"  - Wrap field in dict {"id": value}
        "a|b|c"         - First non-None of fields a, b, c (use @id for term_id)
    """
    spec = spec.strip()

    # @id -> from_id
    if spec == "@id":
        return from_id()

    # =value -> default
    if spec.startswith("="):
        value = spec[1:]
        if value == "[]":
            return default([])
        if value == "{}":
            return default({})
        if value.startswith("[") and value.endswith("]"):
            # =[item] -> default(["item"])
            return default([value[1:-1]])
        return default(value)

    # [field] -> as_list
    if spec.startswith("[") and spec.endswith("]"):
        return as_list(spec[1:-1])

    # {field} -> as_dict
    if spec.startswith("{") and spec.endswith("}"):
        return as_dict(spec[1:-1])

    # field1|field2 -> first_of
    if "|" in spec:
        fields = [f.strip() for f in spec.split("|")]
        return first_of(*fields)

    # plain field name -> field
    return field(spec)


def apply_mappings(
    collection_id: str,
    term_id: str,
    data: dict[str, Any],
    collection_mappings: dict[str, dict[str, str]],
    excluded_fields: dict[str, set[str]] | None = None,
) -> dict[str, Any]:
    """
    Apply string-based mappings to transform term data.

    Args:
        collection_id: The collection being processed
        term_id: The term ID
        data: The raw term data
        collection_mappings: Dict of collection_id -> {target_field: mapping_spec}
        excluded_fields: Optional dict of collection_id -> set of fields to exclude

    Returns:
        Transformed data ready for validation.
    """
    mappings = collection_mappings.get(collection_id, {})
    excluded = (excluded_fields or {}).get(collection_id, set())

    transformed = {}

    # Apply explicit mappings
    for target_field, spec in mappings.items():
        transformer = parse_mapping(spec)
        transformed[target_field] = transformer(term_id, data)

    # Pass through remaining fields
    for key, value in data.items():
        if key not in excluded and key not in transformed:
            transformed[key] = value if value != "" else None

    return transformed


T = TypeVar("T", bound=BaseModel)


class TranslationResult(BaseModel, Generic[T]):
    """Result of a translation attempt."""

    data: T | None = None
    term_id: str | None = None
    collection_id: str | None = None
    data_descriptor_id: str | None = None
    validation_md: str | None = None

    class Config:
        arbitrary_types_allowed = True


def get_pydantic_model_for_collection(
    project_id: str,
    collection_id: str,
) -> Type[DataDescriptor] | None:
    """
    Get the pydantic model class for a given project collection.

    Uses the esgvoc API to look up the data_descriptor_id,
    then maps to the pydantic class.

    Args:
        project_id: The project ID (e.g., "input4mip", "cmip7")
        collection_id: The collection ID (e.g., "source_id", "institution_id")

    Returns:
        The pydantic model class, or None if not found.
    """
    data_descriptor_id = api.get_data_descriptor_from_collection_in_project(project_id, collection_id)
    if data_descriptor_id is None:
        return None

    return DATA_DESCRIPTOR_CLASS_MAPPING.get(data_descriptor_id)


def get_collection_mapping(project_id: str) -> dict[str, tuple[str, Type[DataDescriptor] | None]]:
    """
    Get the full collection -> data_descriptor -> pydantic mapping for a project.

    Args:
        project_id: The project ID

    Returns:
        Dict mapping collection_id -> (data_descriptor_id, pydantic_class)
    """
    mapping = {}
    collections = api.get_all_collections_in_project(project_id)

    for collection_id in collections:
        data_descriptor_id = api.get_data_descriptor_from_collection_in_project(project_id, collection_id)
        pydantic_class = DATA_DESCRIPTOR_CLASS_MAPPING.get(data_descriptor_id) if data_descriptor_id else None
        mapping[collection_id] = (data_descriptor_id, pydantic_class)

    return mapping


def translate_term(
    project_id: str,
    collection_id: str,
    term_id: str,
    term_data: dict[str, Any],
    transform_fn: callable | None = None,
) -> TranslationResult:
    """
    Translate a term from a project collection to a validated pydantic model.

    This function:
    1. Looks up the data_descriptor_id for the collection
    2. Gets the corresponding pydantic model
    3. Prepares the data (adds id, type, drs_name)
    4. Validates against the model

    Args:
        project_id: The source project ID
        collection_id: The source collection ID
        term_id: The term ID
        term_data: The term data dictionary

    Returns:
        TranslationResult with validated data or validation errors.
    """
    # Get the data descriptor and pydantic model
    data_descriptor_id = api.get_data_descriptor_from_collection_in_project(project_id, collection_id)

    if data_descriptor_id is None:
        return TranslationResult(
            term_id=term_id,
            collection_id=collection_id,
            validation_md=f"No data_descriptor found for {project_id}/{collection_id}",
        )

    model_class = DATA_DESCRIPTOR_CLASS_MAPPING.get(data_descriptor_id)

    if model_class is None:
        return TranslationResult(
            term_id=term_id,
            collection_id=collection_id,
            data_descriptor_id=data_descriptor_id,
            validation_md=f"No pydantic model found for data_descriptor '{data_descriptor_id}'",
        )

    # Apply project-specific transformation if provided
    if transform_fn:
        term_data = transform_fn(collection_id, term_id, term_data)

    # Prepare the data
    prepared_data = _prepare_term_data(term_id, data_descriptor_id, term_data)

    # Validate - handle both regular models and Union types
    try:
        # Check if it's a Union type (Annotated unions from create_union)
        if get_origin(model_class) is not None or not hasattr(model_class, "model_validate"):
            # Use TypeAdapter for Union types
            adapter = TypeAdapter(model_class)
            validated = adapter.validate_python(prepared_data)
        else:
            # Regular pydantic model
            validated = model_class.model_validate(prepared_data)

        return TranslationResult(
            data=validated,
            term_id=term_id,
            collection_id=collection_id,
            data_descriptor_id=data_descriptor_id,
        )
    except ValidationError as e:
        return TranslationResult(
            term_id=term_id,
            collection_id=collection_id,
            data_descriptor_id=data_descriptor_id,
            validation_md=_errors_to_md(e),
        )
    except ValueError as e:
        # Union discriminator errors
        return TranslationResult(
            term_id=term_id,
            collection_id=collection_id,
            data_descriptor_id=data_descriptor_id,
            validation_md=f"Union validation error:\n```\n{str(e)}\n```",
        )


def _prepare_term_data(term_id: str, data_descriptor_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Prepare term data for validation."""
    prepared = dict(data)

    # Add required fields if not present
    if "id" not in prepared:
        prepared["id"] = term_id
    if "type" not in prepared:
        prepared["type"] = data_descriptor_id
    if "drs_name" not in prepared:
        prepared["drs_name"] = term_id

    # Convert empty strings to None
    for key, value in prepared.items():
        if value == "":
            prepared[key] = None

    return prepared


def _errors_to_md(err: ValidationError) -> str:
    """Convert ValidationError to Markdown table."""
    headers = ["Field", "Error Type", "Input Value", "Message"]
    rows = []

    for e in err.errors():
        loc = ".".join(str(x) for x in e.get("loc", ["unknown"]))
        err_type = e.get("type", "")
        input_value = e.get("input", e.get("ctx", {}).get("given", "N/A"))
        msg = e.get("msg", "").replace("\n", " ")
        rows.append([loc, err_type, f"`{input_value}`", msg])

    md = "| " + " | ".join(f"**{h}**" for h in headers) + " |\n"
    md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    for row in rows:
        md += "| " + " | ".join(str(c) for c in row) + " |\n"
    return md


def translate_collection(
    project_id: str,
    collection_id: str,
    terms: dict[str, dict[str, Any]],
    transform_fn: callable | None = None,
) -> Iterator[TranslationResult]:
    """
    Translate all terms in a collection.

    Args:
        project_id: The source project ID
        collection_id: The source collection ID
        terms: Dict mapping term_id -> term_data
        transform_fn: Optional function to transform term data before validation.
                      Signature: (collection_id, term_id, data) -> transformed_data

    Yields:
        TranslationResult for each term.
    """
    for term_id, term_data in terms.items():
        yield translate_term(project_id, collection_id, term_id, term_data, transform_fn)
