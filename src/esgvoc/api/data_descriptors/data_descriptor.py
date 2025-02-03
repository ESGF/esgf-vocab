from typing import Protocol, Any, ClassVar
from abc import ABC, abstractmethod
from pydantic import BaseModel, ConfigDict


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        validate_assignment = True,
        validate_default = True,
        extra = "allow",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
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
    def visit_drs_plain_term(self, term: "DrsPlainTermDataDescriptor") -> Any:
        """Visit a DRS plain term."""
        pass
    def visit_term_pattern(self, term: "PatternTermDataDescriptor") -> Any:
        """Visit a term pattern."""
        pass
    def visit_term_composite(self, term: "CompositeTermDataDescriptor") -> Any:
        """Visit a term composite."""


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
    MANDATORY_TERM_FIELDS: ClassVar[list[str]] = ['id', 'type']
    """The set of mandatory term fields."""
    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_sub_set_term(self)


class PlainTermDataDescriptor(DataDescriptor):
    """
    A data descriptor that describes hand written terms.
    """
    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_plain_term(self)


class DrsPlainTermDataDescriptor(PlainTermDataDescriptor):
    """
    A data descriptor that describes hand written terms with DRS name.
    """
    drs_name: str
    """The DRS name."""
    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_drs_plain_term(self)


class PatternTermDataDescriptor(DataDescriptor):
    """
    A data descriptor that describes terms defined by a regular expression.
    """
    regex: str
    """The regular expression."""
    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_term_pattern(self)


class CompositeTermPart(ConfiguredBaseModel):
    """
    A reference to a term, part of a term composite.
    """
    id: str
    """The id of the referenced term."""
    type: str
    """The type of the referenced term."""
    is_required : bool
    """Denote if the term is optional as part of a term composite"""


class CompositeTermDataDescriptor(DataDescriptor):
    """
    A data descriptor that describes terms composed of other terms.
    """
    separator: str
    """The term separator character."""
    parts: list[CompositeTermPart]
    """The composites."""
    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_term_composite(self)