from abc import ABC, abstractmethod
from typing import Any, ClassVar, Protocol

from pydantic import BaseModel, ConfigDict


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


class DataDescriptorSubSet(DataDescriptor):
    """
    A sub set of the information contains in a term.
    """
    MANDATORY_TERM_FIELDS: ClassVar[tuple[str, str]] = ('id', 'type')
    """The set of mandatory term fields."""
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
