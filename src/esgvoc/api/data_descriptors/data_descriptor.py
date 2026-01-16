from abc import ABC, abstractmethod
from typing import Any, ClassVar, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_serializer


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        validate_default=True,
        extra="allow",
        arbitrary_types_allowed=True,
        use_enum_values=True,
        strict=False,
    )


class DataDescriptorVisitor(Protocol):
    """
    The specifications for a term visitor.
    """

    def visit_sub_set_term(self, term: "DataDescriptorSubSet") -> Any:
        """Visit a sub set of the information of a term."""
        pass

    def visit_plain_term(self, term: "PlainTermDataDescriptor") -> Any:
        """Visit a plain term."""
        pass

    def visit_pattern_term(self, term: "PatternTermDataDescriptor") -> Any:
        """Visit a pattern term."""
        pass

    def visit_composite_term(self, term: "CompositeTermDataDescriptor") -> Any:
        """Visit a composite term."""


class DataDescriptor(ConfiguredBaseModel, ABC):
    """
    Generic class for the data descriptor classes.
    """

    id: str
    """The identifier of the terms."""
    type: str
    """The data descriptor to which the term belongs."""
    description: str = ""
    """The description of the term."""

    @abstractmethod
    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        """
        Accept an term visitor.

        :param visitor: The term visitor.
        :type visitor: DataDescriptorVisitor
        :return: Depending on the visitor.
        :rtype: Any
        """
        pass

    @property
    def describe(self):
        return self.model_fields


class DataDescriptorSubSet(DataDescriptor):
    """
    A sub set of the information contains in a term.
    When using selected_term_fields, only id is guaranteed to be present.
    Other fields (type, description) may be None if not selected.
    """

    # Override inherited fields to make them truly optional using Field()
    # Using default_factory to ensure Pydantic treats them as optional
    type: str | None = Field(default=None, validate_default=False)  # type: ignore[assignment]
    """The data descriptor to which the term belongs (optional in subset)."""
    description: str | None = Field(default=None, validate_default=False)  # type: ignore[assignment]
    """The description of the term (optional in subset)."""

    MANDATORY_TERM_FIELDS: ClassVar[tuple[str]] = ("id",)
    """The set of mandatory term fields (only id is guaranteed when using selected_term_fields)."""

    @model_serializer(mode='wrap')
    def serialize_model(self, serializer: Any) -> dict[str, Any]:
        """
        Custom serializer that only includes fields that actually exist on the instance.
        This prevents Pydantic warnings when fields are removed via delattr().
        Uses 'wrap' mode to override default serialization behavior completely.
        """
        # Serialize all attributes from __dict__ that are not private
        result = {
            field_name: field_value
            for field_name, field_value in self.__dict__.items()
            if not field_name.startswith('_')
        }

        # Also include extra fields (like drs_name) that are stored in __pydantic_extra__
        if hasattr(self, '__pydantic_extra__') and self.__pydantic_extra__:
            result.update(self.__pydantic_extra__)

        return result

    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_sub_set_term(self)


class PlainTermDataDescriptor(DataDescriptor):
    """
    A data descriptor that describes hand written terms.
    """

    drs_name: str

    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_plain_term(self)


class PatternTermDataDescriptor(DataDescriptor):
    """
    A data descriptor that describes terms defined by a regular expression.
    """

    regex: str
    """The regular expression."""

    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_pattern_term(self)


class CompositeTermPart(ConfiguredBaseModel):
    """
    A reference to a term, part of a composite term.
    """

    id: str | list[str] | None = None
    """The id of the referenced term."""
    type: str
    """The type of the referenced term."""
    is_required: bool
    """Denote if the term is optional as part of a composite term."""


class CompositeTermDataDescriptor(DataDescriptor):
    """
    A data descriptor that describes terms composed of other terms.
    """

    separator: str
    """The components separator character."""
    parts: list[CompositeTermPart]
    """The components."""

    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_composite_term(self)
