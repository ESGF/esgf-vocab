from pydantic import BaseModel, computed_field
from abc import ABC, abstractmethod
from typing import Any, Mapping, Iterable, Protocol, ClassVar
from esgvoc.api.project_specs import DrsType


class ParserIssueVisitor(Protocol):
    """
    Specifications for a Parser issues visitor.
    """
    
    def visit_space_issue(self, issue: "Space") -> Any: ...
    def visit_unparsable_issue(self, issue: "Unparsable") -> Any: ...
    def visit_extra_separator_issue(self, issue: "ExtraSeparator") -> Any: ...
    def visit_extra_char_issue(self, issue: "ExtraChar") -> Any: ...
    def visit_blank_token_issue(self, issue: "BlankToken") -> Any: ...


class ValidationIssueVisitor(Protocol):
    def visit_filename_extension_issue(self, issue: "FileNameExtensionIssue") -> Any: ...
    def visit_invalid_token_issue(self, issue: "InvalidToken") -> Any: ...
    def visit_extra_token_issue(self, issue: "ExtraToken") -> Any: ...
    def visit_missing_token_issue(self, issue: "MissingToken") -> Any: ...


class GeneratorIssueVisitor(Protocol):
    def visit_invalid_token_issue(self, issue: "InvalidToken") -> Any: ...
    def visit_missing_token_issue(self, issue: "MissingToken") -> Any: ...
    def visit_too_many_words_collection_issue(self, issue: "TooManyWordsCollection") -> Any: ...
    def visit_conflicting_collections_issue(self, issue: "ConflictingCollections") -> Any: ...
    def visit_assign_word_issue(self, issue: "AssignedWord") -> Any: ...


class DrsIssue(BaseModel, ABC):
    """
    Generic class for all the DRS issues.
    """

    @abstractmethod
    def accept(self, visitor) -> Any: ...


class ParserIssue(DrsIssue):
    column: int|None = None

    @abstractmethod
    def accept(self, visitor: ParserIssueVisitor) -> Any: ...

class Space(ParserIssue):
    
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_space_issue(self)
    def __repr__(self):
        return "expression is surrounded by white space[s]"


class Unparsable(ParserIssue):
    expected_drs_type: DrsType
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_unparsable_issue(self)
    def __repr__(self):
        return "unable to parse this expression"


class ExtraSeparator(ParserIssue):
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_extra_separator_issue(self)
    def __repr__(self):
        return f"extra separator(s) at column {self.column}"


class ExtraChar(ParserIssue):
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_extra_char_issue(self)
    def __repr__(self):
        return f"extra character(s) at column {self.column}"


class BlankToken(ParserIssue):
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_blank_token_issue(self)
    def __repr__(self):
        return f"blank token at column {self.column}"


class ValidationIssue(DrsIssue):
    @abstractmethod
    def accept(self, visitor: ValidationIssueVisitor) -> Any: ...


class FileNameExtensionIssue(ValidationIssue):
    expected_extension: str
    def accept(self, visitor: ValidationIssueVisitor) -> Any:
        return visitor.visit_filename_extension_issue(self)
    def __repr__(self):
        return f"filename extension missing or not compliant with '{self.expected_extension}'"
    

class TokenIssue(ValidationIssue):
    token: str
    token_position: int


class GeneratorIssue(DrsIssue):
    @abstractmethod
    def accept(self, visitor: GeneratorIssueVisitor) -> Any: ...


class InvalidToken(TokenIssue, GeneratorIssue):
    collection_id_or_constant_value: str
    def accept(self, visitor: ValidationIssueVisitor|GeneratorIssueVisitor) -> Any:
        return visitor.visit_invalid_token_issue(self)
    def __repr__(self):
        return f"token '{self.token}' not compliant with {self.collection_id_or_constant_value} at position {self.token_position}"


class ExtraToken(TokenIssue):
    collection_id: str|None
    def accept(self, visitor: ValidationIssueVisitor) -> Any:
        return visitor.visit_extra_token_issue(self)
    def __repr__(self):
        repr = f"extra token {self.token}"
        if self.collection_id:
            repr += f" invalidated by the optional collection {self.collection_id}"
        return repr + f" at position {self.token_position}"


class MissingToken(ValidationIssue, GeneratorIssue):
    collection_id: str
    collection_position: int
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