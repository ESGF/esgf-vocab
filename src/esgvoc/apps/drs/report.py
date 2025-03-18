from abc import ABC, abstractmethod
from enum import Enum
from typing import Annotated, Any, ClassVar, Iterable, Literal, Mapping, Protocol

from pydantic import BaseModel, Field, computed_field

from esgvoc.api.project_specs import DrsType


class IssueKind(str, Enum):
    """
    The kinds of validation and generation issues.
    """

    SPACE = 'Space'
    """Represents a problem of unnecessary space[s] at the beginning or end of the DRS expression."""
    UNPARSABLE = 'Unparsable'
    """Represents a problem of non-compliance of the DRS expression."""
    EXTRA_SEPARATOR = 'ExtraSeparator'
    """Represents a problem of multiple separator occurrences in the DRS expression."""
    EXTRA_CHAR = 'ExtraChar'
    """Represents a problem of extra characters at the end of the DRS expression."""
    BLANK_TERM = 'BlankTerm'
    """Represents a problem of blank term in the DRS expression (i.e., space[s] surrounded by separators)."""
    FILE_NAME = 'FileNameExtensionIssue'
    """Represents a problem on the given file name extension (missing or not compliant)."""
    INVALID_TERM = 'InvalidTerm'
    """Represents a problem of invalid term against a collection or a constant part of a DRS specification."""
    EXTRA_TERM = 'ExtraTerm'
    """Represents a problem of extra term at the end of the given DRS expression."""
    MISSING_TERM = 'MissingTerm'
    """Represents a problem of missing term for a collection part of the DRS specification."""
    TOO_MANY = 'TooManyTermsCollection'
    """Represents a problem while inferring a mapping: one term is able to match a collection"""
    CONFLICT = 'ConflictingCollections'
    """Represents a problem while inferring a mapping: collections shares the very same terms"""
    ASSIGNED = 'AssignedTerm'
    """Represents a decision of the Generator to assign a term to a collection, that may not be."""


class ParsingIssueVisitor(Protocol):
    """
    Specifications for a parsing issues visitor.
    """
    def visit_space_issue(self, issue: "Space") -> Any:
        """Visit a space issue."""
        pass

    def visit_unparsable_issue(self, issue: "Unparsable") -> Any:
        """Visit a unparsable issue."""
        pass

    def visit_extra_separator_issue(self, issue: "ExtraSeparator") -> Any:
        """Visit an extra separator issue."""
        pass

    def visit_extra_char_issue(self, issue: "ExtraChar") -> Any:
        """Visit an extra char issue."""
        pass

    def visit_blank_term_issue(self, issue: "BlankTerm") -> Any:
        """Visit a blank term issue."""
        pass


class ComplianceIssueVisitor(Protocol):
    """
    Specifications for a compliance issues visitor.
    """
    def visit_filename_extension_issue(self, issue: "FileNameExtensionIssue") -> Any:
        """Visit a file name extension issue."""
        pass

    def visit_invalid_term_issue(self, issue: "InvalidTerm") -> Any:
        """Visit an invalid term issue."""
        pass

    def visit_extra_term_issue(self, issue: "ExtraTerm") -> Any:
        """Visit an extra term issue."""
        pass

    def visit_missing_term_issue(self, issue: "MissingTerm") -> Any:
        """Visit a missing term issue."""
        pass


class ValidationIssueVisitor(ParsingIssueVisitor, ComplianceIssueVisitor):
    pass


class GenerationIssueVisitor(Protocol):
    """
    Specifications for a generator issues visitor.
    """
    def visit_invalid_term_issue(self, issue: "InvalidTerm") -> Any:
        """Visit an invalid term issue."""
        pass

    def visit_missing_term_issue(self, issue: "MissingTerm") -> Any:
        """Visit a missing term issue."""
        pass

    def visit_too_many_terms_collection_issue(self, issue: "TooManyTermCollection") -> Any:
        """Visit a too many terms collection issue."""
        pass

    def visit_conflicting_collections_issue(self, issue: "ConflictingCollections") -> Any:
        """Visit a conflicting collections issue."""
        pass

    def visit_assign_term_issue(self, issue: "AssignedTerm") -> Any:
        """Visit an assign term issue."""
        pass


