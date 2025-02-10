from abc import ABC, abstractmethod
from typing import Any, ClassVar, Iterable, Mapping, Protocol

from pydantic import BaseModel, computed_field

from esgvoc.api.project_specs import DrsType


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
    def visit_blank_token_issue(self, issue: "BlankToken") -> Any:
        """Visit a blank token issue."""
        pass


class ComplianceIssueVisitor(Protocol):
    """
    Specifications for a compliance issues visitor.
    """
    def visit_filename_extension_issue(self, issue: "FileNameExtensionIssue") -> Any:
        """Visit a file name extension issue."""
        pass
    def visit_invalid_token_issue(self, issue: "InvalidToken") -> Any:
        """Visit an invalid token issue."""
        pass
    def visit_extra_token_issue(self, issue: "ExtraToken") -> Any:
        """Visit an extra token issue."""
        pass
    def visit_missing_token_issue(self, issue: "MissingToken") -> Any:
        """Visit a missing token issue."""
        pass


class ValidationIssueVisitor(ParsingIssueVisitor, ComplianceIssueVisitor):
    pass


class GenerationIssueVisitor(Protocol):
    """
    Specifications for a generator issues visitor.
    """
    def visit_invalid_token_issue(self, issue: "InvalidToken") -> Any:
        """Visit an invalid token issue."""
        pass
    def visit_missing_token_issue(self, issue: "MissingToken") -> Any:
        """Visit a missing token issue."""
        pass
    def visit_too_many_tokens_collection_issue(self, issue: "TooManyTokensCollection") -> Any:
        """Visit a too many tokens collection issue."""
        pass
    def visit_conflicting_collections_issue(self, issue: "ConflictingCollections") -> Any:
        """Visit a conflicting collections issue."""
        pass
    def visit_assign_token_issue(self, issue: "AssignedToken") -> Any:
        """Visit an assign token issue."""
        pass


class DrsIssue(BaseModel, ABC):
    """
    Generic class for all the DRS issues.
    """
    @computed_field # type: ignore
    @property
    def class_name(self) -> str:
       """The class name of the issue for JSON serialization."""
       return self.__class__.__name__
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
    column: int|None = None
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
    def accept(self, visitor: ParsingIssueVisitor) -> Any:
        return visitor.visit_extra_char_issue(self)
    def __str__(self):
        return f"extra character(s) at column {self.column}"
    def __repr__(self) -> str:
        return self.__str__()


class BlankToken(ParsingIssue):
    """
    Represents a problem of blank token in the DRS expression (i.e., space[s] surrounded by separators).
    """
    def accept(self, visitor: ParsingIssueVisitor) -> Any:
        return visitor.visit_blank_token_issue(self)
    def __str__(self):
        return f"blank token at column {self.column}"
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
    def accept(self, visitor: ComplianceIssueVisitor) -> Any:
        return visitor.visit_filename_extension_issue(self)
    def __str__(self):
        return f"filename extension missing or not compliant with '{self.expected_extension}'"


class TokenIssue(ComplianceIssue):
    """
    Generic class for the DRS token issues.
    """
    token: str
    """The faulty token."""
    token_position: int
    """The position of the faulty token (the part position, not the column of the characters."""


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


class InvalidToken(TokenIssue, GenerationIssue):
    """
    Represents a problem of invalid token against a collection or a constant part of a DRS specification.
    """
    collection_id_or_constant_value: str
    """The collection id or the constant part of a DRS specification."""
    def accept(self, visitor: ComplianceIssueVisitor|GenerationIssueVisitor) -> Any:
        return visitor.visit_invalid_token_issue(self)
    def __str__(self):
        return f"token '{self.token}' not compliant with {self.collection_id_or_constant_value} at position {self.token_position}"
    def __repr__(self) -> str:
        return self.__str__()


class ExtraToken(TokenIssue):
    """
    Represents a problem of extra token at the end of the given DRS expression.
    All part of the DRS specification have been processed and this token is not necessary
    (`collection_id` is `None`) or it has been invalidated by an optional collection part
    of the DRS specification (`collection_id` is set).
    """
    collection_id: str|None
    """The optional collection id or `None`."""
    def accept(self, visitor: ComplianceIssueVisitor) -> Any:
        return visitor.visit_extra_token_issue(self)
    def __str__(self):
        repr = f"extra token {self.token}"
        if self.collection_id:
            repr += f" invalidated by the optional collection {self.collection_id}"
        return repr + f" at position {self.token_position}"
    def __repr__(self) -> str:
        return self.__str__()


