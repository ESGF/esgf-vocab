from typing import TYPE_CHECKING, Annotated, Any, Iterable, Type, Union, get_args, get_origin

from pydantic import BaseModel, Discriminator, Tag, TypeAdapter

import esgvoc.core.constants as api_settings
from esgvoc.core.exceptions import EsgvocDbError

if TYPE_CHECKING:
    from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor, DataDescriptorSubSet
    from esgvoc.core.db.models.project import PTerm
    from esgvoc.core.db.models.universe import UTerm


def create_union(*classes: Type[BaseModel]):
    """
    Create a Union type with automatic property-based discrimination.

    Args:
        *classes: BaseModel classes to include in the union (order matters - most specific first)
        name: Optional name for the union type (used for debugging)

    Returns:
        An Annotated Union type with a discriminator that checks required properties
    """
    classes_list = list(classes)

    def property_discriminator(v: Any) -> str:
        """Generic discriminator that checks which class has matching required fields."""
        if not isinstance(v, dict):
            return v.__class__.__name__

        # Get the input fields
        input_fields = set(v.keys())

        # Track which models failed and why
        failed_matches = []

        # Try each class and see which one's required fields match
        for cls in classes_list:
            # Get required fields for this class (excluding nullable fields)
            required_fields = set()
            for field_name, field_info in cls.model_fields.items():
                # Only consider fields that are required AND not nullable
                if field_info.is_required():
                    # Check if None is allowed in the field type
                    annotation = field_info.annotation
                    is_nullable = False

                    # Check for Optional[X] or X | None patterns using get_origin and get_args
                    origin = get_origin(annotation)
                    if origin is Union:
                        # Check if None is in the union args
                        args = get_args(annotation)
                        is_nullable = type(None) in args

                    # Only add to required fields if not nullable
                    if not is_nullable:
                        required_fields.add(field_name)

            # Check if all required fields are present in input
            missing_fields = required_fields - input_fields
            if not missing_fields:
                return cls.__name__
            else:
                failed_matches.append((cls.__name__, sorted(missing_fields)))

        # If no model matched, raise a helpful error
        error_parts = ["Could not discriminate union type. No model matched the input data."]
        error_parts.append(f"Input fields: {sorted(input_fields)}")
        error_parts.append("\nAttempted models:")
        for model_name, missing in failed_matches:
            error_parts.append(f"  - {model_name}: missing required fields {missing}")

        raise ValueError("\n".join(error_parts))

    # Create annotated versions with tags
    tagged_classes = tuple(Annotated[cls, Tag(cls.__name__)] for cls in classes_list)

    # Create Union dynamically
    union_type = Union.__getitem__(tagged_classes)

    return Annotated[union_type, Discriminator(property_discriminator)]


def get_pydantic_class(data_descriptor_id_or_term_type: str) -> type["DataDescriptor"]:
    """
    Get the Pydantic class for a given data descriptor ID or term type.

    Args:
        data_descriptor_id_or_term_type: The identifier of the data descriptor or term type

    Returns:
        The corresponding Pydantic DataDescriptor class

    Raises:
        EsgvocDbError: If no matching pydantic class is found
    """
    from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING

    if data_descriptor_id_or_term_type in DATA_DESCRIPTOR_CLASS_MAPPING:
        return DATA_DESCRIPTOR_CLASS_MAPPING[data_descriptor_id_or_term_type]
    else:
        raise EsgvocDbError(f"'{data_descriptor_id_or_term_type}' pydantic class not found")


def instantiate_pydantic_term(
    term: "UTerm | PTerm", selected_term_fields: Iterable[str] | None
) -> "DataDescriptor | DataDescriptorSubSet":
    """
    Instantiate a Pydantic DataDescriptor from a database term.

    Args:
        term: The database term (UTerm or PTerm) to instantiate
        selected_term_fields: Optional list of specific fields to include. If None, all fields are included.

    Returns:
        A DataDescriptor instance (full model) when selected_term_fields is None,
        or a DataDescriptorSubSet instance when selected_term_fields is provided.
    """
    from esgvoc.api.data_descriptors.data_descriptor import DataDescriptorSubSet

    type = term.specs[api_settings.TERM_TYPE_JSON_KEY]
    if selected_term_fields is not None:
        # Build data dict with only id (truly mandatory) + selected fields
        data = {
            "id": term.id,
        }

        # Add selected fields from term.specs, but only if they exist
        for field in selected_term_fields:
            if field in term.specs:
                data[field] = term.specs[field]

        # Create instance with all fields initially
        # We need type for validation, will remove it if not selected
        if "type" not in data:
            data["type"] = type
        if "description" not in data:
            data["description"] = ""  # Use default value

        subset = DataDescriptorSubSet.model_construct(**data)

        # Now remove unselected optional fields using delattr
        # This maintains backward compatibility (hasattr will return False)
        if "type" not in selected_term_fields and hasattr(subset, "type"):
            delattr(subset, "type")
        if "description" not in selected_term_fields and hasattr(subset, "description"):
            delattr(subset, "description")

        # Mark which fields were actually set
        subset.__pydantic_fields_set__ = {"id"} | set(selected_term_fields)

        return subset
    else:
        term_class = get_pydantic_class(type)

        adapter = TypeAdapter(term_class)
        return adapter.validate_python(term.specs)