class DrsIssue(BaseModel, ABC):
    kind: str
    """The class name of the issue for JSON serialization/deserialization."""

    """
    Generic class for all the DRS issues.
    """
    @abstractmethod
    def accept(self, visitor) -> Any:
        """
        Accept an DRS issue visitor.

        :param visitor: The DRS issue visitor.
        :return: Depending on the visitor.
        :rtype: Any
        """
        pass


class ParsingIssue(DrsIssue):
    """
    Generic class for the DRS parsing issues.
    """
    column: int | None = None
    """the column of faulty characters."""

    @abstractmethod
    def accept(self, visitor: ParsingIssueVisitor) -> Any:
        """
        Accept an DRS parsing issue visitor.

        :param visitor: The DRS parsing issue visitor.
        :type visitor: ParsingIssueVisitor
        :return: Depending on the visitor.
        :rtype: Any
        """
        pass


class Space(ParsingIssue):
    """
    Represents a problem of unnecessary space[s] at the beginning or end of the DRS expression.
    Note: `column` is `None`.
    """
    kind: Literal[IssueKind.SPACE] = IssueKind.SPACE

    def accept(self, visitor: ParsingIssueVisitor) -> Any:
        return visitor.visit_space_issue(self)

    def __str__(self):
        return "expression is surrounded by white space[s]"

    def __repr__(self) -> str:
        return self.__str__()


class Unparsable(ParsingIssue):
    """
    Represents a problem of non-compliance of the DRS expression.
    Note: `column` is `None`.
    """
    expected_drs_type: DrsType
    """The expected DRS type of the expression (directory, file name or dataset id)."""
    kind: Literal[IssueKind.UNPARSABLE] = IssueKind.UNPARSABLE

    def accept(self, visitor: ParsingIssueVisitor) -> Any:
        return visitor.visit_unparsable_issue(self)

    def __str__(self):
        return "unable to parse this expression"

    def __repr__(self) -> str:
        return self.__str__()


class ExtraSeparator(ParsingIssue):
    """
    Represents a problem of multiple separator occurrences in the DRS expression.
    """
    kind: Literal[IssueKind.EXTRA_SEPARATOR] = IssueKind.EXTRA_SEPARATOR

    def accept(self, visitor: ParsingIssueVisitor) -> Any:
        return visitor.visit_extra_separator_issue(self)

    def __str__(self):
        return f"extra separator(s) at column {self.column}"

    def __repr__(self) -> str:
        return self.__str__()


class ExtraChar(ParsingIssue):
    """
    Represents a problem of extra characters at the end of the DRS expression.
    """
    kind: Literal[IssueKind.EXTRA_CHAR] = IssueKind.EXTRA_CHAR

    def accept(self, visitor: ParsingIssueVisitor) -> Any:
        return visitor.visit_extra_char_issue(self)

    def __str__(self):
        return f"extra character(s) at column {self.column}"

    def __repr__(self) -> str:
        return self.__str__()


class BlankTerm(ParsingIssue):
    """
    Represents a problem of blank term in the DRS expression (i.e., space[s] surrounded by separators).
    """
    kind: Literal[IssueKind.BLANK_TERM] = IssueKind.BLANK_TERM

    def accept(self, visitor: ParsingIssueVisitor) -> Any:
        return visitor.visit_blank_term_issue(self)

    def __str__(self):
        return f"blank term at column {self.column}"

    def __repr__(self) -> str:
        return self.__str__()


class ComplianceIssue(DrsIssue):
    """
    Generic class for the compliance issues.
    """
    @abstractmethod
    def accept(self, visitor: ComplianceIssueVisitor) -> Any:
        """
        Accept an DRS compliance issue visitor.

        :param visitor: The DRS compliance issue visitor.
        :type visitor: ComplianceIssueVisitor
        :return: Depending on the visitor.
        :rtype: Any
        """
        pass


class FileNameExtensionIssue(ComplianceIssue):
    """
    Represents a problem on the given file name extension (missing or not compliant).
    """
    expected_extension: str
    """The expected file name extension."""
    kind: Literal[IssueKind.FILE_NAME] = IssueKind.FILE_NAME

    def accept(self, visitor: ComplianceIssueVisitor) -> Any:
        return visitor.visit_filename_extension_issue(self)

    def __str__(self):
        return f"filename extension missing or not compliant with '{self.expected_extension}'"


