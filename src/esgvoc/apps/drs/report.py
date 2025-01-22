from abc import ABC, abstractmethod
from typing import Any, Mapping, Iterable, Protocol, cast
from esgvoc.api.models import DrsType


class ParserIssueVisitor(Protocol):
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


class DrsIssue(ABC):
    """
    Generic class for all the DRS issues.
    """

    @abstractmethod
    def accept(self, visitor) -> Any: ...


class ParserIssue(DrsIssue):
    def __init__(self, column: int|None = None) -> None:
        super().__init__()
        self.column: int|None = column
    @abstractmethod
    def accept(self, visitor: ParserIssueVisitor) -> Any: ...

class Space(ParserIssue):
    def __init__(self) -> None:
        super().__init__()
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_space_issue(self)
    def __repr__(self):
        return "expression is surrounded by white space[s]"


class Unparsable(ParserIssue):
    def __init__(self, expected_drs_type: DrsType) -> None:
        super().__init__()
        self.expected_drs_type = expected_drs_type
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_unparsable_issue(self)
    def __repr__(self):
        return "unable to parse this expression"


class ExtraSeparator(ParserIssue):
    def __init__(self, column: int) -> None:
        super().__init__(column)
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_extra_separator_issue(self)
    def __repr__(self):
        return f"extra separator(s) at column {self.column}"


class ExtraChar(ParserIssue):
    def __init__(self, column: int) -> None:
        super().__init__(column)
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_extra_char_issue(self)
    def __repr__(self):
        return f"extra character(s) at column {self.column}"


class BlankToken(ParserIssue):
    def __init__(self, column: int) -> None:
        super().__init__(column)
    def accept(self, visitor: ParserIssueVisitor) -> Any:
        return visitor.visit_blank_token_issue(self)
    def __repr__(self):
        return f"blank token at column {self.column}"


class ValidationIssue(DrsIssue):
    @abstractmethod
    def accept(self, visitor: ValidationIssueVisitor) -> Any: ...


class FileNameExtensionIssue(ValidationIssue):
    def __init__(self, expected_extension: str) -> None:
        super().__init__()
        self.expected_extension = expected_extension
    def accept(self, visitor: ValidationIssueVisitor) -> Any:
        return visitor.visit_filename_extension_issue(self)
    def __repr__(self):
        return f"filename extension missing or not compliant with '{self.expected_extension}'"
    

# TODO: to be renamed into TokenIssue.
class Token(ValidationIssue):
    def __init__(self, token: str, token_position: int) -> None:
        super().__init__()
        self.token: str = token
        self.token_position: int = token_position


class GeneratorIssue(DrsIssue):
    @abstractmethod
    def accept(self, visitor: GeneratorIssueVisitor) -> Any: ...


class InvalidToken(Token, GeneratorIssue):
    def __init__(self, token: str, token_position: int, collection_id_or_constant_value: str) -> None:
        super().__init__(token, token_position)
        self.collection_id_or_constant_value = collection_id_or_constant_value
    def accept(self, visitor: ValidationIssueVisitor|GeneratorIssueVisitor) -> Any:
        return visitor.visit_invalid_token_issue(self)
    def __repr__(self):
        return f"token '{self.token}' not compliant with {self.collection_id_or_constant_value} at position {self.token_position}"


class ExtraToken(Token):
    def __init__(self, token: str, token_position: int, collection_id: str|None) -> None:
        super().__init__(token, token_position)
        self.collection_id = collection_id
    def accept(self, visitor: ValidationIssueVisitor) -> Any:
        return visitor.visit_extra_token_issue(self)
    def __repr__(self):
        repr = f"extra token {self.token}"
        if self.collection_id:
            repr += f" invalidated by the optional collection {self.collection_id}"
        return repr + f" at position {self.token_position}"


class MissingToken(ValidationIssue, GeneratorIssue):
    def __init__(self, collection_id: str, collection_position: int) -> None:
        super().__init__()
        self.collection_id: str = collection_id
        self.collection_position: int = collection_position
    def accept(self, visitor: ValidationIssueVisitor|GeneratorIssueVisitor) -> Any:
        return visitor.visit_missing_token_issue(self)
    def __repr__(self):
        return f'missing token for {self.collection_id} at position {self.collection_position}'
    

