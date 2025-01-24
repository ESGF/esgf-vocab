from pydantic import BaseModel, computed_field
from abc import ABC, abstractmethod
from typing import Any, Mapping, Iterable, Protocol, ClassVar
from esgvoc.api.project_specs import DrsType


class ParserIssueVisitor(Protocol):
    """
    Specifications for a parser issues visitor.
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


class ValidationIssueVisitor(Protocol):
    """
    Specifications for a validation issues visitor.
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


class GeneratorIssueVisitor(Protocol):
    """
    Specifications for a generator issues visitor.
    """

    def visit_invalid_token_issue(self, issue: "InvalidToken") -> Any:
        """Visit an invalid token issue."""
        pass
    def visit_missing_token_issue(self, issue: "MissingToken") -> Any:
        """Visit a missing token issue."""
        pass
    def visit_too_many_words_collection_issue(self, issue: "TooManyWordsCollection") -> Any:
        """Visit a too many words collection issue."""
        pass
    def visit_conflicting_collections_issue(self, issue: "ConflictingCollections") -> Any:
        """Visit a conflicting collections issue."""
        pass
    def visit_assign_word_issue(self, issue: "AssignedWord") -> Any:
        """Visit an assign word issue."""
        pass


class DrsIssue(BaseModel, ABC):
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


class ParserIssue(DrsIssue):
    """
    Generic class for the DRS parser issues.
    """
    column: int|None = None
    """the column of faulty characters"""

    @abstractmethod
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        """
        Accept an DRS parser issue visitor.

        :param visitor: The DRS parser issue visitor.
        :type visitor: ParserIssueVisitor
        :return: Depending on the visitor.
        :rtype: Any
        """
        pass

class Space(ParserIssue):
    """
    Represents a problem of unnecessary space[s] at the beginning or end of the DRS expression.
    Note: `column` is `None`.
    """
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_space_issue(self)
    def __repr__(self):
        return "expression is surrounded by white space[s]"


class Unparsable(ParserIssue):
    """
    Represents a problem of non-compliance of the DRS expression.
    Note: `column` is `None`.
    """
    expected_drs_type: DrsType
    """The expected DRS type of the expression (directory, file name or dataset id)."""
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_unparsable_issue(self)
    def __repr__(self):
        return "unable to parse this expression"


class ExtraSeparator(ParserIssue):
    """
    Represents a problem of multiple separator occurrences in the DRS expression.
    """
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_extra_separator_issue(self)
    def __repr__(self):
        return f"extra separator(s) at column {self.column}"


class ExtraChar(ParserIssue):
    """
    Represents a problem of extra characters at the end of the DRS expression.
    """
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_extra_char_issue(self)
    def __repr__(self):
        return f"extra character(s) at column {self.column}"


class BlankToken(ParserIssue):
    """
    Represents a problem of blank token in the DRS expression (i.e., space[s] surrounded by separators).
    """
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_blank_token_issue(self)
    def __repr__(self):
        return f"blank token at column {self.column}"


class ValidationIssue(DrsIssue):
    """
    Generic class for the validation issues.
    """
    @abstractmethod
    def accept(self, visitor: ValidationIssueVisitor) -> Any:
        """
        Accept an DRS validation issue visitor.

        :param visitor: The DRS validation issue visitor.
        :type visitor: ValidationIssueVisitor
        :return: Depending on the visitor.
        :rtype: Any
        """
        pass


class FileNameExtensionIssue(ValidationIssue):
    """
    Represents a problem on the given file name extension (missing or not compliant).
    """
    expected_extension: str
    """The expected file name extension."""
    def accept(self, visitor: ValidationIssueVisitor) -> Any:
        return visitor.visit_filename_extension_issue(self)
    def __repr__(self):
        return f"filename extension missing or not compliant with '{self.expected_extension}'"
    

class TokenIssue(ValidationIssue):
    """
    Generic class for the DRS token issues.
    """
    token: str
    """The faulty token."""
    token_position: int
    """The position of the faulty token (the part position, not the column of the characters."""


class GeneratorIssue(DrsIssue):
    """
    Generic class for the DRS generator issues.
    """
    @abstractmethod
    def accept(self, visitor: GeneratorIssueVisitor) -> Any:
        """
        Accept an DRS generator issue visitor.

        :param visitor: The DRS generator issue visitor.
        :type visitor: GeneratorIssueVisitor
        :return: Depending on the visitor.
        :rtype: Any
        """
        pass


