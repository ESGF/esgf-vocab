from typing import Protocol, Any
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
    def visit_plain_term(self, term: "PlainTermDataDescriptor") -> Any:
        """Visit a plain term."""
        pass
    def visit_drs_plain_term(self, term: "DrsPlainTermDataDescriptor") -> Any:
        """Visit a DRS plain term."""
        pass
    def visit_term_pattern(self, term: "TermPatternDataDescriptor") -> Any:
        """Visit a term pattern."""
        pass
    def visit_term_composite(self, term: "TermCompositeDataDescriptor") -> Any:
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


class TermPatternDataDescriptor(DataDescriptor):
    """
    A data descriptor that describes terms defined by a regular expression.
    """
    regex: str
    """The regular expression."""
    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_term_pattern(self)


class TermCompositePart(ConfiguredBaseModel):
    """
    A reference to a term, part of a term composite.
    """
    
    id: str
    """The id of the referenced term."""
    type: str
    """The type of the referenced term."""
    is_required : bool
    """Denote if the term is optional as part of a term composite"""


class TermCompositeDataDescriptor(DataDescriptor):
    """
    A data descriptor that describes terms composed of other terms.
    """
    separator: str
    """The term separator character."""
    parts: list[TermCompositePart]
    """The composites."""
    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_term_composite(self)