class MissingToken(ComplianceIssue, GenerationIssue):
    """
    Represents a problem of missing token for a collection part of the DRS specification.
    """
    collection_id: str
    """The collection id."""
    collection_position: int
    """The collection part position (not the column of the characters)."""
    def accept(self, visitor: ComplianceIssueVisitor|GenerationIssueVisitor) -> Any:
        return visitor.visit_missing_token_issue(self)
    def __str__(self):
        return f'missing token for {self.collection_id} at position {self.collection_position}'
    def __repr__(self) -> str:
        return self.__str__()


class TooManyTokensCollection(GenerationIssue):
    """
    Represents a problem while inferring a mapping collection - token in the generation
    of a DRS expression based on a bag of tokens. The problem is that more than one token
    is able to match this collection. The generator is unable to choose from these tokens
    """
    collection_id: str
    """The collection id."""
    tokens: list[str]
    """The faulty tokens."""
    def accept(self, visitor: GenerationIssueVisitor) -> Any:
        return visitor.visit_too_many_tokens_collection_issue(self)

    def __str__(self):
        tokens_str = ", ".join(token for token in self.tokens)
        result = f'collection {self.collection_id} has more than one token ({tokens_str})'
        return result
    def __repr__(self) -> str:
        return self.__str__()


class ConflictingCollections(GenerationIssue):
    """
    Represents a problem while inferring a mapping collection - token in the generation
    of a DRS expression based on a bag of tokens. The problem is that these collections shares the
    very same tokens. The generator is unable to choose which token for which collection.
    """
    collection_ids: list[str]
    """The ids of the collections."""
    tokens: list[str]
    """The shared tokens."""
    def accept(self, visitor: GenerationIssueVisitor) -> Any:
        return visitor.visit_conflicting_collections_issue(self)
    def __str__(self):
        collection_ids_str = ", ".join(collection_id for collection_id in self.collection_ids)
        tokens_str = ", ".join(token for token in self.tokens)
        result = f"collections {collection_ids_str} are competing for the same token(s) {tokens_str}"
        return result
    def __repr__(self) -> str:
        return self.__str__()


class AssignedToken(GenerationIssue):
    """
    Represents a decision of the Generator to assign this token to the collection, that may not be.
    relevant.
    """
    collection_id: str
    """The collection id."""
    token: str
    """The token."""
    def accept(self, visitor: GenerationIssueVisitor) -> Any:
        return visitor.visit_assign_token_issue(self)
    def __str__(self):
        result = f"assign token {self.token} for collection {self.collection_id}"
        return result
    def __repr__(self) -> str:
        return self.__str__()


GeneratorError =  AssignedToken | ConflictingCollections |  InvalidToken | MissingToken | TooManyTokensCollection
GeneratorWarning = AssignedToken | MissingToken

ValidatorError = BlankToken | ExtraChar | ExtraSeparator | ExtraToken | FileNameExtensionIssue | \
                 InvalidToken | MissingToken | Space | Unparsable
ValidatorWarning = ExtraSeparator | MissingToken | Space


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

    @computed_field # type: ignore
    @property
    def nb_errors(self) -> int:
        """The number of errors."""
        return len(self.errors) if self.errors else 0

    @computed_field # type: ignore
    @property
    def nb_warnings(self) -> int:
        """The number of warnings."""
        return len(self.warnings) if self.warnings else 0

    @computed_field # type: ignore
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

    errors: list[ValidatorError]
    """A list of DRS parsing and compliance issues that are considered as errors."""

    warnings: list[ValidatorWarning]
    """A list of DRS parsing and compliance issues that are considered as warnings."""

    def __str__(self) -> str:
        return f"'{self.expression}' has {self.nb_errors} error(s) and " + \
               f"{self.nb_warnings} warning(s)"

    def __repr__(self) -> str:
        return self.__str__()


class DrsGeneratorReport(DrsReport):
    """
    The DRS generator report.
    """

    MISSING_TAG: ClassVar[str] = '[MISSING]'
    """Tag used in the DRS generated expression to replace a missing term."""

    INVALID_TAG: ClassVar[str] = '[INVALID]'
    """Tag used in the DRS generated expression to replace a invalid term."""

    given_mapping_or_bag_of_tokens: Mapping|Iterable
    """The mapping or the bag of tokens given."""

    mapping_used: Mapping
    """The mapping inferred from the given bag of tokens (same mapping otherwise)."""

    generated_drs_expression: str
    """The generated DRS expression with possible tags to replace missing or invalid tokens."""

    errors: list[GeneratorError]
    """A list of DRS generation issues that are considered as errors."""

    warnings: list[GeneratorWarning]
    """A list of DRS generation issues that are considered as warnings."""

    def __str__(self) -> str:
        return f"'{self.generated_drs_expression}' has {self.nb_errors} error(s) and " + \
               f"{self.nb_warnings} warning(s)"

    def __repr__(self) -> str:
        return self.__str__()
