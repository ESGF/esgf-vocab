"""
Base definitions for all data descriptors
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Protocol

from pydantic import BaseModel, ConfigDict


class ConfiguredBaseModel(BaseModel):
    """
    Base model with configuration we want to apply to all data descriptors
    """

    model_config = ConfigDict(
        validate_assignment=True,
        validate_default=True,
        # TODO: Should be no extras allowed once in production/stable
        extra="allow",
        # TODO: Should be no arbitary types allowed once in production/stable
        arbitrary_types_allowed=True,
        use_enum_values=True,
        # TODO: Should be strict once in production/stable
        strict=False,
    )


class DataDescriptorVisitor(Protocol):
    """
    The specifications for a data descriptor visitor

    The word 'term' was used here,
    but the visitor vists data descriptors, not terms.
    Is 'term' just a short-hand for an instance of a data descriptor?
    Ok, yes, seems so, I should read the type hints sooner probably.
    In which case my question would be,
    isn't `PlainTermDataDescriptor` a weird name/repetition?
    A term is already an instance of a data descriptor
    so this is basically 'instance of a data descriptor data descriptor'?
    """

    def visit_sub_set_term(self, term: "DataDescriptorSubSet") -> Any:
        """Visit a subset of the information of a term"""

    def visit_plain_term(self, term: "PlainTermDataDescriptor") -> Any:
        """Visit a plain term"""

    def visit_pattern_term(self, term: "PatternTermDataDescriptor") -> Any:
        """Visit a pattern term"""

    def visit_composite_term(self, term: "CompositeTermDataDescriptor") -> Any:
        """Visit a composite term"""


class DataDescriptor(ConfiguredBaseModel, ABC):
    """
    Generic class for data descriptors
    """

    id: str
    """
    The unique identifier of the term

    Must be unique among all instances of the given data descriptor.
    [Question: do we enforce/check this uniqueness anywhere?]

    Must be all lowercase.
    [TODO: add this validation]
    """

    type: str
    """
    The kind of data descriptor the term is

    In other words, the name of the data descriptor.
    It's a bit redundant given the class name also defines this,
    but is kept for clarity and consistency of case styles
    as this may not always be the same as the camelCase
    used for Python class names.
    Having this also simplifies parsing from the raw JSON-LD CV files.

    [Are there any rules about this e.g. all lowercase?
    I assume no?]
    """

    @abstractmethod
    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        """
        Accept a term visitor

        :param visitor: The term visitor.
        :type visitor: DataDescriptorVisitor
        :return: Depending on the visitor.
        :rtype: Any
        """


class DataDescriptorSubSet(DataDescriptor):
    """
    A subset of the information contained in a term
    """

    MANDATORY_TERM_FIELDS: ClassVar[tuple[str, str]] = ("id", "type")
    """The set of mandatory fields for the term"""

    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_sub_set_term(self)


class PlainTermDataDescriptor(DataDescriptor):
    """
    A data descriptor that describes hand-written terms.

    [What does hand-written mean here?
    A term that comes from a specific set of available options,
    rather than something more generally verifiable
    like a regular expression or compound term?]
    """

    drs_name: str
    """
    Value of the term as used in the data reference syntax (DRS) [?]

    This may be the same as the ID,
    but may also not be hence a separate attribute is provided.
    Having a separate attribute also ensures
    that the value expected in the DRS
    (and, by extension, file attributes)
    is unambiguously and uniquely defined.

    For example, for the "1pctCO2" experiment,
    `id` is "1pctco2" (all lowercase)
    while "1pctCO2" is the `drs_name`
    because this is the case variation used for this term in file attributes
    and when 'filling out' DRS components.
    """

    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_plain_term(self)


class PatternTermDataDescriptor(DataDescriptor):
    """
    A data descriptor that describes terms that have to match a regular expression
    """

    regex: str
    """The regular expression that defines the allowed values for the term"""

    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_pattern_term(self)


class CompositeTermPart(ConfiguredBaseModel):
    """
    A reference to a term as part of a composite term
    """

    id: str | list[str] | None = None
    """
    The id of the referenced term

    e.g. `horizontal_label` as part of `branded_variable`

    Why can this be a `list` or `None`?
    If you have more than one, wouldn't you have multiple `CompositeTermPart`?
    If you have no composites, wouldn't you just not use a `CompositeTermPart`
    rather than initialising a `CompositeTermPart` with an ID of `None`?
    Or does this allow for using `CompositeTermPart`'s that aren't terms themselves
    (I can't think of that use case, but I guess it exists)?

    See [TODO: cross-ref DataDescriptor.id for details]
    """

    type: str
    """
    The kind of data descriptor the referenced term is

    See [TODO: cross-ref DataDescriptor.type for details]
    """

    is_required: bool
    """
    Denote if the term is an optional part of the composite term or not
    """


class CompositeTermDataDescriptor(DataDescriptor):
    """
    A data descriptor that describes terms composed of other terms.
    """

    separator: str
    """
    The separator to place between components when creating the composite term from its parts
    """

    parts: list[CompositeTermPart]
    """
    The parts i.e. components from which the composite term is constructed
    """

    def accept(self, visitor: DataDescriptorVisitor) -> Any:
        return visitor.visit_composite_term(self)