class TooManyWordsCollection(GeneratorIssue):
    def __init__(self, collection_id: str, words: set[str]) -> None:
        super().__init__()
        self.collection_id: str = collection_id
        self.words: list[str] = list(words)
        self.words.sort()

    def accept(self, visitor: GeneratorIssueVisitor) -> Any:
        return visitor.visit_too_many_words_collection_issue(self)

    def __repr__(self):
        words_str = ", ".join(word for word in self.words)
        result = f'collection {self.collection_id} has more than one word ({words_str})'
        return result


class ConflictingCollections(GeneratorIssue):
    def __init__(self, collection_ids: set[str], words: set[str]) -> None:
        super().__init__()
        self.collection_ids: list[str] = list(collection_ids)
        self.words: list[str] = list(words)
        self.collection_ids.sort()
        self.words.sort()
        
    def accept(self, visitor: GeneratorIssueVisitor) -> Any:
        return visitor.visit_conflicting_collections_issue(self)

    def __repr__(self):
        collection_ids_str = ", ".join(collection_id for collection_id in self.collection_ids)
        words_str = ", ".join(word for word in self.words)
        result = f"collections {collection_ids_str} are competing for the same word(s) {words_str}"
        return result


class AssignedWord(GeneratorIssue):
    def __init__(self, collection_id: str, word: str) -> None:
        super().__init__()
        self.collection_id: str = collection_id
        self.word: str = word

    def accept(self, visitor: GeneratorIssueVisitor) -> Any:
        return visitor.visit_assign_word_issue(self)

    def __repr__(self):
        result = f"assign word {self.word} for collection {self.collection_id}"
        return result


class DrsReport:
    """
    Generic DRS application report class.
    """

    def __init__(self,
                 project_id: str,
                 type: DrsType,
                 errors: list[DrsIssue],
                 warnings: list[DrsIssue]):
        self.project_id: str = project_id
        """The project id associated to the result of the DRS application"""
        self.type: DrsType = type
        """The type of the DRS"""
        self.errors: list[DrsIssue] = errors
        """A list of DRS issues that are considered as errors."""
        self.warnings: list[DrsIssue] = warnings
        """A list of DRS issues that are considered as warnings."""
        self.nb_errors = len(self.errors) if self.errors else 0
        """The number of errors."""
        self.nb_warnings = len(self.warnings) if self.warnings else 0
        """The number of warnings."""
        self.validated: bool = False if errors else True
        """The correctness of the result of the DRS application."""
    def __len__(self) -> int:
        return self.nb_errors
    def __bool__(self) -> bool:
        return self.validated


class DrsValidationReport(DrsReport):
    """
    The DRS validation report class.
    """
    
    def __init__(self,
                 project_id: str,
                 type: DrsType,
                 given_expression: str,
                 errors: list[DrsIssue],
                 warnings: list[DrsIssue]):
        super().__init__(project_id, type, errors, warnings)
        self.expression: str = given_expression
        """The DRS expression been checked"""
        self.message = f"'{self.expression}' has {self.nb_errors} error(s) and " + \
                       f"{self.nb_warnings} warning(s)"
    def __repr__(self) -> str:
        return self.message


class DrsGeneratorReport(DrsReport):
    """
    The DRS generator report.
    """
    
    MISSING_TAG: str = '[MISSING]'
    """Tag used in the DRS generated expression to replace a missing term."""
    INVALID_TAG: str = '[INVALID]'
    """Tag used in the DRS generated expression to replace a invalid term."""
    
    def __init__(self,
                 project_id: str,
                 type: DrsType,
                 given_mapping_or_bag_of_words: Mapping|Iterable,
                 mapping_used: Mapping,
                 computed_drs_expression: str,
                 errors: list[GeneratorIssue],
                 warnings: list[GeneratorIssue]):
        # Mypy can't figure out that GeneratorIssue is an DrsIssue...
        super().__init__(project_id, type, cast(list[DrsIssue], errors),
                         cast(list[DrsIssue], warnings))
        self.given_mapping_or_bag_of_words: Mapping|Iterable = given_mapping_or_bag_of_words
        """The mapping or the bag of tokens given."""
        self.mapping_used: Mapping = mapping_used
        """The mapping inferred from the given bag of tokens (same mapping otherwise)."""
        self.computed_drs_expression = computed_drs_expression # TODO: to be renamed into generated_drs_expression.
        """The generated DRS expression with possible tags to replace missing or invalid tokens"""
        self.message = f"'{self.computed_drs_expression}' has {self.nb_errors} error(s) and " + \
                       f"{self.nb_warnings} warning(s)"
    def __repr__(self) -> str:
        return self.message