class TermIssue(ComplianceIssue):
    """
    Generic class for the DRS term issues.
    """
    term: str
    """The faulty term."""
    term_position: int
    """The position of the faulty term (the part position, not the column of the characters."""


class GenerationIssue(DrsIssue):
    """
    Generic class for the DRS generation issues.
    """
    @abstractmethod
    def accept(self, visitor: GenerationIssueVisitor) -> Any:
        """
        Accept an DRS generation issue visitor.

        :param visitor: The DRS generation issue visitor.
        :type visitor: GenerationIssueVisitor
        :return: Depending on the visitor.
        :rtype: Any
        """
        pass


class InvalidTerm(TermIssue, GenerationIssue):
    """
    Represents a problem of invalid term against a collection or a constant part of a DRS specification.
    """
    collection_id_or_constant_value: str
    """The collection id or the constant part of a DRS specification."""
    kind: Literal[IssueKind.INVALID_TERM] = IssueKind.INVALID_TERM

    def accept(self, visitor: ComplianceIssueVisitor | GenerationIssueVisitor) -> Any:
        return visitor.visit_invalid_term_issue(self)

    def __str__(self):
        return f"term '{self.term}' not compliant with {self.collection_id_or_constant_value} at " + \
               f"position {self.term_position}"

    def __repr__(self) -> str:
        return self.__str__()


class ExtraTerm(TermIssue):
    """
    Represents a problem of extra term at the end of the given DRS expression.
    All part of the DRS specification have been processed and this term is not necessary
    (`collection_id` is `None`) or it has been invalidated by an optional collection part
    of the DRS specification (`collection_id` is set).
    """
    collection_id: str | None
    """The optional collection id or `None`."""
    kind: Literal[IssueKind.EXTRA_TERM] = IssueKind.EXTRA_TERM

    def accept(self, visitor: ComplianceIssueVisitor) -> Any:
        return visitor.visit_extra_term_issue(self)

    def __str__(self):
        repr = f"extra term {self.term}"
        if self.collection_id:
            repr += f" invalidated by the optional collection {self.collection_id}"
        return repr + f" at position {self.term_position}"

    def __repr__(self) -> str:
        return self.__str__()


class MissingTerm(ComplianceIssue, GenerationIssue):
    """
    Represents a problem of missing term for a collection part of the DRS specification.
    """
    collection_id: str
    """The collection id."""
    collection_position: int
    """The collection part position (not the column of the characters)."""
    kind: Literal[IssueKind.MISSING_TERM] = IssueKind.MISSING_TERM

    def accept(self, visitor: ComplianceIssueVisitor | GenerationIssueVisitor) -> Any:
        return visitor.visit_missing_term_issue(self)

    def __str__(self):
        return f'missing term for {self.collection_id} at position {self.collection_position}'

    def __repr__(self) -> str:
        return self.__str__()


class TooManyTermCollection(GenerationIssue):
    """
    Represents a problem while inferring a mapping collection - term in the generation
    of a DRS expression based on a bag of terms. The problem is that more than one term
    is able to match this collection. The generator is unable to choose from these terms
    """
    collection_id: str
    """The collection id."""
    terms: list[str]
    """The faulty terms."""
    kind: Literal[IssueKind.TOO_MANY] = IssueKind.TOO_MANY

    def accept(self, visitor: GenerationIssueVisitor) -> Any:
        return visitor.visit_too_many_terms_collection_issue(self)

    def __str__(self):
        terms_str = ", ".join(term for term in self.terms)
        result = f'collection {self.collection_id} has more than one term ({terms_str})'
        return result

    def __repr__(self) -> str:
        return self.__str__()


class ConflictingCollections(GenerationIssue):
    """
    Represents a problem while inferring a mapping collection - term in the generation
    of a DRS expression based on a bag of terms. The problem is that these collections shares the
    very same terms. The generator is unable to choose which term for which collection.
    """
    collection_ids: list[str]
    """The ids of the collections."""
    terms: list[str]
    """The shared terms."""
    kind: Literal[IssueKind.CONFLICT] = IssueKind.CONFLICT

    def accept(self, visitor: GenerationIssueVisitor) -> Any:
        return visitor.visit_conflicting_collections_issue(self)

    def __str__(self):
        collection_ids_str = ", ".join(collection_id for collection_id in self.collection_ids)
        terms_str = ", ".join(term for term in self.terms)
        result = f"collections {collection_ids_str} are competing for the same term(s) {terms_str}"
        return result

    def __repr__(self) -> str:
        return self.__str__()


