from typing import Union, Annotated, Any, Type, Iterable, TYPE_CHECKING
from pydantic import BaseModel, Discriminator, Tag, TypeAdapter

from esgvoc.core.exceptions import EsgvocDbError
import esgvoc.core.constants as api_settings

if TYPE_CHECKING:
    from esgvoc.api.data_descriptors.data_descriptor import DataDescriptor
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

        # Try each class and see which one's required fields match
        for cls in classes_list:
            # Get required fields for this class
            required_fields = set()
            for field_name, field_info in cls.model_fields.items():
                if field_info.is_required():
                    required_fields.add(field_name)

            # Check if all required fields are present in input
            if required_fields.issubset(input_fields):
                return cls.__name__

        # Default to the last class if nothing matches
        return classes_list[-1].__name__

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


def instantiate_pydantic_term(term: "UTerm | PTerm", selected_term_fields: Iterable[str] | None) -> "DataDescriptor":
    """
    Instantiate a Pydantic DataDescriptor from a database term.

    Args:
        term: The database term (UTerm or PTerm) to instantiate
        selected_term_fields: Optional list of specific fields to include. If None, all fields are included.

    Returns:
        A DataDescriptor instance (either DataDescriptorSubSet or the full model)
    """
    from esgvoc.api.data_descriptors.data_descriptor import DataDescriptorSubSet

    type = term.specs[api_settings.TERM_TYPE_JSON_KEY]
    if selected_term_fields is not None:
        subset = DataDescriptorSubSet(id=term.id, type=type)
        for field in selected_term_fields:
            setattr(subset, field, term.specs.get(field, None))
        for field in DataDescriptorSubSet.MANDATORY_TERM_FIELDS:
            setattr(subset, field, term.specs.get(field, None))
        return subset
    else:
        term_class = get_pydantic_class(type)

        adapter = TypeAdapter(term_class)
        return adapter.validate_python(term.specs)