class InvalidToken(TokenIssue, GeneratorIssue):
    """
    Represents a problem of invalid token against a collection or a constant part of a DRS specification.
    """
    collection_id_or_constant_value: str
    """The collection id or the constant part of a DRS specification."""
    def accept(self, visitor: ValidationIssueVisitor|GeneratorIssueVisitor) -> Any:
        return visitor.visit_invalid_token_issue(self)
    def __repr__(self):
        return f"token '{self.token}' not compliant with {self.collection_id_or_constant_value} at position {self.token_position}"


class ExtraToken(TokenIssue):
    """
    Represents a problem of extra token at the end of the given DRS expression.
    All part of the DRS specification have been processed and this token is not necessary
    (`collection_id` is `None`) or it has been invalidated by an optional collection part 
    of the DRS specification (`collection_id` is set).
    """
    collection_id: str|None
    """The optional collection id or `None`"""
    def accept(self, visitor: ValidationIssueVisitor) -> Any:
        return visitor.visit_extra_token_issue(self)
    def __repr__(self):
        repr = f"extra token {self.token}"
        if self.collection_id:
            repr += f" invalidated by the optional collection {self.collection_id}"
        return repr + f" at position {self.token_position}"


class MissingToken(ValidationIssue, GeneratorIssue):
    """
    Represents a problem of missing token for a collection part of the DRS specification.
    """
    collection_id: str
    """The collection id."""
    collection_position: int
    """The collection part position (not the column of the characters)."""
    def accept(self, visitor: ValidationIssueVisitor|GeneratorIssueVisitor) -> Any:
        return visitor.visit_missing_token_issue(self)
    def __repr__(self):
        return f'missing token for {self.collection_id} at position {self.collection_position}'
    

class TooManyWordsCollection(GeneratorIssue):
    collection_id: str
    words: list[str]
    def accept(self, visitor: GeneratorIssueVisitor) -> Any:
        return visitor.visit_too_many_words_collection_issue(self)

    def __repr__(self):
        words_str = ", ".join(word for word in self.words)
        result = f'collection {self.collection_id} has more than one word ({words_str})'
        return result


class ConflictingCollections(GeneratorIssue):
    collection_ids: list[str]
    words: list[str]
    def accept(self, visitor: GeneratorIssueVisitor) -> Any:
        return visitor.visit_conflicting_collections_issue(self)
    def __repr__(self):
        collection_ids_str = ", ".join(collection_id for collection_id in self.collection_ids)
        words_str = ", ".join(word for word in self.words)
        result = f"collections {collection_ids_str} are competing for the same word(s) {words_str}"
        return result


class AssignedWord(GeneratorIssue):
    collection_id: str
    word: str
    def accept(self, visitor: GeneratorIssueVisitor) -> Any:
        return visitor.visit_assign_word_issue(self)
    def __repr__(self):
        result = f"assign word {self.word} for collection {self.collection_id}"
        return result


class DrsReport(BaseModel):
    """
    Generic DRS application report class.
    """
    project_id: str
    """The project id associated to the result of the DRS application"""
    type: DrsType
    """The type of the DRS"""
    errors: list[DrsIssue]
    """A list of DRS issues that are considered as errors."""
    warnings: list[DrsIssue]
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
    """The DRS expression been checked"""
    def __repr__(self) -> str:
        return f"'{self.expression}' has {self.nb_errors} error(s) and " + \
               f"{self.nb_warnings} warning(s)"


class DrsGeneratorReport(DrsReport):
    """
    The DRS generator report.
    """
    MISSING_TAG: ClassVar[str] = '[MISSING]'
    """Tag used in the DRS generated expression to replace a missing term."""
    INVALID_TAG: ClassVar[str] = '[INVALID]'
    """Tag used in the DRS generated expression to replace a invalid term."""
    given_mapping_or_bag_of_words: Mapping|Iterable
    """The mapping or the bag of tokens given."""
    mapping_used: Mapping
    """The mapping inferred from the given bag of tokens (same mapping otherwise)."""
    computed_drs_expression: str # TODO: to be renamed into generated_drs_expression.
    """The generated DRS expression with possible tags to replace missing or invalid tokens"""
    def __repr__(self) -> str:
        return f"'{self.computed_drs_expression}' has {self.nb_errors} error(s) and " + \
               f"{self.nb_warnings} warning(s)"