class AssignedTerm(GenerationIssue):
    """
    Represents a decision of the Generator to assign this term to the collection, that may not be.
    relevant.
    """
    collection_id: str
    """The collection id."""
    term: str
    """The term."""
    kind: Literal[IssueKind.ASSIGNED] = IssueKind.ASSIGNED

    def accept(self, visitor: GenerationIssueVisitor) -> Any:
        return visitor.visit_assign_term_issue(self)

    def __str__(self):
        result = f"assign term {self.term} for collection {self.collection_id}"
        return result

    def __repr__(self) -> str:
        return self.__str__()


GenerationError = Annotated[AssignedTerm | ConflictingCollections | InvalidTerm | MissingTerm |
                            TooManyTermCollection, Field(discriminator='kind')]
GenerationWarning = Annotated[AssignedTerm | MissingTerm, Field(discriminator='kind')]

ValidationError = Annotated[BlankTerm | ExtraChar | ExtraSeparator | ExtraTerm |
                            FileNameExtensionIssue | InvalidTerm | MissingTerm | Space | Unparsable,
                            Field(discriminator='kind')]
ValidationWarning = Annotated[ExtraSeparator | MissingTerm | Space, Field(discriminator='kind')]


class DrsReport(BaseModel):
    """
    Generic DRS application report class.
    """

    project_id: str
    """The project id associated to the result of the DRS application."""

    type: DrsType
    """The type of the DRS"""

    errors: list
    """A list of DRS issues that are considered as errors."""

    warnings: list
    """A list of DRS issues that are considered as warnings."""

    @computed_field  # type: ignore
    @property
    def nb_errors(self) -> int:
        """The number of errors."""
        return len(self.errors) if self.errors else 0

    @computed_field  # type: ignore
    @property
    def nb_warnings(self) -> int:
        """The number of warnings."""
        return len(self.warnings) if self.warnings else 0

    @computed_field  # type: ignore
    @property
    def validated(self) -> bool:
        """The correctness of the result of the DRS application."""
        return False if self.errors else True

    def __len__(self) -> int:
        return self.nb_errors

    def __bool__(self) -> bool:
        return self.validated


class DrsValidationReport(DrsReport):
    """
    The DRS validation report class.
    """

    expression: str
    """The DRS expression been checked."""

    errors: list[ValidationError]
    """A list of DRS parsing and compliance issues that are considered as errors."""

    warnings: list[ValidationWarning]
    """A list of DRS parsing and compliance issues that are considered as warnings."""

    def __str__(self) -> str:
        return f"'{self.expression}' has {self.nb_errors} error(s) and " + \
               f"{self.nb_warnings} warning(s)"

    def __repr__(self) -> str:
        return self.__str__()


class DrsGenerationReport(DrsReport):
    """
    The DRS generation report.
    """

    MISSING_TAG: ClassVar[str] = '[MISSING]'
    """Tag used in the DRS generated expression to replace a missing term."""

    INVALID_TAG: ClassVar[str] = '[INVALID]'
    """Tag used in the DRS generated expression to replace a invalid term."""

    given_mapping_or_bag_of_terms: Mapping | Iterable
    """The mapping or the bag of terms given."""

    mapping_used: Mapping
    """The mapping inferred from the given bag of terms (same mapping otherwise)."""

    generated_drs_expression: str
    """The generated DRS expression with possible tags to replace missing or invalid terms."""

    errors: list[GenerationError]
    """A list of DRS generation issues that are considered as errors."""

    warnings: list[GenerationWarning]
    """A list of DRS generation issues that are considered as warnings."""

    def __str__(self) -> str:
        return f"'{self.generated_drs_expression}' has {self.nb_errors} error(s) and " + \
               f"{self.nb_warnings} warning(s)"

    def __repr__(self) -> str:
        return self.__str__()
